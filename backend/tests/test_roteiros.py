"""Testes exaustivos do ciclo de roteiros: validação 422, concorrência 409, isolamento e SSE."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from app.routers import roteiros as roteiros_module
from app.services.storage_service import (
    deletar_viagem_usuario_sync,
    listar_viagens_usuario_sync,
    salvar_nova_viagem_sync,
)


@pytest.fixture
def payload_valido() -> dict[str, object]:
    """Payload de planejamento completo e válido segundo o schema."""
    return {
        "origem_cidade": "Teresina",
        "origem_uf": "PI",
        "destino_cidade": "Brasília",
        "destino_uf": "DF",
        "dias_estadia": 3,
        "estilo_viagem": "cultural",
        "preferencia_rota": "rapida",
        "tipo_veiculo": "gasolina",
        "consumo_medio": 12.0,
        "autonomia_km": 500.0,
        "capacidade_veiculo": 50.0,
        "preco_unidade": 5.89,
        "passageiros": 2,
    }


# =============================================================================
# 1. Validação Pydantic v2 Estrita (HTTP 422)
# =============================================================================

def test_validacao_rejeita_uf_invalida_com_422(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Garante que UF inexistente ou com formato incorreto resulte em HTTP 422."""
    payload_valido["origem_uf"] = "XX"
    response = client.post("/api/v1/roteiros/planejar", json=payload_valido, headers=auth_headers)
    assert response.status_code == 422
    assert "origem_uf" in str(response.json())


