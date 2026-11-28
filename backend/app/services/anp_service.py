"""Dados regulatórios da ANP para postos ao longo da rota: catálogo de referência, cruzamento e ranqueamento.

O cruzamento combina duas fontes:

1. O catálogo regulatório local (`CATALOGO_ANP`), que funciona também como fallback controlado quando o
   provedor externo de postos (Overpass/OpenStreetMap) falha.
2. Os postos reais devolvidos pelo OpenStreetMap, enriquecidos com o registro ANP correspondente
   (mesmo CNPJ ou até `RAIO_CORRESPONDENCIA_KM` de distância) ou, na falta dele, com as tags do OSM.

ATENÇÃO: os registros de `CATALOGO_ANP` são uma AMOSTRA ILUSTRATIVA para demonstração e testes (CNPJs e
razões sociais fictícios, posições aproximadas ao longo da BR-343 no Piauí). Para uso real, substitua-os
pelos dados abertos de revendedores autorizados publicados pela ANP.

Fórmula do ranqueamento regulatório (`calcular_ranking_score`, escala de 0 a 10):

    score = 10 * (0,45 * avaliacao / 5 + 0,35 * min(anos_autorizacao, 20) / 20 + 0,20 * proximidade)
    proximidade = max(0, 1 - distancia_km / raio_km)

Sem avaliação informada, usa-se a nota neutra `AVALIACAO_NEUTRA`; sem registro ANP, o tempo de
autorização conta como zero (o posto não comprova autorização e cai no ranking).
"""

from datetime import UTC, date, datetime
from typing import Any

from app.services.geo_utils import haversine_km

PESO_AVALIACAO = 0.45
PESO_AUTORIZACAO = 0.35
PESO_PROXIMIDADE = 0.20
AVALIACAO_MAXIMA = 5.0
AVALIACAO_NEUTRA = 3.0
# Acima deste tempo de autorização o histórico regulatório já não diferencia os postos
ANOS_AUTORIZACAO_TETO = 20
# Distância máxima para considerar que um posto do OSM e um registro ANP são o mesmo estabelecimento
RAIO_CORRESPONDENCIA_KM = 0.3

# Amostra ilustrativa (dados fictícios) de revendedores autorizados ao longo da BR-343 no Piauí
CATALOGO_ANP: tuple[dict[str, Any], ...] = (
    {
        "cnpj": "00.343.001/0001-10",
        "razao_social": "Auto Posto Portal de Sete Cidades Ltda",
        "nome_fantasia": "Posto Portal de Sete Cidades",
        "latitude": -4.2652,
        "longitude": -41.7798,
        "rodovia": "BR-343",
        "municipio": "Piripiri",
        "uf": "PI",
        "avaliacao": 4.7,
        "data_autorizacao_anp": "2006-03-14",
        "combustiveis": ["Gasolina comum", "Gasolina aditivada", "Etanol", "Diesel S10"],
    },
    {
        "cnpj": "00.343.002/0001-20",
        "razao_social": "Comercial de Combustíveis Caldeirão Ltda",
        "nome_fantasia": "Posto Caldeirão",
        "latitude": -4.2811,
        "longitude": -41.7714,
        "rodovia": "BR-343",
        "municipio": "Piripiri",
        "uf": "PI",
        "avaliacao": 4.2,
        "data_autorizacao_anp": "2015-08-02",
        "combustiveis": ["Gasolina comum", "Etanol", "Diesel S10", "Diesel S500"],
    },
    {
        "cnpj": "00.343.003/0001-30",
        "razao_social": "Posto Piripiri Norte Revendedora Ltda",
        "nome_fantasia": "Posto Piripiri Norte",
        "latitude": -4.2533,
        "longitude": -41.7861,
        "rodovia": "BR-343",
        "municipio": "Piripiri",
        "uf": "PI",
        "avaliacao": 3.6,
        "data_autorizacao_anp": "2021-11-09",
        "combustiveis": ["Gasolina comum", "Diesel S500"],
    },
    {
        "cnpj": "00.343.004/0001-40",
        "razao_social": "Rede Poty de Combustíveis Ltda",
        "nome_fantasia": "Posto Poty Saída Norte",
        "latitude": -5.0231,
        "longitude": -42.7603,
        "rodovia": "BR-343",
        "municipio": "Teresina",
        "uf": "PI",
        "avaliacao": 4.4,
        "data_autorizacao_anp": "2004-05-21",
        "combustiveis": ["Gasolina comum", "Gasolina aditivada", "Etanol", "Diesel S10", "GNV"],
    },
    {
        "cnpj": "00.343.005/0001-50",
        "razao_social": "Posto Carnaubais de Campo Maior Ltda",
        "nome_fantasia": "Posto Carnaubais",
        "latitude": -4.8292,
        "longitude": -42.1655,
        "rodovia": "BR-343",
        "municipio": "Campo Maior",
        "uf": "PI",
        "avaliacao": 4.1,
        "data_autorizacao_anp": "2011-02-17",
        "combustiveis": ["Gasolina comum", "Etanol", "Diesel S10"],
    },
    {
        "cnpj": "00.343.006/0001-60",
        "razao_social": "Auto Posto Piracuruca Ltda",
        "nome_fantasia": "Posto Piracuruca",
        "latitude": -3.9265,
        "longitude": -41.7102,
        "rodovia": "BR-343",
        "municipio": "Piracuruca",
        "uf": "PI",
        "avaliacao": 4.0,
        "data_autorizacao_anp": "2013-06-30",
        "combustiveis": ["Gasolina comum", "Etanol", "Diesel S10", "Diesel S500"],
    },
    {
        "cnpj": "00.343.007/0001-70",
        "razao_social": "Posto Delta do Parnaíba Combustíveis Ltda",
        "nome_fantasia": "Posto Delta",
        "latitude": -2.9192,
        "longitude": -41.7590,
        "rodovia": "BR-343",
        "municipio": "Parnaíba",
        "uf": "PI",
        "avaliacao": 4.5,
        "data_autorizacao_anp": "2008-09-12",
        "combustiveis": ["Gasolina comum", "Gasolina aditivada", "Etanol", "Diesel S10"],
    },
)

