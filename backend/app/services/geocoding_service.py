"""Serviço assíncrono de geocodificação (Open-Meteo Geocoding) com normalização da UF."""

import unicodedata
from typing import Any

import httpx

from app.core.catalogo import COORDS_CAPITAIS, ESTADOS_BRASIL
from app.core.config import settings
from app.core.logging_config import logger

URL_GEOCODING = "https://geocoding-api.open-meteo.com/v1/search"


def _normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para comparação robusta."""
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower().strip()


def obter_sigla_uf(admin1: str, uf_informada: str = "") -> str:
    """Converte o estado retornado pela API (`admin1`) na sigla oficial de 2 letras (ex: 'Piauí' -> 'PI').

    Se o `admin1` já for uma sigla válida, devolve ela; senão usa a UF informada, se válida; senão ''.
    """
    admin1_normalizado = _normalizar(admin1)
    for sigla, nome in ESTADOS_BRASIL.items():
        if _normalizar(nome) == admin1_normalizado:
            return sigla

    admin1_upper = admin1.strip().upper()
    if admin1_upper in ESTADOS_BRASIL:
        return admin1_upper

    uf_upper = uf_informada.strip().upper()
    if uf_upper in ESTADOS_BRASIL:
        return uf_upper

    return ""


def _escolher_resultado(resultados: list[dict[str, Any]], uf: str) -> dict[str, Any]:
    """Escolhe entre os candidatos o que pertence à UF informada (via `admin1`), tratando homônimos.

    Se nenhum candidato estiver na UF digitada, devolve o primeiro (o mais relevante para a API):
    é assim que uma UF errada (ex: Teresina / RJ) acaba corrigida pela UF real da cidade.
    """
    uf_informada = uf.strip().upper()
    for candidato in resultados:
        if obter_sigla_uf(str(candidato.get("admin1", ""))) == uf_informada:
            return candidato
    return resultados[0]


def eh_coordenada_de_fallback(lat: float, lon: float, uf: str) -> bool:
    """Indica se as coordenadas vieram do fallback (cidade não localizada): capital da UF ou (0.0, 0.0)."""
    if lat == 0.0 and lon == 0.0:
        return True
    return COORDS_CAPITAIS.get(uf.strip().upper()) == (lat, lon)


async def buscar_coordenadas_async(
    client: httpx.AsyncClient, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Geocodifica uma cidade brasileira e devolve (latitude, longitude, uf_oficial_detectada).

    Usa o `httpx.AsyncClient` recebido (pool compartilhado) com o timeout `TIMEOUT_GEOCODING`.
    Nunca levanta exceção: se a cidade não for localizada ou o provedor falhar, devolve as
    coordenadas da capital da UF informada (ver `eh_coordenada_de_fallback`).
    """
    # A API aceita o nome da cidade sozinho ("cidade + UF" no mesmo texto não devolve resultados)
    # e o filtro de país se chama `countryCode` (o parâmetro `country_codes` é ignorado).
    params: dict[str, str | int] = {
        "name": cidade.strip(),
        "count": 10,
        "language": "pt",
        "countryCode": "BR",
    }

    try:
        resposta = await client.get(URL_GEOCODING, params=params, timeout=settings.TIMEOUT_GEOCODING)
        resposta.raise_for_status()
        resultados = resposta.json().get("results")

        if resultados:
            escolhido = _escolher_resultado(resultados, uf)
            lat = float(escolhido.get("latitude", 0.0))
            lon = float(escolhido.get("longitude", 0.0))
            uf_detectada = obter_sigla_uf(str(escolhido.get("admin1", "")), uf)
            return lat, lon, uf_detectada
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("Geocoding de '%s/%s' indisponível (%s). Usando fallback.", cidade, uf, exc)

    uf_upper = uf.strip().upper()
    if uf_upper in COORDS_CAPITAIS:
        lat_cap, lon_cap = COORDS_CAPITAIS[uf_upper]
        return lat_cap, lon_cap, uf_upper

    return 0.0, 0.0, uf_upper
