"""Testes do geocoding assíncrono: filtro de país, homônimos, correção de UF e fallback das capitais."""

import httpx
import pytest

from app.services.geocoding_service import (
    buscar_coordenadas_async,
    eh_coordenada_de_fallback,
    obter_sigla_uf,
)

pytestmark = pytest.mark.anyio


def _resposta(resultados: list[dict[str, object]]) -> httpx.Response:
    return httpx.Response(200, json={"results": resultados})


@pytest.mark.parametrize(
    ("admin1", "uf_informada", "esperado"),
    [("Piauí", "", "PI"), ("Ceara", "", "CE"), ("DF", "", "DF"), ("Inexistente", "sp", "SP"), ("Inexistente", "", "")],
)
def test_obter_sigla_uf(admin1: str, uf_informada: str, esperado: str) -> None:
    assert obter_sigla_uf(admin1, uf_informada) == esperado


async def test_consulta_usa_filtro_de_pais_e_apenas_o_nome_da_cidade(criar_client) -> None:
    capturadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return _resposta([{"latitude": -5.089, "longitude": -42.801, "admin1": "Piauí"}])

    async with criar_client(handler) as client:
        await buscar_coordenadas_async(client, "  Teresina ", "PI")

    parametros = capturadas[0].url.params
    assert parametros["countryCode"] == "BR"
    assert parametros["name"] == "Teresina"  # sem a UF e sem espaços nas pontas
    assert parametros["count"] == "10"


async def test_escolhe_o_homonimo_da_uf_informada(criar_client) -> None:
    candidatos = [
        {"latitude": -7.0, "longitude": -35.0, "admin1": "Paraíba"},
        {"latitude": -29.68, "longitude": -53.8, "admin1": "Rio Grande do Sul"},
    ]
    async with criar_client(lambda _: _resposta(candidatos)) as client:
        lat, lon, uf = await buscar_coordenadas_async(client, "Santa Maria", "RS")

    assert (lat, lon, uf) == (-29.68, -53.8, "RS")


async def test_uf_errada_e_corrigida_pela_uf_real_da_cidade(criar_client) -> None:
    candidatos = [{"latitude": -5.089, "longitude": -42.801, "admin1": "Piauí"}]
    async with criar_client(lambda _: _resposta(candidatos)) as client:
        lat, lon, uf = await buscar_coordenadas_async(client, "Teresina", "RJ")

    assert (lat, lon, uf) == (-5.089, -42.801, "PI")


@pytest.mark.parametrize(
    "handler",
    [
        lambda _: httpx.Response(200, json={}),
        lambda _: httpx.Response(500),
        lambda _: httpx.Response(200, text="isto não é JSON"),
    ],
    ids=["sem-resultados", "http-500", "json-invalido"],
)
async def test_falha_ou_cidade_ausente_cai_na_capital_da_uf(criar_client, handler) -> None:
    async with criar_client(handler) as client:
        lat, lon, uf = await buscar_coordenadas_async(client, "Cidade Inexistente", "pi")

    assert (lat, lon, uf) == (-5.089, -42.801, "PI")  # capital: Teresina
    assert eh_coordenada_de_fallback(lat, lon, uf)


async def test_timeout_do_provedor_nao_levanta_excecao(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("lento demais", request=request)

    async with criar_client(handler) as client:
        resultado = await buscar_coordenadas_async(client, "Brasília", "DF")

    assert resultado == (-15.779, -47.929, "DF")


async def test_uf_desconhecida_sem_resultado_devolve_coordenadas_zeradas(criar_client) -> None:
    async with criar_client(lambda _: httpx.Response(200, json={})) as client:
        lat, lon, uf = await buscar_coordenadas_async(client, "Lugar Nenhum", "")

    assert (lat, lon, uf) == (0.0, 0.0, "")
    assert eh_coordenada_de_fallback(lat, lon, uf)


def test_coordenada_exata_da_cidade_nao_e_fallback() -> None:
    assert not eh_coordenada_de_fallback(-5.1234, -42.5678, "PI")
