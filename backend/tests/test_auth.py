"""Testes automatizados das rotas de autenticação (Google, visitante, logout e proteção 401)."""

from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.core.config import settings


def test_login_visitante_cria_perfil_com_ttl(client: TestClient) -> None:
    """Verifica se o login visitante gera identificador com prefixo e TTL de 2 horas (7200s)."""
    response = client.post("/api/v1/auth/visitante")
    assert response.status_code == 200
    dados = response.json()

    assert "usuario" in dados
    assert "access_token" in dados
    assert dados["expires_in"] == 7200

    usuario = dados["usuario"]
    assert usuario["modo"] == "visitante"
    assert usuario["id"].startswith("visitante_")
    assert usuario["nome"] == "Viajante Visitante"
    assert usuario["accessToken"] == dados["access_token"]


def test_login_google_valida_token_sucesso(client: TestClient) -> None:
    """Verifica fluxo bem-sucedido de autenticação Google com mock no tokeninfo."""
    payload_jwt = {"credential": "jwt_valido_mock_google"}

    resposta_mock = httpx.Response(
        status_code=200,
        json={
            "sub": "987654321",
            "name": "Mikaelle Barroso",
            "email": "mikaelle@example.com",
            "picture": "https://example.com/foto.jpg",
            "aud": settings.GOOGLE_CLIENT_ID,
        },
        request=httpx.Request("GET", "https://oauth2.googleapis.com/tokeninfo"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resposta_mock
        response = client.post("/api/v1/auth/google", json=payload_jwt)

        assert response.status_code == 200
        dados = response.json()
        usuario = dados["usuario"]
        assert usuario["id"] == "usr_google_987654321"
        assert usuario["nome"] == "Mikaelle Barroso"
        assert usuario["email"] == "mikaelle@example.com"
        assert usuario["modo"] == "google"


def test_login_google_token_invalido_rejeita_com_401(client: TestClient) -> None:
    """Garante que token inválido rejeitado pelo Google resulte em HTTP 401."""
    payload_jwt = {"credential": "jwt_token_falso"}

    resposta_mock = httpx.Response(
        status_code=400,
        json={"error_description": "Invalid Value"},
        request=httpx.Request("GET", "https://oauth2.googleapis.com/tokeninfo"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = resposta_mock
        response = client.post("/api/v1/auth/google", json=payload_jwt)

        assert response.status_code == 401
        assert "Token do Google inválido" in response.json()["detail"]


def test_login_google_falha_de_rede_retorna_503(client: TestClient) -> None:
    """Verifica resiliência em falha de conexão com os servidores do Google."""
    payload_jwt = {"credential": "jwt_token_qualquer"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Erro de DNS no Google")
        response = client.post("/api/v1/auth/google", json=payload_jwt)

        assert response.status_code == 503
        assert "Não foi possível conectar ao serviço de autenticação" in response.json()["detail"]


def test_logout_encerra_sessao(client: TestClient) -> None:
    """Verifica se o logout aceita requisição com cabeçalho X-User-Id e encerra a sessão."""
    headers = {"X-User-Id": "visitante_logout_teste"}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert "Sessão encerrada com sucesso" in response.json()["mensagem"]


def test_rota_protegida_sem_autenticacao_retorna_401(client: TestClient) -> None:
    """Garante que requisições a rotas protegidas sem cabeçalho de usuário recebam HTTP 401."""
    response = client.get("/api/v1/roteiros/minhas-viagens")
    assert response.status_code == 401
    assert "Sua sessão expirou ou credenciais ausentes" in response.json()["detail"]

