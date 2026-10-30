"""Serviço assíncrono de altimetria: perfil de elevação, ganho/perda e impacto estimado no consumo."""

from itertools import pairwise
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging_config import logger
from app.services.erros import ServicoIndisponivelError, falha_http
from app.services.geo_utils import distancias_acumuladas_km, ponto_na_distancia

URL_OPEN_ELEVATION = "https://api.open-elevation.com/api/v1/lookup"
URL_OPEN_METEO_ELEVATION = "https://api.open-meteo.com/v1/elevation"

# Uma amostra de elevação a cada ~10 km de rota, entre 2 e 100 pontos (limite de uma requisição às APIs)
ESPACAMENTO_AMOSTRAS_KM = 10.0
MIN_AMOSTRAS = 2
MAX_AMOSTRAS = 100

# Modelo de impacto no consumo (ordem de grandeza para um carro de ~1,4 t, não uma medição):
# cada metro de subida líquida por km rodado soma ~2% de consumo; a descida devolve 30% da subida (inércia),
# e o acréscimo é limitado a 25%.
PENALIZACAO_PCT_POR_METRO_POR_KM = 2.0
CREDITO_DESCIDA = 0.30
IMPACTO_MAXIMO_PERCENTUAL = 25.0


def _amostrar_rota(coordenadas: list[list[float]]) -> list[tuple[float, float, float]]:
    """Seleciona pontos (distancia_km, latitude, longitude) igualmente espaçados ao longo da rota."""
    acumuladas = distancias_acumuladas_km(coordenadas)
    total = acumuladas[-1]
    quantidade = min(MAX_AMOSTRAS, max(MIN_AMOSTRAS, int(total / ESPACAMENTO_AMOSTRAS_KM) + 2))
    amostras = []
    for i in range(quantidade):
        alvo = total * i / (quantidade - 1)
        lat, lon = ponto_na_distancia(coordenadas, acumuladas, alvo)
        amostras.append((alvo, lat, lon))
    return amostras


async def _elevacoes_open_elevation(client: httpx.AsyncClient, pontos: list[tuple[float, float, float]]) -> list[float]:
    corpo = {"locations": [{"latitude": lat, "longitude": lon} for _, lat, lon in pontos]}
    resposta = await client.post(URL_OPEN_ELEVATION, json=corpo, timeout=min(settings.TIMEOUT_ROTA, 2.0))
    resposta.raise_for_status()
    return [float(item["elevation"]) for item in resposta.json()["results"]]


async def _elevacoes_open_meteo(client: httpx.AsyncClient, pontos: list[tuple[float, float, float]]) -> list[float]:
    params = {
        "latitude": ",".join(f"{lat:.5f}" for _, lat, _ in pontos),
        "longitude": ",".join(f"{lon:.5f}" for _, _, lon in pontos),
    }
    resposta = await client.get(URL_OPEN_METEO_ELEVATION, params=params, timeout=settings.TIMEOUT_ROTA)
    resposta.raise_for_status()
    return [float(valor) for valor in resposta.json()["elevation"]]


def estimar_impacto_consumo(ganho_m: float, perda_m: float, distancia_km: float) -> float:
    """Percentual de consumo extra causado pelo relevo (0 a 25), segundo o modelo documentado no módulo."""
    if distancia_km <= 0:
        return 0.0
    subida_liquida = max(ganho_m - CREDITO_DESCIDA * perda_m, 0.0)
    impacto = subida_liquida / distancia_km * PENALIZACAO_PCT_POR_METRO_POR_KM
    return round(min(impacto, IMPACTO_MAXIMO_PERCENTUAL), 1)


async def calcular_altimetria_async(client: httpx.AsyncClient, coordenadas: list[list[float]]) -> dict[str, Any]:
    """Calcula o perfil altimétrico da rota (coordenadas GeoJSON [longitude, latitude]).

    Consulta a Open-Elevation e, se ela falhar, a Open-Meteo Elevation. Retorna `ganho_m` e `perda_m`
    (somas das subidas e descidas entre amostras, em metros), `altitude_maxima_m`, `altitude_minima_m`,
    `desnivel_liquido_m`, `impacto_consumo_percentual` e `perfil` (lista de {distancia_km, altitude_m, ...}).
    A amostragem (~1 ponto a cada 10 km) subestima morros menores que o espaçamento.
    Levanta `ServicoIndisponivelError` se não houver rota ou se as duas fontes falharem.
    """
    if len(coordenadas) < 2:
        raise ServicoIndisponivelError("Altimetria indisponível (rota sem geometria)")

    pontos = _amostrar_rota(coordenadas)
    fonte = "Open-Elevation"
    try:
        elevacoes = await _elevacoes_open_elevation(client, pontos)
    except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc:
        logger.warning("Open-Elevation indisponível (%s). Tentando Open-Meteo Elevation.", type(exc).__name__)
        fonte = "Open-Meteo Elevation"
        try:
            elevacoes = await _elevacoes_open_meteo(client, pontos)
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as exc_reserva:
            raise falha_http("Altimetria (Open-Elevation e Open-Meteo)", exc_reserva) from exc_reserva

    if len(elevacoes) != len(pontos):
        raise ServicoIndisponivelError("Altimetria devolveu quantidade de pontos diferente da enviada")

    ganho = perda = 0.0
    for anterior, atual in pairwise(elevacoes):
        delta = atual - anterior
        if delta > 0:
            ganho += delta
        else:
            perda += -delta

    distancia_total = pontos[-1][0]
    return {
        "ganho_m": round(ganho, 1),
        "perda_m": round(perda, 1),
        "altitude_maxima_m": round(max(elevacoes), 1),
        "altitude_minima_m": round(min(elevacoes), 1),
        "desnivel_liquido_m": round(elevacoes[-1] - elevacoes[0], 1),
        "impacto_consumo_percentual": estimar_impacto_consumo(ganho, perda, distancia_total),
        "fonte": fonte,
        "perfil": [
            {
                "distancia_km": round(d, 1),
                "altitude_m": round(alt, 1),
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
            }
            for (d, lat, lon), alt in zip(pontos, elevacoes)
        ],
    }
