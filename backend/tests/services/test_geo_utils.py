"""Testes das funções geométricas: haversine, distância acumulada e interpolação na polilinha."""

import pytest

from app.services.geo_utils import (
    distancias_acumuladas_km,
    haversine_km,
    ponto_na_distancia,
)


def test_haversine_teresina_brasilia_em_linha_reta() -> None:
    distancia = haversine_km(-5.089, -42.801, -15.779, -47.929)
    assert 1100 < distancia < 1400  # a rota rodoviária (~1.670 km) é maior que a linha reta


def test_haversine_mesmo_ponto_vale_zero() -> None:
    assert haversine_km(-5.0, -42.0, -5.0, -42.0) == 0.0


def test_distancias_acumuladas_crescem_e_comecam_em_zero() -> None:
    acumuladas = distancias_acumuladas_km([[-42.0, -5.0], [-42.0, -6.0], [-42.0, -7.0]])
    assert acumuladas[0] == 0.0
    assert acumuladas[1] == pytest.approx(111.2, abs=0.5)  # 1 grau de latitude ~ 111 km
    assert acumuladas[2] == pytest.approx(2 * acumuladas[1], rel=1e-6)


def test_ponto_na_distancia_interpola_no_meio_do_segmento() -> None:
    coordenadas = [[-42.0, -5.0], [-42.0, -7.0]]
    acumuladas = distancias_acumuladas_km(coordenadas)
    lat, lon = ponto_na_distancia(coordenadas, acumuladas, acumuladas[-1] / 2)
    assert lat == pytest.approx(-6.0, abs=1e-6)
    assert lon == pytest.approx(-42.0)


def test_ponto_na_distancia_limita_nas_extremidades() -> None:
    coordenadas = [[-42.0, -5.0], [-43.0, -6.0]]
    acumuladas = distancias_acumuladas_km(coordenadas)
    assert ponto_na_distancia(coordenadas, acumuladas, -10) == (-5.0, -42.0)
    assert ponto_na_distancia(coordenadas, acumuladas, 99999) == (-6.0, -43.0)
