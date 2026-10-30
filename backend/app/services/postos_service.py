"""Paradas de abastecimento/recarga: projeção pela autonomia e confirmação opcional via OpenStreetMap (Overpass)."""

import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging_config import logger
from app.services.geo_utils import (
    distancias_acumuladas_km,
    haversine_km,
    ponto_na_distancia,
)

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


async def _buscar_posto_proximo(
    client: httpx.AsyncClient, lat: float, lon: float, tag_amenity: str
) -> dict[str, Any] | None:
    """Consulta o Overpass e devolve o posto mais próximo do ponto, ou None se não houver ou o provedor falhar."""
    consulta = (
        f'[out:json][timeout:6];node["amenity"="{tag_amenity}"](around:{RAIO_BUSCA_M},{lat},{lon});out 10;'
    )
    try:
        resposta = await client.post(URL_OVERPASS, data={"data": consulta}, timeout=settings.TIMEOUT_ROTA)
        resposta.raise_for_status()
        elementos = resposta.json().get("elements") or []
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Overpass indisponível para (%s, %s): %s", lat, lon, type(exc).__name__)
        return None

    candidatos = [e for e in elementos if "lat" in e and "lon" in e]
    if not candidatos:
        return None
    return min(candidatos, key=lambda e: haversine_km(lat, lon, e["lat"], e["lon"]))


async def localizar_paradas_async(
    client: httpx.AsyncClient,
    coordenadas: list[list[float]],
    distancia_km: float,
    autonomia_km: float,
    tipo_veiculo: str = "gasolina",
) -> list[dict[str, Any]]:
    """Projeta as paradas e tenta confirmar cada uma com um posto real (em paralelo).

    Parada confirmada: `estimada=False`, com nome e coordenadas do posto (até `RAIO_BUSCA_M` da rota).
    Sem resposta do Overpass, a parada permanece com a posição projetada e `estimada=True`.
    """
    paradas = projetar_paradas(coordenadas, distancia_km, autonomia_km, tipo_veiculo)
    if not paradas:
        return []

    _, tag_amenity, nome_generico = _rotulos(tipo_veiculo)
    achados = await asyncio.gather(
        *(_buscar_posto_proximo(client, p["latitude"], p["longitude"], tag_amenity) for p in paradas)
    )

    for parada, posto in zip(paradas, achados):
        if posto is None:
            continue
        nome = (posto.get("tags") or {}).get("name") or nome_generico
        parada["nome"] = f"{nome} (km {round(parada['distancia_origem_km'])})"
        parada["latitude"] = round(float(posto["lat"]), 5)
        parada["longitude"] = round(float(posto["lon"]), 5)
        parada["id"] = parada["id"].replace("estimada", "posto")
        parada["estimada"] = False
    return paradas
