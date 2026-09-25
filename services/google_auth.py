"""Serviço de autenticação: validação do token JWT do Google Identity Services."""

from typing import Any

import httpx

from config import GOOGLE_CLIENT_ID


def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
    """Valida o token JWT no endpoint oficial 'https://oauth2.googleapis.com/tokeninfo'.

    Verifica se o token foi emitido para o GOOGLE_CLIENT_ID configurado no projeto
    e retorna o payload do usuário (sub, name, email, picture) ou None se for inválido.
    """
    try:
        resposta = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=4.0,
        )
        resposta.raise_for_status()
        payload: dict[str, Any] = resposta.json()

        # Verifica se o token foi emitido para este projeto (campo 'aud' deve bater com o CLIENT_ID)
        if payload.get("aud") != GOOGLE_CLIENT_ID:
            return None

        return payload

    except (httpx.TimeoutException, httpx.HTTPError, Exception):
        return None
