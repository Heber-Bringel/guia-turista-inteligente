"""Integração dos serviços de dados com o roteador: assinaturas compatíveis e pipeline completo sem rede."""

import json
import xml.etree.ElementTree as ET
from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.circuit_breaker import CIRCUIT_BREAKERS, CircuitState
from app.routers import roteiros as roteiros_module
from app.services.gemini_service import gerar_guia_contingencia

HEADERS = {"X-User-Id": "usr_teste_douglas"}

SERVICOS_DO_ROTEADOR = [
    "buscar_coordenadas_async",
    "obter_clima_async",
    "calcular_rota_osrm_async",
    "calcular_altimetria_async",
    "calcular_custos_async",
    "gerar_guia_ia_com_diagnostico_async",
    "gerar_guia_ia_stream_async",
    "gerar_gpx_async",
]

PAYLOAD = {
    "origem_cidade": "Teresina",
    "origem_uf": "PI",
    "destino_cidade": "Brasília",
    "destino_uf": "DF",
    "dias_estadia": 2,
    "estilo_viagem": "cultural",
    "preferencia_rota": "rapida",
    "tipo_veiculo": "gasolina",
    "consumo_medio": 12.0,
    "autonomia_km": 500.0,
    "capacidade_veiculo": 50.0,
    "preco_unidade": 5.89,
    "passageiros": 2,
}

GEOMETRIA = [[-42.801, -5.089], [-44.5, -9.0], [-46.0, -12.5], [-47.929, -15.779]]
ALTERNATIVA = [[-42.801, -5.089], [-43.9, -10.0], [-47.929, -15.779]]


def _provedores_simulados(request: httpx.Request) -> httpx.Response:
    """Responde por host como as APIs reais; qualquer host inesperado derruba o teste."""
    host = request.url.host
    if host == "geocoding-api.open-meteo.com":
        cidades = {
            "Teresina": {"latitude": -5.089, "longitude": -42.801, "admin1": "Piauí"},
            "Brasília": {"latitude": -15.779, "longitude": -47.929, "admin1": "Distrito Federal"},
        }
        return httpx.Response(200, json={"results": [cidades[request.url.params["name"]]]})
    if host == "api.open-meteo.com":
        atual = {"temperature_2m": 31.4, "apparent_temperature": 34.0, "relative_humidity_2m": 38, "wind_speed_10m": 12.5, "weather_code": 1}
        return httpx.Response(200, json={"current": atual})
    if host == "router.project-osrm.org":
        rota = {"distance": 1_674_600.0, "duration": 77_880.0, "geometry": {"type": "LineString", "coordinates": GEOMETRIA}}
        curta = {"distance": 1_650_000.0, "duration": 80_000.0, "geometry": {"type": "LineString", "coordinates": ALTERNATIVA}}
        return httpx.Response(200, json={"code": "Ok", "routes": [rota, curta], "waypoints": [{"distance": 5.0}, {"distance": 9.0}]})
    if host == "overpass-api.de":
        posto = {"lat": -9.0, "lon": -44.0, "tags": {"name": "Posto Teste"}}
        return httpx.Response(200, json={"elements": [posto]})
    if host == "api.open-elevation.com":
        locais = json.loads(request.content)["locations"]
        # Sobe de 100 m a cada amostra: o ganho total é conhecido
        return httpx.Response(200, json={"results": [{"elevation": 100.0 + 10.0 * i} for i, _ in enumerate(locais)]})
    raise AssertionError(f"chamada externa inesperada: {request.url}")


@pytest.fixture(autouse=True)
def circuitos_fechados() -> None:
    """Circuit breakers são globais; estados deixados por outros testes não podem afetar estes."""
    for breaker in CIRCUIT_BREAKERS.values():
        breaker.state = CircuitState.CLOSED
        breaker.failure_count = 0


@pytest.fixture
def api_offline(client: TestClient, sem_chave_gemini) -> Generator[TestClient, None, None]:
    """TestClient cujo pool HTTP compartilhado responde pelos provedores simulados (sem internet)."""
    original = client.app.state.http_client
    client.app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(_provedores_simulados))
    yield client
    client.app.state.http_client = original


