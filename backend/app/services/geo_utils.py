"""Funções geométricas puras sobre polilinhas GeoJSON, cujas coordenadas seguem a ordem [longitude, latitude]."""

import math
from itertools import pairwise

RAIO_TERRA_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância em km, sobre a esfera, entre dois pontos dados em graus."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * RAIO_TERRA_KM * math.asin(min(1.0, math.sqrt(a)))


def distancias_acumuladas_km(coordenadas: list[list[float]]) -> list[float]:
    """Distância percorrida desde o primeiro ponto até cada vértice (o primeiro vale 0.0)."""
    acumuladas = [0.0]
    for (lon_a, lat_a), (lon_b, lat_b) in pairwise(coordenadas):
        acumuladas.append(acumuladas[-1] + haversine_km(lat_a, lon_a, lat_b, lon_b))
    return acumuladas


def ponto_na_distancia(
    coordenadas: list[list[float]], acumuladas: list[float], alvo_km: float
) -> tuple[float, float]:
    """Interpola linearmente o ponto (latitude, longitude) situado a `alvo_km` do início da polilinha."""
    if alvo_km <= 0.0:
        return coordenadas[0][1], coordenadas[0][0]
    if alvo_km >= acumuladas[-1]:
        return coordenadas[-1][1], coordenadas[-1][0]

    # Busca binária do segmento que contém o alvo
    baixo, alto = 0, len(acumuladas) - 1
    while alto - baixo > 1:
        meio = (baixo + alto) // 2
        if acumuladas[meio] <= alvo_km:
            baixo = meio
        else:
            alto = meio

    trecho = acumuladas[alto] - acumuladas[baixo]
    fracao = (alvo_km - acumuladas[baixo]) / trecho if trecho > 0 else 0.0
    lon = coordenadas[baixo][0] + (coordenadas[alto][0] - coordenadas[baixo][0]) * fracao
    lat = coordenadas[baixo][1] + (coordenadas[alto][1] - coordenadas[baixo][1]) * fracao
    return lat, lon
