"""Testes da altimetria: ganho/perda, amostragem, fallback entre provedores e modelo de impacto no consumo."""

import json
from typing import Any

import httpx
import pytest

from app.services.altimetria_service import (
    IMPACTO_MAXIMO_PERCENTUAL,
    MAX_AMOSTRAS,
    calcular_altimetria_async,
    estimar_impacto_consumo,
)
from app.services.erros import ServicoIndisponivelError

pytestmark = pytest.mark.anyio

# ~27,8 km em linha reta (0,25 grau de latitude): 4 amostras, uma a cada ~9,3 km
ROTA_CURTA = [[-42.8, -5.0], [-42.8, -5.25]]
# ~3.300 km entre o Piauí e Mato Grosso do Sul: satura no máximo de 100 amostras
ROTA_LONGA = [[-35.0, -5.0], [-60.0, -25.0]]


def _open_elevation(elevacoes: list[float]):
    def handler(request: httpx.Request) -> httpx.Response:
        locais = json.loads(request.content)["locations"]
        assert len(locais) == len(elevacoes)
        return httpx.Response(200, json={"results": [{"elevation": e} for e in elevacoes]})

    return handler


async def test_calcula_ganho_perda_e_extremos(criar_client) -> None:
    # 100 -> 300 (+200) -> 250 (-50) -> 400 (+150)
    async with criar_client(_open_elevation([100, 300, 250, 400])) as client:
        resultado = await calcular_altimetria_async(client, ROTA_CURTA)

    assert resultado["ganho_m"] == 350.0
    assert resultado["perda_m"] == 50.0
    assert resultado["altitude_maxima_m"] == 400.0
    assert resultado["altitude_minima_m"] == 100.0
    assert resultado["desnivel_liquido_m"] == 300.0
    assert resultado["fonte"] == "Open-Elevation"


async def test_perfil_tem_distancia_crescente_e_coordenadas_da_rota(criar_client) -> None:
    async with criar_client(_open_elevation([100, 300, 250, 400])) as client:
        perfil = (await calcular_altimetria_async(client, ROTA_CURTA))["perfil"]

    assert [p["altitude_m"] for p in perfil] == [100.0, 300.0, 250.0, 400.0]
    distancias = [p["distancia_km"] for p in perfil]
    assert distancias[0] == 0.0
    assert distancias == sorted(distancias)
    assert distancias[-1] == pytest.approx(27.8, abs=0.5)
    assert perfil[0]["latitude"] == -5.0 and perfil[-1]["latitude"] == -5.25


async def test_envia_latitude_e_longitude_nos_campos_certos(criar_client) -> None:
    corpos: list[Any] = []

    def handler(request: httpx.Request) -> httpx.Response:
        corpos.append(json.loads(request.content))
        return httpx.Response(200, json={"results": [{"elevation": 0}] * len(corpos[0]["locations"])})

    async with criar_client(handler) as client:
        await calcular_altimetria_async(client, ROTA_CURTA)

    primeiro = corpos[0]["locations"][0]
    assert primeiro == {"latitude": -5.0, "longitude": -42.8}  # a rota vem como [lon, lat]


async def test_rota_longa_limita_a_quantidade_de_amostras(criar_client) -> None:
    async with criar_client(_open_elevation([0.0] * MAX_AMOSTRAS)) as client:
        resultado = await calcular_altimetria_async(client, ROTA_LONGA)

    assert len(resultado["perfil"]) == MAX_AMOSTRAS


async def test_open_elevation_fora_do_ar_usa_open_meteo(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.open-elevation.com":
            return httpx.Response(504)
        assert len(request.url.params["latitude"].split(",")) == 4
        return httpx.Response(200, json={"elevation": [10, 20, 15, 30]})

    async with criar_client(handler) as client:
        resultado = await calcular_altimetria_async(client, ROTA_CURTA)

    assert resultado["fonte"] == "Open-Meteo Elevation"
    assert resultado["ganho_m"] == 25.0 and resultado["perda_m"] == 5.0


async def test_resposta_malformada_tambem_aciona_o_provedor_reserva(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.open-elevation.com":
            return httpx.Response(200, json={"inesperado": True})
        return httpx.Response(200, json={"elevation": [1, 2, 3, 4]})

    async with criar_client(handler) as client:
        assert (await calcular_altimetria_async(client, ROTA_CURTA))["fonte"] == "Open-Meteo Elevation"


async def test_os_dois_provedores_fora_do_ar_levantam_erro_legivel(criar_client) -> None:
    async with criar_client(lambda _: httpx.Response(500)) as client:
        with pytest.raises(ServicoIndisponivelError, match="Altimetria"):
            await calcular_altimetria_async(client, ROTA_CURTA)


async def test_quantidade_de_pontos_diferente_da_enviada_levanta_erro(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [{"elevation": 1}]})

    async with criar_client(handler) as client:
        with pytest.raises(ServicoIndisponivelError, match="quantidade de pontos"):
            await calcular_altimetria_async(client, ROTA_CURTA)


@pytest.mark.parametrize("coordenadas", [[], [[-42.8, -5.0]]])
async def test_rota_sem_geometria_nao_consulta_a_api(criar_client, coordenadas: list[list[float]]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria haver requisição")

    async with criar_client(handler) as client:
        with pytest.raises(ServicoIndisponivelError, match="sem geometria"):
            await calcular_altimetria_async(client, coordenadas)


def test_impacto_consumo_segue_o_modelo_documentado() -> None:
    # (850 - 0,3 * 220) m de subida líquida / 1674 km * 2% por (m/km) = ~0,9%
    assert estimar_impacto_consumo(850.0, 220.0, 1674.0) == 0.9
    # Serra forte: 1000 m de subida em 100 km = 10 m/km = 20%
    assert estimar_impacto_consumo(1000.0, 0.0, 100.0) == 20.0


def test_impacto_consumo_tem_teto_e_nunca_e_negativo() -> None:
    assert estimar_impacto_consumo(5000.0, 0.0, 50.0) == IMPACTO_MAXIMO_PERCENTUAL
    assert estimar_impacto_consumo(0.0, 800.0, 100.0) == 0.0  # só descida: sem penalização
    assert estimar_impacto_consumo(100.0, 0.0, 0.0) == 0.0
