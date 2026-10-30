"""Testes do roteamento OSRM: unidades, ordem lon/lat, escolha por preferência, alternativas e sem estrada."""

from typing import Any

import httpx
import pytest

from app.services.erros import ServicoIndisponivelError
from app.services.rota_service import (
    NOME_MAIS_ECONOMICA,
    NOME_MENOR_TEMPO,
    calcular_rota_osrm_async,
)

pytestmark = pytest.mark.anyio

# Teresina -> Brasília (latitude, longitude)
ORIGEM = (-5.089, -42.801)
DESTINO = (-15.779, -47.929)

# Duas rotas candidatas: A é a mais rápida; B é mais curta, porém mais lenta (8% a mais de tempo)
ROTA_A = {
    "distance": 1_700_000.0,
    "duration": 72_000.0,
    "geometry": {"type": "LineString", "coordinates": [[-42.801, -5.089], [-45.0, -10.0], [-47.929, -15.779]]},
}
ROTA_B = {
    "distance": 1_650_000.0,
    "duration": 78_000.0,
    "geometry": {"type": "LineString", "coordinates": [[-42.801, -5.089], [-44.0, -11.0], [-47.929, -15.779]]},
}


def _osrm(rotas: list[dict[str, Any]], snap: tuple[float, float] = (12.0, 30.0), code: str = "Ok") -> httpx.Response:
    return httpx.Response(
        200,
        json={"code": code, "routes": rotas, "waypoints": [{"distance": snap[0]}, {"distance": snap[1]}]},
    )


async def _calcular(criar_client, resposta: httpx.Response, **kwargs: Any) -> dict[str, Any]:
    async with criar_client(lambda _: resposta) as client:
        return await calcular_rota_osrm_async(client, *ORIGEM, *DESTINO, **kwargs)


async def test_requisicao_usa_longitude_primeiro_e_pede_geometria_geojson(criar_client) -> None:
    capturadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return _osrm([ROTA_A])

    async with criar_client(handler) as client:
        await calcular_rota_osrm_async(client, *ORIGEM, *DESTINO)

    assert capturadas[0].url.path.endswith("/-42.801,-5.089;-47.929,-15.779")
    assert capturadas[0].url.params["geometries"] == "geojson"
    assert capturadas[0].url.params["alternatives"] == "true"


async def test_converte_unidades_e_preserva_geometria_lon_lat(criar_client) -> None:
    rota = await _calcular(criar_client, _osrm([ROTA_A]))

    assert rota["distancia_km"] == 1700.0  # metros -> km
    assert rota["duracao_minutos"] == 1200.0  # segundos -> minutos
    assert rota["geometria"]["type"] == "LineString"
    assert rota["geometria"]["coordinates"][0] == [-42.801, -5.089]  # [longitude, latitude]
    assert rota["alternativas"] == []
    assert rota["nome"] == NOME_MENOR_TEMPO
    assert rota["paradas"] == []


async def test_rapida_escolhe_a_menor_duracao_e_lista_a_economica_como_alternativa(criar_client) -> None:
    rota = await _calcular(criar_client, _osrm([ROTA_B, ROTA_A]), preferencia="rapida")

    assert rota["distancia_km"] == 1700.0
    assert rota["nome"] == NOME_MENOR_TEMPO
    assert [alt["nome"] for alt in rota["alternativas"]] == [NOME_MAIS_ECONOMICA]
    alternativa = rota["alternativas"][0]
    assert (alternativa["distancia_km"], alternativa["duracao_minutos"]) == (1650.0, 1300.0)
    assert alternativa["geometria"]["coordinates"][1] == [-44.0, -11.0]


async def test_economica_escolhe_a_menor_distancia(criar_client) -> None:
    rota = await _calcular(criar_client, _osrm([ROTA_A, ROTA_B]), preferencia="economica")

    assert rota["distancia_km"] == 1650.0
    assert rota["nome"] == NOME_MAIS_ECONOMICA
    assert [alt["nome"] for alt in rota["alternativas"]] == [NOME_MENOR_TEMPO]


async def test_cenica_escolhe_a_mais_longa_dentro_da_tolerancia(criar_client) -> None:
    rota = await _calcular(criar_client, _osrm([ROTA_A, ROTA_B]), preferencia="cenica")

    assert rota["duracao_minutos"] == 1300.0  # 8% mais lenta que a rápida, abaixo do limite de 30%


async def test_cenica_ignora_alternativa_muito_mais_lenta(criar_client) -> None:
    lentissima = {**ROTA_B, "duration": 120_000.0}  # 67% mais lenta: acima da tolerância
    rota = await _calcular(criar_client, _osrm([ROTA_A, lentissima]), preferencia="cenica")

    assert rota["duracao_minutos"] == 1200.0


async def test_destino_sem_estrada_levanta_erro_de_rota_direta(criar_client) -> None:
    # Fernando de Noronha: o OSRM encaixa o ponto na costa a mais de 10 km
    with pytest.raises(ServicoIndisponivelError, match="Considere voos ou barcos"):
        await _calcular(criar_client, _osrm([ROTA_A], snap=(5.0, 45_000.0)))


async def test_codigo_diferente_de_ok_levanta_erro(criar_client) -> None:
    with pytest.raises(ServicoIndisponivelError, match="Sem rota direta"):
        await _calcular(criar_client, _osrm([], code="NoRoute"))


async def test_falha_http_levanta_erro_legivel(criar_client) -> None:
    with pytest.raises(ServicoIndisponivelError, match=r"OSRM indisponível \(HTTP 502\)"):
        await _calcular(criar_client, httpx.Response(502))


async def test_timeout_levanta_erro_legivel(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("", request=request)

    async with criar_client(handler) as client:
        with pytest.raises(ServicoIndisponivelError, match="tempo limite excedido"):
            await calcular_rota_osrm_async(client, *ORIGEM, *DESTINO)


async def test_coordenadas_zeradas_nao_consultam_o_osrm(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria haver requisição")

    async with criar_client(handler) as client:
        with pytest.raises(ServicoIndisponivelError, match="não geocodificado"):
            await calcular_rota_osrm_async(client, 0.0, 0.0, *DESTINO)


async def test_com_autonomia_projeta_paradas_estimadas_na_rota(criar_client) -> None:
    rota = await _calcular(criar_client, _osrm([ROTA_A]), autonomia_km=500.0)

    # Alcance útil = 500 * (1 - 0,18) = 410 km; 1700 km exigem paradas em 410, 820, 1230 e 1640
    assert [p["distancia_origem_km"] for p in rota["paradas"]] == [410.0, 820.0, 1230.0, 1640.0]
    assert all(p["estimada"] for p in rota["paradas"])