# Tags `fuel:*` do OpenStreetMap -> nome do combustível exibido no pop-up
COMBUSTIVEIS_OSM: dict[str, str] = {
    "fuel:octane_87": "Gasolina comum",
    "fuel:octane_91": "Gasolina comum",
    "fuel:octane_95": "Gasolina aditivada",
    "fuel:ethanol": "Etanol",
    "fuel:e100": "Etanol",
    "fuel:diesel": "Diesel",
    "fuel:GTL_diesel": "Diesel S10",
    "fuel:HGV_diesel": "Diesel S500",
    "fuel:cng": "GNV",
    "fuel:lpg": "GLP",
}


def _somente_digitos(texto: str | None) -> str:
    return "".join(c for c in str(texto or "") if c.isdigit())


def calcular_anos_autorizacao(data_autorizacao: str | None, hoje: date | None = None) -> int | None:
    """Anos completos desde a autorização na ANP (data ISO 'AAAA-MM-DD'); None se ausente ou inválida."""
    if not data_autorizacao:
        return None
    try:
        inicio = date.fromisoformat(str(data_autorizacao))
    except ValueError:
        return None
    referencia = hoje or datetime.now(UTC).date()
    anos = referencia.year - inicio.year - ((referencia.month, referencia.day) < (inicio.month, inicio.day))
    return max(anos, 0)


def calcular_ranking_score(
    avaliacao: float | None,
    anos_autorizacao: int | None,
    distancia_km: float,
    raio_km: float,
) -> float:
    """Score regulatório de 0 a 10 (fórmula no docstring do módulo), arredondado a uma casa decimal."""
    nota = AVALIACAO_NEUTRA if avaliacao is None else min(max(float(avaliacao), 0.0), AVALIACAO_MAXIMA)
    anos = min(max(anos_autorizacao or 0, 0), ANOS_AUTORIZACAO_TETO)
    proximidade = max(0.0, 1.0 - distancia_km / raio_km) if raio_km > 0 else 0.0
    score = (
        PESO_AVALIACAO * nota / AVALIACAO_MAXIMA
        + PESO_AUTORIZACAO * anos / ANOS_AUTORIZACAO_TETO
        + PESO_PROXIMIDADE * proximidade
    )
    return round(10.0 * score, 1)


def _posto_do_registro(registro: dict[str, Any], hoje: date | None) -> dict[str, Any]:
    """Converte um registro do catálogo ANP no formato de posto usado pelas paradas."""
    return {
        "nome": registro.get("nome_fantasia") or registro["razao_social"],
        "latitude": float(registro["latitude"]),
        "longitude": float(registro["longitude"]),
        "cnpj": registro["cnpj"],
        "razao_social": registro["razao_social"],
        "avaliacao": registro.get("avaliacao"),
        "tempo_autorizacao_anp": calcular_anos_autorizacao(registro.get("data_autorizacao_anp"), hoje),
        "combustiveis": list(registro.get("combustiveis") or []),
        "rodovia": registro.get("rodovia"),
        "municipio": registro.get("municipio"),
        "uf": registro.get("uf"),
        "fonte": "anp",
    }


