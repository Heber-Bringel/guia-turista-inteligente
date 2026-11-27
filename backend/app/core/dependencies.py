"""Dependências injetáveis do FastAPI (cliente HTTP compartilhado, autenticação, X-Support-Key e Accept-Language)."""

import hmac
from typing import Annotated

import httpx
from fastapi import Header, HTTPException, Request, status

from app.core.cache import cache
from app.core.config import settings
from app.core.logging_config import logger
from app.schemas.auth import UsuarioPerfil

IDIOMAS_SUPORTADOS = {"pt", "en", "es", "fr", "zh", "hi", "ar", "ru"}


async def obter_http_client(request: Request) -> httpx.AsyncClient:
    """Injeta a instância global de httpx.AsyncClient criada no lifespan da aplicação."""
    client = getattr(request.app.state, "http_client", None)
    if client is None or not isinstance(client, httpx.AsyncClient):
        logger.warning("http_client não encontrado no app.state. Criando cliente temporário.")
        return httpx.AsyncClient(timeout=10.0)
    return client


def normalizar_idioma(accept_language: str | None) -> str:
    """Extrai e normaliza o código de idioma principal do cabeçalho Accept-Language (padrão 'pt').

    Exemplos:
    - 'en-US,en;q=0.9,pt-BR;q=0.8' -> 'en'
    - 'zh-CN' -> 'zh'
    - 'pt-BR' -> 'pt'
    - None ou idioma desconhecido -> 'pt'
    """
    if not accept_language or not isinstance(accept_language, str):
        return "pt"
    primeiro_token = accept_language.split(",")[0].split(";")[0].strip().lower()
    if not primeiro_token:
        return "pt"
    codigo_base = primeiro_token.split("-")[0].split("_")[0].strip()
    return codigo_base if codigo_base in IDIOMAS_SUPORTADOS else "pt"


async def obter_idioma(
    accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
) -> str:
    """Dependência FastAPI que injeta o idioma normalizado a partir de Accept-Language."""
    return normalizar_idioma(accept_language)


async def validar_support_key(
    x_support_key: Annotated[str | None, Header(alias="X-Support-Key")] = None,
) -> str:
    """Protege endpoints operacionais e de ChatOps exigindo o cabeçalho X-Support-Key.

    Retorna HTTP 401 se o cabeçalho estiver ausente ou HTTP 403 se a chave for inválida.
    """
    chave_recebida = (x_support_key or "").strip()
    if not chave_recebida:
        logger.warning("Acesso bloqueado a endpoint de suporte: cabeçalho X-Support-Key ausente.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso restrito à equipe de suporte: cabeçalho X-Support-Key obrigatório.",
        )

    chave_esperada = (settings.SUPPORT_API_KEY or "").strip()
    if not chave_esperada or not hmac.compare_digest(chave_recebida, chave_esperada):
        logger.warning("Acesso bloqueado a endpoint de suporte: X-Support-Key inválida.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: credencial X-Support-Key inválida.",
        )

    return chave_recebida


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
        except Exception as exc:  # noqa: BLE001
            logger.debug("Falha ao validar perfil em cache para %s: %s", user_id, exc)

    # Se for ID com prefixo de visitante
    if user_id.startswith(("visitante_", "visitante-")):
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
