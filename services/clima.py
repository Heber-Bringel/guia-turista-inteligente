"""Serviço de telemetria climática (Open-Meteo Forecast)."""

import httpx


def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Consulta o Open-Meteo Forecast e retorna temperatura (°C), umidade (%) e vento (km/h).

    Caso coordenadas sejam inválidas (0.0, 0.0) ou ocorra timeout (4.0s),
    retorna dicionário de contingência com valores 'N/D'.
    """
    fallback = {
        "temperatura": "N/D",
        "umidade": "N/D",
        "vento": "N/D",
    }

    # Validação rápida de coordenadas zeradas
    if lat == 0.0 and lon == 0.0:
        return fallback

    url = "https://api.open-meteo.com/v1/forecast"
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
    }

    try:
        resposta = client.get(url, params=params, timeout=4.0)
        resposta.raise_for_status()
        dados = resposta.json()
        current = dados.get("current", {})

        temperatura = current.get("temperature_2m")
        umidade = current.get("relative_humidity_2m")
        vento = current.get("wind_speed_10m")

        if temperatura is None or umidade is None or vento is None:
            return fallback

        return {
            "temperatura": f"{temperatura} °C",
            "umidade": f"{umidade}%",
            "vento": f"{vento} km/h",
        }

    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001
        return fallback
