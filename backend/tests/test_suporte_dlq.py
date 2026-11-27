"""Testes da V3 (AT07): ChatOps com X-Support-Key, DLQ em BackgroundTasks, Chat Multilíngue e Despacho n8n."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from app.core.config import settings
from app.routers import roteiros as roteiros_module
from app.services import n8n_service
from app.services.storage_service import salvar_nova_viagem_sync
from fastapi.testclient import TestClient


@pytest.fixture
def support_headers() -> dict[str, str]:
    """Cabeçalho autenticado de suporte operacional (ChatOps)."""
    return {"X-Support-Key": settings.SUPPORT_API_KEY}


# =============================================================================
# 1. Segurança Operacional ChatOps (X-Support-Key em /status, /uptime, /telemetria, /testardlq)
# =============================================================================

@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/suporte/status",
        "/api/v1/suporte/uptime",
        "/api/v1/suporte/telemetria",
        "/api/v1/suporte/testardlq",
        "/status",
        "/uptime",
        "/telemetria",
        "/testardlq",
    ],
)
def test_endpoints_suporte_bloqueiam_acesso_sem_x_support_key(
    client: TestClient, endpoint: str
) -> None:
    """Garante que nenhum endpoint operacional responda sem X-Support-Key válido."""
    res_ausente = client.get(endpoint)
    assert res_ausente.status_code == 401

    res_invalido = client.get(endpoint, headers={"X-Support-Key": "token-forjado-invalido"})
    assert res_invalido.status_code == 403


def test_chatops_status_e_uptime_autenticados(
    client: TestClient, support_headers: dict[str, str]
) -> None:
    """Verifica respostas dos comandos /status e /uptime quando autenticados por X-Support-Key."""
    res_status = client.get("/api/v1/suporte/status", headers=support_headers)
    assert res_status.status_code == 200
    dados_status = res_status.json()
    assert dados_status["comando"] == "/status"
    assert dados_status["status"] == "online"
    assert dados_status["http_pool_ativo"] is True
    assert "dlq" in dados_status["n8n_webhooks"]

    res_uptime = client.get("/api/v1/suporte/uptime", headers=support_headers)
    assert res_uptime.status_code == 200
    dados_uptime = res_uptime.json()
    assert dados_uptime["comando"] == "/uptime"
    assert dados_uptime["uptime_segundos"] >= 0.0
    assert "uptime_formatado" in dados_uptime


# =============================================================================
# 2. DLQ em BackgroundTasks e Endpoint /testardlq
# =============================================================================

def test_testardlq_agenda_incidente_em_backgroundtasks_com_uuid_e_stack_trace(
    client: TestClient, support_headers: dict[str, str]
) -> None:
    """Comprova que /testardlq gera UUID válido, não vaza stack trace no HTTP e envia à DLQ em BackgroundTasks."""
    n8n_service.HISTORICO_EVENTOS_N8N.clear()

    with patch.object(
        n8n_service, "despachar_evento_dlq", wraps=n8n_service.despachar_evento_dlq
    ) as spy_dlq:
        res = client.post("/api/v1/suporte/testardlq", headers=support_headers)
        assert res.status_code == 200
        dados = res.json()

        # Valida UUID de rastreio
        uuid_obj = uuid.UUID(dados["trace_id"])
        assert str(uuid_obj) == dados["trace_id"]
        assert dados["status"] == "incidente_agendado_dlq"
        assert dados["execucao"] == "BackgroundTasks"
        # A resposta HTTP pública não deve vazar stack trace cru
        assert "Traceback (most recent call last)" not in json.dumps(dados)

        # Verifica que o BackgroundTasks executou despachar_evento_dlq com stack_trace completo
        assert spy_dlq.called
        payload_enviado = spy_dlq.call_args[0][1]
        assert payload_enviado["trace_id"] == dados["trace_id"]
        assert payload_enviado["servico"] == "chatops_testardlq"
        assert "RuntimeError" in payload_enviado["stack_trace"]
        assert "Falha simulada pelo comando ChatOps /testardlq" in payload_enviado["stack_trace"]


def test_falha_de_provedor_no_planejamento_aciona_dlq_sem_expor_erro_tecnico(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Quando um provedor externo falha em /planejar, o usuário recebe mensagem higienizada e a DLQ é acionada."""
    payload = {
        "origem_cidade": "Teresina",
        "origem_uf": "PI",
        "destino_cidade": "Parnaíba",
        "destino_uf": "PI",
        "dias_estadia": 2,
        "estilo_viagem": "ecoturismo",
        "preferencia_rota": "rapida",
        "tipo_veiculo": "gasolina",
        "consumo_medio": 12.0,
        "autonomia_km": 200.0,
        "capacidade_veiculo": 50.0,
        "preco_unidade": 5.89,
        "passageiros": 2,
    }

    with (
        patch.object(
            roteiros_module,
            "buscar_coordenadas_async",
            new_callable=AsyncMock,
            return_value=(-5.089, -42.801, "PI"),
        ),
        patch.object(
            roteiros_module,
            "obter_clima_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("SocketTimeoutError interno em api.open-meteo.com:443"),
        ),
        patch.object(
            roteiros_module,
            "calcular_rota_osrm_async",
            new_callable=AsyncMock,
            return_value={
                "distancia_km": 338.0,
                "duracao_minutos": 280.0,
                "geometria": {"type": "LineString", "coordinates": [[-42.8, -5.0], [-41.7, -2.9]]},
                "paradas": [
                    {
                        "id": "posto_anp_br343",
                        "nome": "Posto Piripiri BR-343",
                        "latitude": -4.273,
                        "longitude": -41.778,
                        "distancia_origem_km": 160.0,
                        "estimada": False,
                        "visitado": False,
                        "cnpj": "07.456.789/0001-90",
                        "razao_social": "Auto Posto Caldeirão da BR-343 Ltda",
                        "avaliacao": 4.8,
                        "tempo_autorizacao_anp": "14 anos",
                        "combustiveis": ["Gasolina Comum", "Diesel S10"],
                        "ranking_score": 9.4,
                    }
                ],
            },
        ),
        patch.object(
            roteiros_module,
            "agendar_dlq_background",
            wraps=roteiros_module.agendar_dlq_background,
        ) as spy_agendar_dlq,
    ):
        res = client.post(
            "/api/v1/roteiros/planejar",
            json=payload,
            headers={**auth_headers, "Accept-Language": "en-US,en;q=0.9"},
        )
        assert res.status_code == 200
        dados = res.json()

        # Idioma extraído do Accept-Language
        assert dados["idioma"] == "en"

        # Dados regulatórios ANP preservados nas paradas
        posto = dados["paradas"][0]
        assert posto["cnpj"] == "07.456.789/0001-90"
        assert posto["razao_social"] == "Auto Posto Caldeirão da BR-343 Ltda"
        assert posto["avaliacao"] == 4.8
        assert posto["tempo_autorizacao_anp"] == "14 anos"
        assert "Gasolina Comum" in posto["combustiveis"]

        # Higienização: mensagem técnica crua "SocketTimeoutError" não aparece nos diagnósticos públicos
        msg_clima = next(d["mensagem"] for d in dados["diagnosticos"] if d["provedor"] == "clima")
        assert "SocketTimeoutError" not in msg_clima

        # DLQ acionada em BackgroundTasks
        assert spy_agendar_dlq.called


