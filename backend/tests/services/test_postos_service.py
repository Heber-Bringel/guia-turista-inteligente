"""Testes das paradas: projeção pela autonomia (margem de 18%) e confirmação opcional por postos reais."""

import httpx
import pytest

from app.services.postos_service import (
    MAX_PARADAS,
    localizar_paradas_async,
    projetar_paradas,
)

# Linha reta Teresina -> Brasília com poucos vértices
TRAJETO = [[-42.801, -5.089], [-44.5, -9.0], [-46.0, -12.5], [-47.929, -15.779]]
DISTANCIA_KM = 1674.6


def test_projeta_uma_parada_a_cada_alcance_util_antes_do_destino() -> None:
    paradas = projetar_paradas(TRAJETO, DISTANCIA_KM, autonomia_km=500.0)

    # Alcance útil = 500 * (1 - 0,18) = 410 km; a parada de 1640 km ainda cabe antes dos 1674,6 km
    assert [p["distancia_origem_km"] for p in paradas] == [410.0, 820.0, 1230.0, 1640.0]
    assert len({p["id"] for p in paradas}) == 4
    assert all(p["estimada"] is True and p["visitado"] is False for p in paradas)


def test_paradas_ficam_dentro_da_caixa_da_rota_e_em_ordem() -> None:
    paradas = projetar_paradas(TRAJETO, DISTANCIA_KM, autonomia_km=500.0)

    latitudes = [p["latitude"] for p in paradas]
    assert latitudes == sorted(latitudes, reverse=True)  # a rota desce de -5 para -15,8
    assert all(-15.779 <= lat <= -5.089 for lat in latitudes)
    assert all(-47.929 <= p["longitude"] <= -42.801 for p in paradas)


@pytest.mark.parametrize("distancia_km", [300.0, 410.0])
def test_sem_parada_quando_o_destino_cabe_no_alcance_util(distancia_km: float) -> None:
    assert projetar_paradas(TRAJETO, distancia_km, autonomia_km=500.0) == []


def test_logo_acima_do_alcance_util_ja_exige_parada() -> None:
    # Chegar com menos de 18% de reserva não é aceitável: 415 km > 410 km
    paradas = projetar_paradas(TRAJETO, 415.0, autonomia_km=500.0)
    assert [p["distancia_origem_km"] for p in paradas] == [410.0]


def test_eletrico_usa_rotulo_de_recarga() -> None:
    paradas = projetar_paradas(TRAJETO, DISTANCIA_KM, autonomia_km=400.0, tipo_veiculo="eletrico")
    assert paradas[0]["nome"].startswith("Recarga estimada")


def test_combustao_usa_rotulo_de_abastecimento() -> None:
    assert projetar_paradas(TRAJETO, DISTANCIA_KM, autonomia_km=500.0)[0]["nome"].startswith("Abastecimento estimado")


def test_autonomia_irreal_nao_gera_centenas_de_marcadores() -> None:
    assert len(projetar_paradas(TRAJETO, DISTANCIA_KM, autonomia_km=10.0)) == MAX_PARADAS


@pytest.mark.parametrize(
    ("coordenadas", "distancia_km", "autonomia_km"),
    [([], 100.0, 500.0), (TRAJETO[:1], 100.0, 500.0), (TRAJETO, 0.0, 500.0), (TRAJETO, 100.0, 0.0)],
)
def test_entradas_invalidas_nao_geram_paradas(coordenadas: list[list[float]], distancia_km: float, autonomia_km: float) -> None:
    assert projetar_paradas(coordenadas, distancia_km, autonomia_km) == []


@pytest.mark.anyio
async def test_postos_encontrados_confirmam_as_paradas(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "overpass-api.de"
        assert 'amenity"="fuel' in request.content.decode().replace("%22", '"').replace("%3D", "=")
        elementos = [
            {"lat": -9.0, "lon": -44.0, "tags": {"name": "Posto Longe"}},
            {"lat": -7.001, "lon": -43.401, "tags": {"name": "Posto Ipiranga"}},
        ]
        return httpx.Response(200, json={"elements": elementos})

    async with criar_client(handler) as client:
        paradas = await localizar_paradas_async(client, TRAJETO, DISTANCIA_KM, autonomia_km=500.0)

    assert len(paradas) == 4
    assert all(p["estimada"] is False for p in paradas)
    assert all("km" in p["nome"] for p in paradas)
    assert all(p["id"].startswith("parada_posto_") for p in paradas)


@pytest.mark.anyio
async def test_escolhe_o_posto_mais_proximo_da_posicao_projetada(criar_client) -> None:
    projetadas = projetar_paradas(TRAJETO, 1000.0, autonomia_km=1000.0)  # alcance útil de 820 km: uma parada
    alvo = projetadas[0]

    def handler(request: httpx.Request) -> httpx.Response:
        perto = {"lat": alvo["latitude"] + 0.01, "lon": alvo["longitude"], "tags": {"name": "Posto Perto"}}
        longe = {"lat": alvo["latitude"] + 0.5, "lon": alvo["longitude"], "tags": {"name": "Posto Longe"}}
        return httpx.Response(200, json={"elements": [longe, perto]})

    async with criar_client(handler) as client:
        paradas = await localizar_paradas_async(client, TRAJETO, 1000.0, autonomia_km=1000.0)

    assert len(paradas) == 1
    assert paradas[0]["nome"] == "Posto Perto (km 820)"


@pytest.mark.anyio
async def test_eletrico_busca_eletropostos(criar_client) -> None:
    consultas: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        consultas.append(request.content.decode())
        return httpx.Response(200, json={"elements": [{"lat": -7.0, "lon": -43.4, "tags": {}}]})

    async with criar_client(handler) as client:
        paradas = await localizar_paradas_async(client, TRAJETO, DISTANCIA_KM, autonomia_km=1000.0, tipo_veiculo="eletrico")

    assert "charging_station" in consultas[0]
    assert paradas[0]["nome"].startswith("Eletroposto")  # sem `name` no OSM, usa o nome genérico


@pytest.mark.anyio
@pytest.mark.parametrize("resposta", [httpx.Response(429), httpx.Response(200, json={"elements": []}), httpx.Response(200, text="xml")])
async def test_overpass_indisponivel_mantem_paradas_estimadas(criar_client, resposta: httpx.Response) -> None:
    async with criar_client(lambda _: resposta) as client:
        paradas = await localizar_paradas_async(client, TRAJETO, DISTANCIA_KM, autonomia_km=500.0)

    assert len(paradas) == 4
    assert all(p["estimada"] is True for p in paradas)
    assert paradas[0]["nome"].startswith("Abastecimento estimado")


@pytest.mark.anyio
async def test_rota_curta_nao_consulta_o_overpass(criar_client) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("não deveria haver requisição")

    async with criar_client(handler) as client:
        assert await localizar_paradas_async(client, TRAJETO, 200.0, autonomia_km=500.0) == []
