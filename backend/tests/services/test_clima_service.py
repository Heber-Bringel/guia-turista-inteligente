"""Testes do serviço de clima: unidades numéricas, descrição WMO e falhas que levantam erro legível."""

import httpx
import pytest

from app.services.clima_service import descrever_codigo_wmo, obter_clima_async
from app.services.erros import ServicoIndisponivelError

pytestmark = pytest.mark.anyio

ATUAL = {
    "temperature_2m": 31.4,
    "apparent_temperature": 34.0,
    "relative_humidity_2m": 38,
    "wind_speed_10m": 12.5,
    "weather_code": 0,
}


async def test_devolve_valores_numericos_e_descricao_em_portugues(criar_client) -> None:
    capturadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return httpx.Response(200, json={"current": ATUAL})

    async with criar_client(handler) as client:
        clima = await obter_clima_async(client, -15.779, -47.929)

    assert clima == {
        "temperatura_c": 31.4,
        "sensacao_termica_c": 34.0,
        "umidade_percentual": 38.0,
        "vento_kmh": 12.5,
        "descricao": "Céu limpo",
    }
    parametros = capturadas[0].url.params
    assert parametros["latitude"] == "-15.779"
    assert parametros["longitude"] == "-47.929"
    assert parametros["wind_speed_unit"] == "kmh"
    assert "weather_code" in parametros["current"]


async def test_sensacao_termica_ausente_vira_none(criar_client) -> None:
    atual = {k: v for k, v in ATUAL.items() if k != "apparent_temperature"}
    async with criar_client(lambda _: httpx.Response(200, json={"current": atual})) as client:
        clima = await obter_clima_async(client, -5.0, -42.0)

    assert clima["sensacao_termica_c"] is None


async def test_coordenadas_zeradas_nao_consultam_a_api(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria haver requisição")

    async with criar_client(handler) as client:
        with pytest.raises(ServicoIndisponivelError, match="não geocodificado"):
            await obter_clima_async(client, 0.0, 0.0)


async def test_timeout_vira_erro_com_mensagem_legivel(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("", request=request)

    async with criar_client(handler) as client:
        with pytest.raises(ServicoIndisponivelError, match=r"Open-Meteo indisponível \(tempo limite excedido\)"):
            await obter_clima_async(client, -5.0, -42.0)


async def test_http_de_erro_informa_o_status(criar_client) -> None:
    async with criar_client(lambda _: httpx.Response(503)) as client:
        with pytest.raises(ServicoIndisponivelError, match="HTTP 503"):
            await obter_clima_async(client, -5.0, -42.0)


async def test_dados_incompletos_levantam_erro(criar_client) -> None:
    async with criar_client(lambda _: httpx.Response(200, json={"current": {"temperature_2m": 20}})) as client:
        with pytest.raises(ServicoIndisponivelError, match="incompletos"):
            await obter_clima_async(client, -5.0, -42.0)


@pytest.mark.parametrize(
    ("codigo", "texto"),
    [(0, "Céu limpo"), (95, "Trovoadas"), (999, "Condição não informada"), (None, "Condição não informada")],
)
def test_descrever_codigo_wmo(codigo: int | None, texto: str) -> None:
    assert descrever_codigo_wmo(codigo) == texto
