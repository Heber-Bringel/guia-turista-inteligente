"""Integração V3 do roteador com os serviços de dados: patrimônios por região e evento do Workflow 4."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.routers import roteiros as roteiros_module
from app.routers.roteiros import _selecionar_patrimonios_destino


@pytest.mark.parametrize(
    ("destino", "ausentes"),
    [
        ("Campinas - SP", {"Parque Nacional de Sete Cidades", "BR-343"}),  # contém "pi"
        ("Curitiba - PR", {"Pelourinho", "Chapada Diamantina"}),  # contém "ba"
        ("Bauru - SP", {"Pelourinho"}),
    ],
)
def test_patrimonios_regionais_nao_casam_por_trecho_solto(destino: str, ausentes: set[str]) -> None:
    assert not ausentes & set(_selecionar_patrimonios_destino(destino, "quero passear"))


@pytest.mark.parametrize(
    ("destino", "esperado"),
    [
        ("Piripiri - PI", "Parque Nacional de Sete Cidades"),
        ("Salvador - BA", "Pelourinho"),
        ("Brasília - DF", "Congresso Nacional"),
        ("Campinas - SP", "Centro Histórico de Campinas"),
    ],
)
def test_patrimonios_regionais_pela_uf_do_destino(destino: str, esperado: str) -> None:
    assert esperado in _selecionar_patrimonios_destino(destino, "")


def test_chat_de_cidade_sem_patrimonio_conhecido_nao_inventa_patrimonios(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(roteiros_module.gemini_service.settings, "GEMINI_API_KEY", "")
    resposta = client.post(
        "/api/v1/roteiros/chat",
        headers={**auth_headers, "Accept-Language": "en"},
        json={"destino": "Pirenópolis - GO", "mensagem": "Plan two calm days"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["patrimonios_preservados"] == []
    assert resposta.json()["idioma"] == "en"


def test_planejar_agenda_o_evento_do_workflow_4(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "origem_cidade": "Teresina",
        "origem_uf": "PI",
        "destino_cidade": "Piripiri",
        "destino_uf": "PI",
        "dias_estadia": 2,
        "estilo_viagem": "ecoturismo",
        "preferencia_rota": "rapida",
        "tipo_veiculo": "gasolina",
        "consumo_medio": 12.0,
        "autonomia_km": 500.0,
        "capacidade_veiculo": 50.0,
        "preco_unidade": 5.89,
        "passageiros": 2,
    }
    coordenadas = AsyncMock(side_effect=[(-5.089, -42.801, "PI"), (-4.2733, -41.7769, "PI")])
    disparo = AsyncMock(return_value=None)

    with (
        patch.object(roteiros_module, "buscar_coordenadas_async", coordenadas),
        patch.object(roteiros_module, "despachar_evento_clima_n8n", disparo),
    ):
        resposta = client.post(
            "/api/v1/roteiros/planejar", json=payload, headers={**auth_headers, "Accept-Language": "fr-FR"}
        )

    assert resposta.status_code == 200
    disparo.assert_awaited_once()
    evento = disparo.await_args.args[1]
    assert evento["destino"] == "Piripiri - PI"
    assert (evento["latitude"], evento["longitude"]) == (-4.2733, -41.7769)
    assert evento["idioma"] == "fr"
    assert evento["dias"] == 2
    assert evento["roteiro_id"] == resposta.json()["id"]


def test_planejar_sem_destino_geocodificado_nao_dispara_o_workflow_4(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "origem_cidade": "Teresina",
        "origem_uf": "PI",
        "destino_cidade": "Piripiri",
        "destino_uf": "PI",
        "dias_estadia": 1,
        "estilo_viagem": "cultural",
        "preferencia_rota": "rapida",
        "tipo_veiculo": "gasolina",
        "consumo_medio": 12.0,
        "autonomia_km": 500.0,
        "capacidade_veiculo": 50.0,
        "preco_unidade": 5.89,
        "passageiros": 1,
    }
    disparo = AsyncMock(return_value=None)

    with (
        patch.object(roteiros_module, "buscar_coordenadas_async", AsyncMock(side_effect=RuntimeError("geocoding fora"))),
        patch.object(roteiros_module, "despachar_evento_clima_n8n", disparo),
    ):
        resposta = client.post("/api/v1/roteiros/planejar", json=payload, headers=auth_headers)

    assert resposta.status_code == 200
    disparo.assert_not_awaited()