def _combustiveis_osm(tags: dict[str, Any]) -> list[str]:
    encontrados: list[str] = []
    for tag, nome in COMBUSTIVEIS_OSM.items():
        if str(tags.get(tag, "")).lower() == "yes" and nome not in encontrados:
            encontrados.append(nome)
    return encontrados


def _registro_correspondente(
    elemento: dict[str, Any], catalogo: tuple[dict[str, Any], ...] | list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Registro ANP do mesmo estabelecimento: mesmo CNPJ nas tags do OSM ou posição praticamente igual."""
    tags = elemento.get("tags") or {}
    cnpj_osm = _somente_digitos(tags.get("ref:vatin") or tags.get("ref:CNPJ") or tags.get("cnpj"))
    if cnpj_osm:
        for registro in catalogo:
            if _somente_digitos(registro["cnpj"]) == cnpj_osm:
                return registro
    for registro in catalogo:
        if haversine_km(elemento["lat"], elemento["lon"], registro["latitude"], registro["longitude"]) <= RAIO_CORRESPONDENCIA_KM:
            return registro
    return None


def _posto_do_osm(
    elemento: dict[str, Any],
    catalogo: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    nome_generico: str,
    hoje: date | None,
) -> dict[str, Any]:
    """Posto do OSM enriquecido com o registro ANP correspondente (ou só com as tags, se não houver)."""
    registro = _registro_correspondente(elemento, catalogo)
    tags = elemento.get("tags") or {}
    if registro is not None:
        posto = _posto_do_registro(registro, hoje)
        # A posição e o nome vêm do posto real mapeado; os dados regulatórios, da ANP
        posto["nome"] = tags.get("name") or posto["nome"]
        posto["latitude"] = float(elemento["lat"])
        posto["longitude"] = float(elemento["lon"])
        posto["fonte"] = "osm+anp"
        return posto

    cnpj = tags.get("ref:vatin") or tags.get("ref:CNPJ") or tags.get("cnpj")
    return {
        "nome": tags.get("name") or tags.get("brand") or nome_generico,
        "latitude": float(elemento["lat"]),
        "longitude": float(elemento["lon"]),
        "cnpj": str(cnpj) if cnpj else None,
        "razao_social": tags.get("operator"),
        "avaliacao": None,
        "tempo_autorizacao_anp": None,
        "combustiveis": _combustiveis_osm(tags),
        "rodovia": None,
        "municipio": tags.get("addr:city"),
        "uf": tags.get("addr:state"),
        "fonte": "osm",
    }


def ranquear_postos(
    lat: float,
    lon: float,
    raio_km: float,
    elementos_osm: list[dict[str, Any]] | None = None,
    catalogo: tuple[dict[str, Any], ...] | list[dict[str, Any]] = CATALOGO_ANP,
    nome_generico: str = "Posto de combustível",
    hoje: date | None = None,
) -> list[dict[str, Any]]:
    """Cruza os postos do OSM com o catálogo ANP ao redor do ponto e devolve a lista ordenada pelo score.

    Registros ANP dentro do raio que não tenham correspondência no OSM também entram, de modo que uma
    falha do OSM (`elementos_osm=None`) ainda produz postos confirmados pelo catálogo regulatório.
    Cada posto traz `distancia_km` até o ponto e `ranking_score`; empates favorecem o mais próximo.
    """
    candidatos: list[dict[str, Any]] = []
    cnpjs_usados: set[str] = set()

    for elemento in elementos_osm or []:
        if "lat" not in elemento or "lon" not in elemento:
            continue
        posto = _posto_do_osm(elemento, catalogo, nome_generico, hoje)
        if posto.get("cnpj"):
            cnpjs_usados.add(_somente_digitos(posto["cnpj"]))
        candidatos.append(posto)

    for registro in catalogo:
        if _somente_digitos(registro["cnpj"]) in cnpjs_usados:
            continue
        if haversine_km(lat, lon, registro["latitude"], registro["longitude"]) <= raio_km:
            candidatos.append(_posto_do_registro(registro, hoje))

    for posto in candidatos:
        distancia = haversine_km(lat, lon, posto["latitude"], posto["longitude"])
        posto["distancia_km"] = round(distancia, 2)
        posto["ranking_score"] = calcular_ranking_score(
            posto.get("avaliacao"), posto.get("tempo_autorizacao_anp"), distancia, raio_km
        )

    return sorted(candidatos, key=lambda p: (-p["ranking_score"], p["distancia_km"]))
