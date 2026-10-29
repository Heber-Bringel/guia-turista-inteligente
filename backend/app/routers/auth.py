"""Rotas de autenticação: Google OAuth (validação tokeninfo), visitante volátil e logout."""

import time
import uuid
from typing import Annotated
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from app.core.cache import cache
from app.core.config import settings
from app.core.dependencies import obter_http_client
from app.core.logging_config import logger
from app.schemas.auth import LoginResponse, TokenGoogleRequest, UsuarioPerfil

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/google",
    response_model=LoginResponse,
    summary="Login com Google Identity Services",
    description="Valida o JWT emitido pelo Google no endpoint oauth2/tokeninfo e autentica o usuário.",
)
async def login_google(
    payload: TokenGoogleRequest,
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
) -> LoginResponse:
    """Valida o token JWT recebido pelo frontend diretamente na infraestrutura do Google."""
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={payload.credential}"

    try:
        resp = await client.get(url, timeout=settings.TIMEOUT_SEGUNDOS)
    except httpx.RequestError as exc:
        logger.error("Falha de rede ao consultar Google TokenInfo: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível conectar ao serviço de autenticação do Google.",
        ) from exc

    if resp.status_code != 200:
        logger.warning("Token do Google rejeitado com status %d: %s", resp.status_code, resp.text)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token do Google inválido ou expirado.",
        )

    dados_token = resp.json()
    token_aud = dados_token.get("aud")

    # Se configurado GOOGLE_CLIENT_ID, valida audience
    if settings.GOOGLE_CLIENT_ID and token_aud != settings.GOOGLE_CLIENT_ID:
        logger.error("Audience inválido no token Google. Esperado: %s, recebido: %s", settings.GOOGLE_CLIENT_ID, token_aud)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Audience do token não corresponde ao Client ID configurado.",
        )

    sub = str(dados_token.get("sub", "")).strip()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador do usuário ausente no token do Google.",
        )

    user_id = f"usr_google_{sub}"
    nome = dados_token.get("name") or dados_token.get("given_name") or "Viajante Google"
    email = dados_token.get("email")
    foto = dados_token.get("picture")

    perfil = UsuarioPerfil(
        id=user_id,
        nome=nome,
        email=email,
        foto=foto,
        modo="google",
        accessToken=user_id,
        expiresAt=int((time.time() + settings.VISITANTE_TTL_SEGUNDOS) * 1000),
    )

    # Armazena perfil no cache
    cache.set(f"sessao:{user_id}", perfil.model_dump(), ttl_seconds=settings.VISITANTE_TTL_SEGUNDOS)

    return LoginResponse(
        usuario=perfil,
        access_token=user_id,
        expires_in=settings.VISITANTE_TTL_SEGUNDOS,
    )


@router.post(
    "/visitante",
    response_model=LoginResponse,
    summary="Login temporário como visitante",
    description="Cria uma identidade volátil com TTL de 2 horas para uso imediato sem cadastro.",
)
async def login_visitante() -> LoginResponse:
    """Cria uma sessão de visitante isolada e com validade temporária."""
    token_visitante = f"visitante_{uuid.uuid4().hex[:12]}"
    ttl = settings.VISITANTE_TTL_SEGUNDOS
    expires_at = int((time.time() + ttl) * 1000)

    perfil = UsuarioPerfil(
        id=token_visitante,
        nome="Viajante Visitante",
        email=None,
        foto="/static/img/visitante.svg",
        modo="visitante",
        accessToken=token_visitante,
        expiresAt=expires_at,
    )

    cache.set(f"sessao:{token_visitante}", perfil.model_dump(), ttl_seconds=ttl)

    return LoginResponse(
        usuario=perfil,
        access_token=token_visitante,
        expires_in=ttl,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Encerramento de sessão",
    description="Aceita chamadas do navegador, inclusive via navigator.sendBeacon.",
)
async def logout(
    request: Request,
    response: Response,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> dict[str, str]:
    """Invalida a sessão ativa do usuário no cache da aplicação."""
    user_id = (x_user_id or "").strip()
    if not user_id:
        try:
            body = await request.json()
            if isinstance(body, dict):
                user_id = str(body.get("user_id") or body.get("id") or "").strip()
        except Exception:
            pass

    if user_id:
        cache.delete(f"sessao:{user_id}")
        logger.info("Sessão finalizada para o usuário: %s", user_id)

    return {"mensagem": "Sessão encerrada com sucesso."}