# =============================================================================
# 3. Chat Multilíngue Contextual (Accept-Language + Preservação de Patrimônios Locais)
# =============================================================================

@pytest.mark.parametrize(
    ("accept_language", "idioma_esperado"),
    [
        ("en-US,en;q=0.9", "en"),
        ("es-ES,es;q=0.8", "es"),
        ("fr-FR", "fr"),
        ("zh-CN", "zh"),
        ("hi-IN", "hi"),
        ("ar-SA", "ar"),
        ("ru-RU", "ru"),
        ("pt-BR", "pt"),
    ],
)
def test_chat_roteiro_adapta_idioma_e_preserva_patrimonios_locais(
    client: TestClient,
    auth_headers: dict[str, str],
    accept_language: str,
    idioma_esperado: str,
) -> None:
    """Verifica se POST /api/v1/roteiros/chat respeita Accept-Language e preserva nomes de patrimônios locais."""
    payload_chat = {
        "destino": "Piripiri - PI",
        "dias_estadia": 2,
        "estilo_viagem": "ecoturismo",
        "ritmo_viagem": "tranquilo",
        "acompanhantes": "família",
        "preferencias_gastronomia": "maria-isabel e capote",
        "mensagem": "Queremos visitar o Parque Nacional de Sete Cidades e passar pela BR-343.",
        "historico": [],
    }

    res = client.post(
        "/api/v1/roteiros/chat",
        json=payload_chat,
        headers={**auth_headers, "Accept-Language": accept_language},
    )
    assert res.status_code == 200
    dados = res.json()

    assert dados["idioma"] == idioma_esperado
    assert "Parque Nacional de Sete Cidades" in dados["resposta"]
    assert "Parque Nacional de Sete Cidades" in dados["patrimonios_preservados"]


# =============================================================================
# 4. Despacho Multicanal via n8n (E-mail e WhatsApp em BackgroundTasks)
# =============================================================================

@pytest.mark.parametrize(
    ("canal", "destinatario"),
    [
        ("email", "viajante@ifpi.edu.br"),
        ("whatsapp", "+5586999990000"),
    ],
)
def test_despachar_roteiro_multicanal_agenda_background_task(
    client: TestClient,
    auth_headers: dict[str, str],
    canal: str,
    destinatario: str,
) -> None:
    """Verifica se POST /api/v1/roteiros/despachar agenda envio em BackgroundTasks para turismo-despachar-roteiro."""
    user_id = auth_headers["X-User-Id"]
    salvar_nova_viagem_sync(
        user_id,
        {
            "id": "rot_piripiri_01",
            "origem": {"cidade": "Teresina", "uf": "PI"},
            "destino": {"cidade": "Piripiri", "uf": "PI"},
            "guia": "Visite o Parque Nacional de Sete Cidades.",
        },
    )

    with patch.object(
        n8n_service,
        "despachar_roteiro_multicanal",
        wraps=n8n_service.despachar_roteiro_multicanal,
    ) as spy_despacho:
        res = client.post(
            "/api/v1/roteiros/despachar",
            json={
                "roteiro_id": "rot_piripiri_01",
                "canal": canal,
                "destinatario": destinatario,
                "nome_viajante": "Mikaelle Barroso",
            },
            headers={**auth_headers, "Accept-Language": "pt-BR"},
        )
        assert res.status_code == 200
        dados = res.json()
        assert dados["status"] == "agendado"
        assert dados["canal"] == canal
        assert dados["destinatario"] == destinatario
        assert dados["protocolo"].startswith("dsp_")
        assert spy_despacho.called
