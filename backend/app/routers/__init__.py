"""Pacote de rotas da API FastAPI."""

from app.routers.auth import router as auth_router
from app.routers.roteiros import router as roteiros_router
from app.routers.telemetria import router as telemetria_router

__all__ = ["auth_router", "roteiros_router", "telemetria_router"]

