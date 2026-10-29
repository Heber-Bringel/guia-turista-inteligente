"""Dependências injetáveis do FastAPI (cliente HTTP compartilhado, autenticação e sessão)."""

from typing import Annotated
import httpx
from fastapi import Header, HTTPException, Request, status
from app.core.cache import cache
from app.core.logging_config import logger
from app.schemas.auth import UsuarioPerfil


async def obter_http_client(request: Request) -> httpx.AsyncClient:
    """Injeta a instância global de httpx.AsyncClient criada no lifespan da aplicação."""
    client = getattr(request.app.state, "http_client", None)
    if client is None or not isinstance(client, httpx.AsyncClient):
        logger.warning("http_client não encontrado no app.state. Criando cliente temporário.")
        return httpx.AsyncClient(timeout=10.0)
    return client


async def obter_usuario_ativo(
    request: Request,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> UsuarioPerfil:
    """Extrai e valida o usuário ativo a partir do cabeçalho X-User-Id ou Bearer Token.

    Retorna HTTP 401 caso não haja nenhuma credencial de autenticação fornecida.
    """
    token_bearer: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        token_bearer = authorization[7:].strip()

    # Prioridade de resolução de identidade:
    # 1. X-User-Id direto
    # 2. Bearer token
    user_id = (x_user_id or token_bearer or "").strip()

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sua sessão expirou ou credenciais ausentes. Entre novamente para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verifica se há perfil cached em memória (especialmente visitantes)
    perfil_salvo = cache.get(f"sessao:{user_id}")
    if isinstance(perfil_salvo, dict):
        try:
            return UsuarioPerfil.model_validate(perfil_salvo)
        except Exception:
            pass

    # Se for ID com prefixo de visitante
    if user_id.startswith("visitante_") or user_id.startswith("visitante-"):
        return UsuarioPerfil(
            id=user_id,
            nome="Viajante Visitante",
            modo="visitante",
            foto="/static/img/visitante.svg",
            accessToken=user_id,
        )

    # Caso padrão para usuários Google ou IDs autenticados
    return UsuarioPerfil(
        id=user_id,
        nome="Viajante Conectado",
        modo="google" if "google" in user_id else "visitante",
        accessToken=user_id,
    )

