"""Paradas de abastecimento/recarga: projeção pela autonomia, postos reais (Overpass) e ranqueamento regulatório ANP.

Cada parada projetada pela autonomia é confirmada pelo posto de melhor `ranking_score` ao redor dela,
cruzando o OpenStreetMap com o catálogo regulatório da ANP (`anp_service`). Se o Overpass falhar, o próprio
catálogo ANP serve de fallback controlado; sem nenhum posto conhecido, a parada fica com a posição estimada.
"""

import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging_config import logger
from app.services.anp_service import CATALOGO_ANP, ranquear_postos
from app.services.geo_utils import distancias_acumuladas_km, ponto_na_distancia

URL_OVERPASS = "https://overpass-api.de/api/interpreter"

# Reserva mínima (fração da autonomia) com que o veículo deve chegar a uma parada ou ao destino
MARGEM_SEGURANCA = 0.18
# Raio, em metros, da busca de um posto real ao redor da posição projetada
RAIO_BUSCA_M = 10_000
# Teto de paradas por roteiro, para que uma autonomia irreal (ex: 5 km) não gere centenas de marcadores
MAX_PARADAS = 20


def _rotulos(tipo_veiculo: str) -> tuple[str, str, str]:
    """(nome genérico da parada, tag OSM do tipo de posto, nome genérico do posto real)."""
    if tipo_veiculo == "eletrico":
        return "Recarga estimada", "charging_station", "Eletroposto"
    return "Abastecimento estimado", "fuel", "Posto de combustível"


def projetar_paradas(
    coordenadas: list[list[float]],
    distancia_km: float,
    autonomia_km: float,
    tipo_veiculo: str = "gasolina",
    margem: float = MARGEM_SEGURANCA,
) -> list[dict[str, Any]]:
    """Projeta ao longo da polilinha as paradas necessárias para nunca passar da reserva crítica.

    Modelo: tanque/bateria cheio na saída e reabastecimento completo em cada parada. O alcance útil por
    trecho é `autonomia_km * (1 - margem)`; há parada em cada múltiplo dele enquanto ele ficar antes do destino.
    As posições são ESTIMADAS (`estimada=True`): não há garantia de que exista posto naquele ponto.
    """
    if len(coordenadas) < 2 or distancia_km <= 0 or autonomia_km <= 0:
        return []

    alcance_util = autonomia_km * (1.0 - margem)
    if alcance_util <= 0 or distancia_km <= alcance_util:
        return []

    acumuladas = distancias_acumuladas_km(coordenadas)
    # A distância da polilinha simplificada difere da distância viária do OSRM; ajusta a escala
    escala = acumuladas[-1] / distancia_km if distancia_km > 0 else 1.0
    rotulo, _, _ = _rotulos(tipo_veiculo)

    paradas: list[dict[str, Any]] = []
    km = alcance_util
    while km < distancia_km and len(paradas) < MAX_PARADAS:
        lat, lon = ponto_na_distancia(coordenadas, acumuladas, km * escala)
        paradas.append(
            {
                "id": f"parada_estimada_{len(paradas) + 1}",
                "nome": f"{rotulo} (km {round(km)})",
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "distancia_origem_km": round(km, 1),
                "estimada": True,
                "visitado": False,
            }
        )
        km += alcance_util
    return paradas


async def _buscar_postos_osm(
    client: httpx.AsyncClient, lat: float, lon: float, tag_amenity: str
) -> list[dict[str, Any]] | None:
    """Consulta o Overpass ao redor do ponto; devolve os elementos com posição, ou None se o provedor falhar."""
    consulta = (
        f'[out:json][timeout:6];node["amenity"="{tag_amenity}"](around:{RAIO_BUSCA_M},{lat},{lon});out 10;'
    )
    try:
        resposta = await client.post(
            URL_OVERPASS,
            data={"data": consulta},
            headers={"User-Agent": "GuiaTuristaInteligente/3.0 (FastAPI)", "Accept": "application/json"},
            timeout=min(settings.TIMEOUT_ROTA, 2.5),
        )
        resposta.raise_for_status()
        elementos = resposta.json().get("elements") or []
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        logger.warning("Overpass indisponível para (%s, %s): %s", lat, lon, type(exc).__name__)
        return None
    return [e for e in elementos if isinstance(e, dict) and "lat" in e and "lon" in e]


# Atributos regulatórios copiados do posto escolhido para a parada (contrato do pop-up ANP no mapa)
CAMPOS_REGULATORIOS = (
    "cnpj",
    "razao_social",
    "avaliacao",
    "tempo_autorizacao_anp",
    "combustiveis",
    "ranking_score",
    "rodovia",
    "municipio",
    "uf",
)


def _aplicar_posto(parada: dict[str, Any], posto: dict[str, Any]) -> None:
    """Confirma a parada no posto escolhido, copiando posição e atributos regulatórios ANP."""
    parada["nome"] = f"{posto['nome']} (km {round(parada['distancia_origem_km'])})"
    parada["latitude"] = round(float(posto["latitude"]), 5)
    parada["longitude"] = round(float(posto["longitude"]), 5)
    parada["id"] = parada["id"].replace("estimada", "posto")
    parada["estimada"] = False
    for campo in CAMPOS_REGULATORIOS:
        if posto.get(campo) not in (None, [], ""):
            parada[campo] = posto[campo]


async def localizar_paradas_async(
    client: httpx.AsyncClient,
    coordenadas: list[list[float]],
    distancia_km: float,
    autonomia_km: float,
    tipo_veiculo: str = "gasolina",
) -> list[dict[str, Any]]:
    """Projeta as paradas e confirma cada uma no posto de melhor ranking regulatório ao redor (em paralelo).

    Parada confirmada: `estimada=False`, com nome, coordenadas e dados ANP (CNPJ, razão social, avaliação,
    tempo de autorização em anos, combustíveis e `ranking_score`) do posto escolhido, até `RAIO_BUSCA_M`
    da posição projetada. O catálogo ANP só vale para combustíveis: eletropostos não são regulados pela ANP.
    Sem posto no OSM nem no catálogo, a parada permanece com a posição projetada e `estimada=True`.
    """
    paradas = projetar_paradas(coordenadas, distancia_km, autonomia_km, tipo_veiculo)
    if not paradas:
        return []

    _, tag_amenity, nome_generico = _rotulos(tipo_veiculo)
    catalogo = () if tipo_veiculo == "eletrico" else CATALOGO_ANP
    achados = await asyncio.gather(
        *(_buscar_postos_osm(client, p["latitude"], p["longitude"], tag_amenity) for p in paradas)
    )

    for parada, elementos in zip(paradas, achados):
        ranking = ranquear_postos(
            parada["latitude"],
            parada["longitude"],
            RAIO_BUSCA_M / 1000,
            elementos,
            catalogo=catalogo,
            nome_generico=nome_generico,
        )
        if ranking:
            _aplicar_posto(parada, ranking[0])
    return paradas
