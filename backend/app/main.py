"""Ponto de entrada do microsserviço FastAPI - Guia do Turista Inteligente."""

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import httpx
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import logger, set_correlation_id, setup_logging
from app.routers.auth import router as auth_router
from app.routers.roteiros import router as roteiros_router
from app.routers.telemetria import router as telemetria_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia o ciclo de vida da aplicação: cria pool de HTTP compartilhado e encerra no shutdown."""
    setup_logging()
    logger.info("Iniciando %s v%s...", settings.APP_NAME, settings.APP_VERSION)

    # Criação do cliente HTTP assíncrono compartilhado com pool de conexões configurado
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
    timeout = httpx.Timeout(settings.TIMEOUT_SEGUNDOS, connect=5.0)
    headers = {
        "User-Agent": f"GuiaTuristaInteligente/{settings.APP_VERSION} (FastAPI; +https://github.com/Heber-Bringel/guia-turista-inteligente)",
        "Accept": "application/json",
    }
    app.state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers)
    logger.info("Pool de conexões httpx.AsyncClient instanciado em app.state.http_client.")

    # Garante existência do diretório de dados
    dados_path = settings.obter_caminho_dados()
    dados_path.parent.mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown gracioso
    logger.info("Encerrando pool de conexões httpx.AsyncClient...")
    if hasattr(app.state, "http_client"):
        await app.state.http_client.aclose()
    logger.info("Aplicação finalizada com sucesso.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Microsserviço backend assíncrono para planejamento de viagens turísticas, "
        "telemetria rodoviária (OSRM), previsão do tempo (Open-Meteo), perfil altimétrico, "
        "cálculo de autonomia/custos e streaming do guia com Google Gemini."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Middleware de CORS restrito às origens frontend (React 19)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID"],
)


@app.middleware("http")
async def correlation_and_process_time_middleware(request: Request, call_next) -> Response:
    """Injeta Correlation-ID (X-Request-ID) e calcula latência de processamento em X-Process-Time."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_correlation_id(request_id)

    inicio = time.perf_counter()
    response = await call_next(request)
    duracao_ms = (time.perf_counter() - inicio) * 1000

    # Injeta cabeçalhos padronizados para telemetria no frontend
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duracao_ms:.2f}"
    return response


# =============================================================================
# Probes de Observabilidade (Liveness e Readiness) e Métricas na Raiz
# =============================================================================

@app.get(
    "/healthz",
    tags=["Observabilidade"],
    summary="Liveness Probe",
    description="Indica se o processo da aplicação está vivo e respondendo.",
)
async def healthz() -> dict[str, str]:
    """Retorna status HTTP 200 rápido para checagem de liveness de contêineres e balanceadores."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get(
    "/readyz",
    tags=["Observabilidade"],
    summary="Readiness Probe",
    description="Verifica se o pool HTTP compartilhado está ativo e o disco tem permissão de escrita.",
)
async def readyz() -> JSONResponse:
    """Retorna 200 se a aplicação estiver apta a receber tráfego, ou 503 se algum recurso falhar."""
    http_pronto = (
        hasattr(app.state, "http_client")
        and isinstance(app.state.http_client, httpx.AsyncClient)
        and not app.state.http_client.is_closed
    )
    pasta_dados = settings.obter_caminho_dados().parent
    pasta_gravavel = os.access(pasta_dados, os.W_OK) if pasta_dados.exists() else False

    esta_pronto = http_pronto and pasta_gravavel
    conteudo = {
        "status": "ready" if esta_pronto else "not_ready",
        "http_client": http_pronto,
        "storage_writable": pasta_gravavel,
    }

    status_code = status.HTTP_200_OK if esta_pronto else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=conteudo)


# Inclusão dos routers com versionamento /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(roteiros_router, prefix="/api/v1")
app.include_router(telemetria_router, prefix="/api/v1")

# Exposição direta de /metrics na raiz para conformidade com raspadores do Prometheus
app.include_router(telemetria_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

