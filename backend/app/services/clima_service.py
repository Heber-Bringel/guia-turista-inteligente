"""Serviço assíncrono de telemetria climática (Open-Meteo Forecast)."""

from typing import Any

import httpx

from app.core.config import settings
from app.services.erros import ServicoIndisponivelError, falha_http

URL_FORECAST = "https://api.open-meteo.com/v1/forecast"

# Códigos WMO de `weather_code` -> descrição em português
DESCRICAO_WMO: dict[int, str] = {
    0: "Céu limpo",
    1: "Predominantemente limpo",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Nevoeiro",
    48: "Nevoeiro com geada",
    51: "Garoa leve",
    53: "Garoa moderada",
    55: "Garoa intensa",
    56: "Garoa congelante leve",
    57: "Garoa congelante intensa",
    61: "Chuva fraca",
    63: "Chuva moderada",
    65: "Chuva forte",
    66: "Chuva congelante leve",
    67: "Chuva congelante forte",
    71: "Neve fraca",
    73: "Neve moderada",
    75: "Neve forte",
    77: "Grãos de neve",
    80: "Pancadas de chuva fracas",
    81: "Pancadas de chuva moderadas",
    82: "Pancadas de chuva violentas",
    85: "Pancadas de neve fracas",
    86: "Pancadas de neve fortes",
    95: "Trovoadas",
    96: "Trovoadas com granizo leve",
    99: "Trovoadas com granizo forte",
}


def descrever_codigo_wmo(codigo: int | None) -> str:
    """Traduz o `weather_code` WMO; códigos desconhecidos viram uma descrição neutra."""
    if codigo is None:
        return "Condição não informada"
    return DESCRICAO_WMO.get(int(codigo), "Condição não informada")


async def obter_clima_async(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
    """Consulta o clima atual no ponto dado.

    Unidades: temperatura e sensação em °C, umidade em %, vento em km/h.
    Levanta `ServicoIndisponivelError` (coordenadas zeradas, timeout, HTTP de erro ou dados incompletos),
    para que o roteador marque o provedor como indisponível e siga com degradação controlada.
    """
    if lat == 0.0 and lon == 0.0:
        raise ServicoIndisponivelError("Clima indisponível (destino não geocodificado)")

    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    }

    try:
        resposta = await client.get(URL_FORECAST, params=params, timeout=settings.TIMEOUT_CLIMA)
        resposta.raise_for_status()
        atual = resposta.json().get("current") or {}
    except (httpx.HTTPError, ValueError) as exc:
        raise falha_http("Open-Meteo", exc) from exc

    temperatura = atual.get("temperature_2m")
    umidade = atual.get("relative_humidity_2m")
    vento = atual.get("wind_speed_10m")
    if temperatura is None or umidade is None or vento is None:
        raise ServicoIndisponivelError("Open-Meteo devolveu dados climáticos incompletos")

    return {
        "temperatura_c": float(temperatura),
        "sensacao_termica_c": float(atual["apparent_temperature"]) if atual.get("apparent_temperature") is not None else None,
        "umidade_percentual": float(umidade),
        "vento_kmh": float(vento),
        "descricao": descrever_codigo_wmo(atual.get("weather_code")),
    }
