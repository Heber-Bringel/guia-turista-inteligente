"""Pacote de componentes essenciais (core) da aplicação FastAPI."""

from app.core.cache import cache
from app.core.circuit_breaker import CircuitBreaker, CircuitState, obter_circuit_breaker
from app.core.config import settings
from app.core.dependencies import obter_http_client, obter_usuario_ativo
from app.core.logging_config import get_correlation_id, logger, set_correlation_id, setup_logging

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "cache",
    "get_correlation_id",
    "logger",
    "obter_circuit_breaker",
    "obter_http_client",
    "obter_usuario_ativo",
    "set_correlation_id",
    "settings",
    "setup_logging",
]

