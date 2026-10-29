"""Serviço assíncrono de roteamento rodoviário (OSRM): distância, duração, geometria GeoJSON e alternativas."""

from typing import Any

import httpx

from app.core.config import settings
from app.services.erros import ServicoIndisponivelError, falha_http
from app.services.postos_service import MARGEM_SEGURANCA, projetar_paradas

URL_OSRM = "https://router.project-osrm.org/route/v1/driving"

# Se o ponto de partida/chegada estiver a mais de 10 km da via mais próxima (ex: ilhas), não há rota rodoviária
LIMITE_SNAP_METROS = 10_000.0
# Na preferência "cenica", só se aceita uma alternativa até 30% mais demorada que a mais rápida
TOLERANCIA_CENICA = 1.30

NOME_MENOR_TEMPO = "Sugestão 01 (Rodovia Principal / Menor Tempo)"
NOME_MAIS_ECONOMICA = "Sugestão 02 (Rodovias Federais / Mais Econômica)"


def _montar_rota(bruta: dict[str, Any]) -> dict[str, Any]:
    """Converte uma rota crua do OSRM nas unidades da API (km, minutos) com GeoJSON [longitude, latitude]."""
    coordenadas = [[round(lon, 5), round(lat, 5)] for lon, lat in bruta["geometry"]["coordinates"]]
    return {
        "distancia_km": round(float(bruta["distance"]) / 1000.0, 1),
        "duracao_minutos": round(float(bruta["duration"]) / 60.0, 1),
        "geometria": {"type": "LineString", "coordinates": coordenadas},
    }


def _escolher_principal(rotas: list[dict[str, Any]], preferencia: str) -> dict[str, Any]:
    """Escolhe a rota principal conforme a preferência.

    O OSRM público só oferece o perfil `driving`, então as preferências são heurísticas sobre as candidatas:
    rapida = menor duração; economica = menor distância (proxy de combustível); cenica = a candidata mais
    longa em tempo dentro de `TOLERANCIA_CENICA` da mais rápida (tende a evitar o eixo mais direto).
    """
    mais_rapida = min(rotas, key=lambda r: r["duracao_minutos"])
    if preferencia == "economica":
        return min(rotas, key=lambda r: r["distancia_km"])
    if preferencia == "cenica":
        limite = mais_rapida["duracao_minutos"] * TOLERANCIA_CENICA
        return max((r for r in rotas if r["duracao_minutos"] <= limite), key=lambda r: r["duracao_minutos"])
    return mais_rapida


def _nomear(rotas: list[dict[str, Any]]) -> None:
    """Rotula as candidatas: Sugestão 01 (menor tempo), Sugestão 02 (menor distância) e Alternativa N."""
    mais_rapida = min(rotas, key=lambda r: r["duracao_minutos"])
    mais_curta = min(rotas, key=lambda r: r["distancia_km"])
    mais_rapida["nome"] = NOME_MENOR_TEMPO
    if mais_curta is not mais_rapida:
        mais_curta["nome"] = NOME_MAIS_ECONOMICA
    extras = 1
    for rota in rotas:
        if "nome" not in rota:
            extras += 1
            rota["nome"] = f"Alternativa {extras:02d}"


async def calcular_rota_osrm_async(
    client: httpx.AsyncClient,
    lat_o: float,
    lon_o: float,
    lat_d: float,
    lon_d: float,
    preferencia: str = "rapida",
    autonomia_km: float | None = None,
    tipo_veiculo: str = "gasolina",
    margem_seguranca: float = MARGEM_SEGURANCA,
) -> dict[str, Any]:
    """Calcula a rota de carro entre dois pontos.

    Retorna `distancia_km`, `duracao_minutos`, `geometria` (GeoJSON LineString em [longitude, latitude]),
    `nome` da rota escolhida, `alternativas` (cada uma com nome, distância, duração e geometria) e `paradas`.
    As paradas só são projetadas se `autonomia_km` for informada (posições estimadas, ver `postos_service`).
    Levanta `ServicoIndisponivelError` se não houver rota rodoviária (ex: ilhas) ou o OSRM falhar.
    """
    if (lat_o == 0.0 and lon_o == 0.0) or (lat_d == 0.0 and lon_d == 0.0):
        raise ServicoIndisponivelError("Rota indisponível (origem ou destino não geocodificado)")

    # OSRM espera {longitude},{latitude};{longitude},{latitude}
    url = f"{URL_OSRM}/{lon_o},{lat_o};{lon_d},{lat_d}"
    params = {"overview": "simplified", "geometries": "geojson", "alternatives": "true"}

    try:
        resposta = await client.get(url, params=params, timeout=settings.TIMEOUT_ROTA)
        resposta.raise_for_status()
        dados = resposta.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise falha_http("OSRM", exc) from exc

    brutas = dados.get("routes") or []
    if dados.get("code") != "Ok" or not brutas:
        raise ServicoIndisponivelError("Sem rota direta. Considere voos ou barcos")

    # Ilhas: o OSRM "encaixa" o ponto na costa mais próxima; distante demais significa sem estrada
    for waypoint in dados.get("waypoints") or []:
        if float(waypoint.get("distance", 0.0)) > LIMITE_SNAP_METROS:
            raise ServicoIndisponivelError("Sem rota direta. Considere voos ou barcos")

    rotas = [_montar_rota(bruta) for bruta in brutas]
    _nomear(rotas)
    principal = _escolher_principal(rotas, preferencia)

    resultado: dict[str, Any] = {
        "distancia_km": principal["distancia_km"],
        "duracao_minutos": principal["duracao_minutos"],
        "geometria": principal["geometria"],
        "nome": principal["nome"],
        "alternativas": [r for r in rotas if r is not principal],
        "paradas": [],
    }
    if autonomia_km:
        resultado["paradas"] = projetar_paradas(
            principal["geometria"]["coordinates"],
            principal["distancia_km"],
            autonomia_km,
            tipo_veiculo,
            margem_seguranca,
        )
    return resultado