@pytest.mark.parametrize("nome", SERVICOS_DO_ROTEADOR)
def test_roteador_usa_o_servico_real_e_nao_o_stub_de_import_error(nome: str) -> None:
    funcao = getattr(roteiros_module, nome)
    assert funcao.__module__.startswith("app.services."), f"{nome} caiu no stub definido no roteador"


def test_planejar_completo_com_os_servicos_reais(api_offline: TestClient) -> None:
    resposta = api_offline.post("/api/v1/roteiros/planejar", json=PAYLOAD, headers=HEADERS)

    assert resposta.status_code == 200
    roteiro = resposta.json()
    assert "X-Process-Time" in resposta.headers

    # Geocoding e rota
    assert roteiro["origem"] == {"cidade": "Teresina", "uf": "PI", "latitude": -5.089, "longitude": -42.801}
    assert roteiro["destino"]["uf"] == "DF"
    assert roteiro["distancia_km"] == 1674.6
    assert roteiro["duracao_minutos"] == 1298.0
    assert roteiro["geometria"]["coordinates"] == GEOMETRIA

    # Clima
    assert roteiro["clima"]["temperatura_c"] == 31.4
    assert roteiro["clima"]["descricao"] == "Predominantemente limpo"

    # Altimetria (amostras sempre subindo)
    assert roteiro["altimetria"]["ganho_m"] > 0
    assert roteiro["altimetria"]["perda_m"] == 0.0

    assert roteiro["altimetria"]["fonte"] == "Open-Elevation"
    assert len(roteiro["altimetria"]["perfil"]) > 2
    impacto = roteiro["altimetria"]["impacto_consumo_percentual"]
    assert impacto > 0

    # Custos: 1674,6 km / 12 km/L * R$ 5,89, acrescidos do impacto do relevo, e rateio entre 2 passageiros
    assert roteiro["custos"]["combustivel_ou_energia"] == pytest.approx(1674.6 / 12 * 5.89 * (1 + impacto / 100), abs=0.01)
    assert roteiro["custos"]["por_passageiro"] == pytest.approx(roteiro["custos"]["total"] / 2, abs=0.01)
    assert roteiro["custos"]["emissoes_kg_co2"] > 0

    # Paradas (autonomia de 500 km exige abastecimento) e guia de contingência (sem chave Gemini)
    assert len(roteiro["paradas"]) == 4  # alcance útil de 410 km em 1674,6 km
    assert all(p["estimada"] is False and p["nome"].startswith("Posto Teste") for p in roteiro["paradas"])

    # Alternativas: geometria compatível com o mapa mais nome e métricas da sugestão
    assert len(roteiro["alternativas"]) == 1
    alternativa = roteiro["alternativas"][0]
    assert alternativa["type"] == "LineString" and alternativa["coordinates"] == ALTERNATIVA
    assert alternativa["nome"] == "Sugestão 02 (Rodovias Federais / Mais Econômica)"
    assert (alternativa["distancia_km"], alternativa["duracao_minutos"]) == (1650.0, 1333.3)

    assert roteiro["guia"].startswith("🏛️ IDENTIDADE: Brasília")
    assert "Dia 2" in roteiro["guia"]

    diagnosticos = {d["provedor"]: d["status"] for d in roteiro["diagnosticos"]}
    assert {diagnosticos[p] for p in ("geocoding", "clima", "rota", "altimetria", "postos")} == {"disponivel"}
    # Sem chave Gemini o guia é a contingência, e o diagnóstico deixa isso claro
    assert diagnosticos["gemini"] == "parcial"


def test_planejar_degrada_quando_clima_e_altimetria_falham(api_offline: TestClient) -> None:
    def com_falhas(request: httpx.Request) -> httpx.Response:
        if request.url.host in ("api.open-meteo.com", "api.open-elevation.com"):
            return httpx.Response(503)
        return _provedores_simulados(request)

    api_offline.app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(com_falhas))
    resposta = api_offline.post("/api/v1/roteiros/planejar", json=PAYLOAD, headers=HEADERS)

    assert resposta.status_code == 200
    roteiro = resposta.json()
    diagnosticos = {d["provedor"]: d for d in roteiro["diagnosticos"]}
    assert diagnosticos["clima"]["status"] == "indisponivel" and "HTTP 503" in diagnosticos["clima"]["mensagem"]
    assert diagnosticos["altimetria"]["status"] == "indisponivel"
    assert roteiro["clima"]["temperatura_c"] is None
    assert roteiro["distancia_km"] == 1674.6  # o restante do planejamento segue utilizável
    assert roteiro["custos"]["total"] > 0