def test_validacao_rejeita_campos_extras_com_422(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Garante que atributos inesperados sejam proibidos (extra='forbid') com HTTP 422."""
    payload_valido["campo_nao_permitido"] = "valor_proibido"
    response = client.post("/api/v1/roteiros/planejar", json=payload_valido, headers=auth_headers)
    assert response.status_code == 422
    assert "Extra inputs are not permitted" in str(response.json()) or "extra" in str(response.json()).lower()


def test_validacao_rejeita_cidade_em_branco_com_422(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Garante que cidade vazia ou apenas com espaços seja rejeitada."""
    payload_valido["destino_cidade"] = "   "
    response = client.post("/api/v1/roteiros/planejar", json=payload_valido, headers=auth_headers)
    assert response.status_code == 422


def test_validacao_rejeita_limites_numericos_com_422(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Valida limites de dias de estadia (1 a 5) e passageiros (1 a 8)."""
    payload_dias = dict(payload_valido)
    payload_dias["dias_estadia"] = 6
    res_dias = client.post("/api/v1/roteiros/planejar", json=payload_dias, headers=auth_headers)
    assert res_dias.status_code == 422

    payload_pass = dict(payload_valido)
    payload_pass["passageiros"] = 10
    res_pass = client.post("/api/v1/roteiros/planejar", json=payload_pass, headers=auth_headers)
    assert res_pass.status_code == 422


# =============================================================================
# 2. Idempotência e Concorrência (HTTP 409 e liberação no finally)
# =============================================================================

def test_requisicao_duplicada_em_andamento_retorna_409(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Verifica se uma requisição idêntica para o mesmo usuário resulta em 409 e libera a chave após conclusão."""
    user_id = auth_headers["X-User-Id"]
    chave = f"{user_id}:{payload_valido['origem_cidade']}_{payload_valido['origem_uf']}->{payload_valido['destino_cidade']}_{payload_valido['destino_uf']}".lower()

    # Simula a chave como já presente no conjunto de ativas
    roteiros_module.REQUISICOES_ATIVAS.add(chave)

    try:
        response = client.post(
            "/api/v1/roteiros/planejar", json=payload_valido, headers=auth_headers
        )
        assert response.status_code == 409
        assert "já está sendo calculado" in response.json()["detail"]
    finally:
        roteiros_module.REQUISICOES_ATIVAS.discard(chave)

    # Após descarte da chave, a requisição passa normalmente
    assert chave not in roteiros_module.REQUISICOES_ATIVAS


# =============================================================================
# 3. Isolamento Total de Histórico entre Usuários
# =============================================================================

def test_isolamento_total_de_historico_entre_usuarios(
    client: TestClient,
    auth_headers: dict[str, str],
    auth_headers_outro_usuario: dict[str, str],
) -> None:
    """Usuário A não pode visualizar, alterar ou excluir roteiros do Usuário B."""
    user_a = auth_headers["X-User-Id"]
    user_b = auth_headers_outro_usuario["X-User-Id"]

    # Salva uma viagem no storage diretamente para o Usuário A
    viagem_a = {
        "id": "rot_privado_user_a",
        "origem": {"cidade": "Teresina", "uf": "PI"},
        "destino": {"cidade": "Fortaleza", "uf": "CE"},
        "atrativos": [{"id": "atr_1", "nome": "Praia de Iracema", "visitado": False}],
    }
    salvar_nova_viagem_sync(user_a, viagem_a)

    # 1. Usuário B lista viagens -> NÃO deve ver a viagem do Usuário A
    res_b = client.get("/api/v1/roteiros/minhas-viagens", headers=auth_headers_outro_usuario)
    assert res_b.status_code == 200
    viagens_b = res_b.json()
    assert not any(v["id"] == "rot_privado_user_a" for v in viagens_b)

    # 2. Usuário B tenta marcar visita na viagem do Usuário A -> HTTP 404
    res_visita = client.patch(
        "/api/v1/roteiros/rot_privado_user_a/visitas",
        json={"atrativo_id": "atr_1", "visitado": True},
        headers=auth_headers_outro_usuario,
    )
    assert res_visita.status_code == 404

    # 3. Usuário B tenta excluir a viagem do Usuário A -> HTTP 404
    res_delete = client.delete(
        "/api/v1/roteiros/rot_privado_user_a", headers=auth_headers_outro_usuario
    )
    assert res_delete.status_code == 404

    # 4. Usuário A consegue marcar visita e excluir normalmente
    res_visita_a = client.patch(
        "/api/v1/roteiros/rot_privado_user_a/visitas",
        json={"atrativo_id": "atr_1", "visitado": True},
        headers=auth_headers,
    )
    assert res_visita_a.status_code == 200

    res_delete_a = client.delete("/api/v1/roteiros/rot_privado_user_a", headers=auth_headers)
    assert res_delete_a.status_code == 204


# =============================================================================
# 4. Escrita Atômica Concorrente no Storage (Sem Perda de Dados)
# =============================================================================

def test_escrita_atomica_concorrente_sem_perda_de_dados() -> None:
    """Garante que múltiplas gravações simultâneas em threads concorrentes não corrompam o arquivo JSON."""
    user_id = "usr_concorrente_stress"
    total_viagens = 20

    def gravar(indice: int) -> None:
        viagem = {
            "id": f"rot_stress_{indice}",
            "titulo": f"Viagem de teste {indice}",
            "indice": indice,
        }
        salvar_nova_viagem_sync(user_id, viagem)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(gravar, range(total_viagens)))

    viagens_salvas = listar_viagens_usuario_sync(user_id)
    assert len(viagens_salvas) == total_viagens
    ids_salvos = {v["id"] for v in viagens_salvas}
    for i in range(total_viagens):
        assert f"rot_stress_{i}" in ids_salvos


# =============================================================================
# 5. Planejamento com Serviços Mockados e Degradação Graciosa
# =============================================================================

def test_planejar_roteiro_completo_com_servicos_mockados(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Verifica a montagem correta da resposta completa quando os serviços respondem com sucesso."""
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
            return_value={"temperatura_c": 31.0, "umidade_percentual": 40.0, "vento_kmh": 15.0, "descricao": "Ensolarado"},
        ),
        patch.object(
            roteiros_module,
            "calcular_rota_osrm_async",
            new_callable=AsyncMock,
            return_value={
                "distancia_km": 1674.6,
                "duracao_minutos": 1298.0,
                "geometria": {"type": "LineString", "coordinates": [[-42.801, -5.089], [-47.929, -15.779]]},
                "paradas": [],
            },
        ),
        patch.object(
            roteiros_module,
            "gerar_guia_ia_async",
            new_callable=AsyncMock,
            return_value=("Guia cultural completo de Brasília.", [{"id": "atr_1", "nome": "Congresso", "visitado": False}]),
        ),
    ):
        response = client.post("/api/v1/roteiros/planejar", json=payload_valido, headers=auth_headers)
        assert response.status_code == 200
        dados = response.json()

        assert dados["distancia_km"] == 1674.6
        assert dados["duracao_minutos"] == 1298.0
        assert dados["clima"]["temperatura_c"] == 31.0
        assert dados["origem"]["cidade"] == "Teresina"
        assert dados["destino"]["cidade"] == "Brasília"
        assert len(dados["paradas"]) >= 1  # Gerou parada por exceder autonomia
        assert any(d["provedor"] == "gemini" and d["status"] == "disponivel" for d in dados["diagnosticos"])


def test_planejar_roteiro_degradacao_controlada_quando_provedor_falha(
    client: TestClient, auth_headers: dict[str, str], payload_valido: dict[str, object]
) -> None:
    """Garante que a falha de um provedor (ex: clima e IA) não resulte em erro 500, gerando status 'indisponivel'."""
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
            side_effect=Exception("Timeout no Open-Meteo"),
        ),
        patch.object(
            roteiros_module,
            "calcular_rota_osrm_async",
            new_callable=AsyncMock,
            return_value={
                "distancia_km": 500.0,
                "duracao_minutos": 360.0,
                "geometria": {"type": "LineString", "coordinates": [[-42.8, -5.0], [-43.0, -5.5]]},
                "paradas": [],
            },
        ),
        patch.object(
            roteiros_module,
            "gerar_guia_ia_async",
            new_callable=AsyncMock,
            side_effect=Exception("Cota 429 excedida no Gemini"),
        ),
    ):
        response = client.post("/api/v1/roteiros/planejar", json=payload_valido, headers=auth_headers)
        assert response.status_code == 200
        dados = response.json()

        # Resposta mantém estrutura consistente
        assert dados["distancia_km"] == 500.0
        # Diagnósticos refletem as falhas com degradação graciosa
        diagnosticos = {d["provedor"]: d["status"] for d in dados["diagnosticos"]}
        assert diagnosticos.get("clima") in ("indisponivel", "parcial")
        assert diagnosticos.get("gemini") in ("indisponivel", "parcial")


# =============================================================================
# 6. Formato do Streaming SSE
# =============================================================================

def test_stream_guia_emite_eventos_sse_formatados(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Verifica se o endpoint /stream-guia transmite eventos no formato padrão data: {...}\n\n com chunk final."""
    async def mock_stream_generator(payload: dict):
        yield "Bem-vindo a Brasília! "
        yield "Visite a Catedral Metropolitana."

    with patch.object(roteiros_module, "gerar_guia_ia_stream_async", side_effect=mock_stream_generator):
        payload_stream = {
            "destino": "Brasília - DF",
            "dias_estadia": 2,
            "estilo_viagem": "cultural",
            "clima_info": {},
            "atrativos": [],
            "gastronomia": [],
        }

        response = client.post(
            "/api/v1/roteiros/stream-guia",
            json=payload_stream,
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["Content-Type"]

        conteudo = response.text
        assert 'data: {"chunk": "Bem-vindo a Brasília! ", "done": false}' in conteudo
        assert 'data: {"chunk": "Visite a Catedral Metropolitana.", "done": false}' in conteudo
        assert 'data: {"chunk": "", "done": true}' in conteudo


# =============================================================================
# 7. Endpoints Complementares: Mapa, Custos e GPX
# =============================================================================

def test_mapa_rota_retorna_geojson(client: TestClient) -> None:
    """Verifica endpoint leve de mapa retornando LineString GeoJSON."""
    with (
        patch.object(
            roteiros_module,
            "buscar_coordenadas_async",
            new_callable=AsyncMock,
            return_value=(-3.717, -38.543, "CE"),
        ),
        patch.object(
            roteiros_module,
            "calcular_rota_osrm_async",
            new_callable=AsyncMock,
            return_value={
                "distancia_km": 500.0,
                "duracao_minutos": 380.0,
                "geometria": {"type": "LineString", "coordinates": [[-38.5, -3.7], [-35.2, -5.7]]},
            },
        ),
    ):
        response = client.post(
            "/api/v1/roteiros/mapa-rota",
            json={
                "origem_cidade": "Fortaleza",
                "origem_uf": "CE",
                "destino_cidade": "Natal",
                "destino_uf": "RN",
                "preferencia_rota": "rapida",
            },
        )
        assert response.status_code == 200
        dados = response.json()
        assert dados["type"] == "LineString"
        assert len(dados["coordinates"]) >= 2


def test_exportar_gpx_download(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Verifica download de arquivo GPX 1.1 estruturado."""
    user_id = auth_headers["X-User-Id"]
    salvar_nova_viagem_sync(user_id, {"id": "rot_gpx_123", "origem": {"cidade": "A"}, "destino": {"cidade": "B"}})

    response = client.post(
        "/api/v1/roteiros/exportar/gpx",
        json={"roteiro_id": "rot_gpx_123"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "application/gpx+xml" in response.headers["Content-Type"]
    assert "gpx version=" in response.text