def test_destino_sem_estrada_degrada_com_a_mensagem_do_servico(api_offline: TestClient) -> None:
    def ilha(request: httpx.Request) -> httpx.Response:
        if request.url.host == "router.project-osrm.org":
            rota = {"distance": 1.0, "duration": 1.0, "geometry": {"type": "LineString", "coordinates": GEOMETRIA}}
            return httpx.Response(200, json={"code": "Ok", "routes": [rota], "waypoints": [{"distance": 3.0}, {"distance": 45_000.0}]})
        return _provedores_simulados(request)

    api_offline.app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(ilha))
    resposta = api_offline.post("/api/v1/roteiros/planejar", json=PAYLOAD, headers=HEADERS)

    assert resposta.status_code == 200
    rota = next(d for d in resposta.json()["diagnosticos"] if d["provedor"] == "rota")
    assert rota["status"] == "indisponivel" and "Considere voos ou barcos" in rota["mensagem"]


def test_mapa_rota_devolve_a_geometria_real(api_offline: TestClient) -> None:
    corpo = {k: PAYLOAD[k] for k in ("origem_cidade", "origem_uf", "destino_cidade", "destino_uf", "preferencia_rota")}

    resposta = api_offline.post("/api/v1/roteiros/mapa-rota", json=corpo, headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.json() == {"type": "LineString", "coordinates": GEOMETRIA}


def test_endpoint_de_custos_usa_o_servico_real(client: TestClient) -> None:
    corpo = {"distancia_km": 600.0, "tipo_veiculo": "gasolina", "consumo_medio": 12.0, "preco_unidade": 6.0, "passageiros": 2, "pedagios_estimados": 40.0}

    resposta = client.post("/api/v1/roteiros/custos", json=corpo)

    assert resposta.status_code == 200
    assert resposta.json() == {
        "combustivel_ou_energia": 300.0,
        "pedagios": 40.0,
        "total": 340.0,
        "por_passageiro": 170.0,
        "moeda": "BRL",
        "emissoes_kg_co2": 115.5,
    }


def test_stream_guia_emite_o_guia_em_eventos_sse_validos(client: TestClient, sem_chave_gemini) -> None:
    corpo = {"destino": "Teresina - PI", "dias_estadia": 1, "estilo_viagem": "cultural", "clima_info": {}, "atrativos": [], "gastronomia": []}

    resposta = client.post("/api/v1/roteiros/stream-guia", json=corpo, headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/event-stream")
    eventos = [json.loads(bloco.removeprefix("data: ")) for bloco in resposta.text.strip().split("\n\n")]
    assert all(e["done"] is False for e in eventos[:-1])
    assert eventos[-1] == {"chunk": "", "done": True}
    assert "".join(e["chunk"] for e in eventos) == gerar_guia_contingencia("Teresina - PI", 1, {})


def test_gpx_exportado_contem_a_rota_planejada(api_offline: TestClient) -> None:
    roteiro = api_offline.post("/api/v1/roteiros/planejar", json=PAYLOAD, headers=HEADERS).json()

    # O histórico é gravado em tarefa de segundo plano; o TestClient a executa antes de devolver a resposta
    resposta = api_offline.post("/api/v1/roteiros/exportar/gpx", json={"roteiro_id": roteiro["id"]}, headers=HEADERS)

    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/gpx+xml")
    assert f'filename="roteiro-{roteiro["id"]}.gpx"' in resposta.headers["content-disposition"]
    raiz = ET.fromstring(resposta.text)
    ns = {"g": "http://www.topografix.com/GPX/1/1"}
    assert len(raiz.findall(".//g:trkpt", ns)) == len(GEOMETRIA)
    nomes = [w.findtext("g:name", namespaces=ns) for w in raiz.findall("g:wpt", ns)]
    assert nomes[0] == "Origem: Teresina" and nomes[-1] == "Destino: Brasília"
    assert len(nomes) == 2 + len(roteiro["paradas"])
    # O perfil de altitude foi salvo com o roteiro, então todos os pontos da trilha têm <ele>
    assert all(p.find("g:ele", ns) is not None for p in raiz.findall(".//g:trkpt", ns))
