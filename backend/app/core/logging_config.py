"""Configuração de logging estruturado com Correlation-ID rastreável via ContextVar."""

import logging
import sys
from contextvars import ContextVar

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    """Retorna o correlation ID ativo no contexto da requisição atual."""
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Define o correlation ID para o contexto da requisição atual."""
    correlation_id_ctx.set(correlation_id)


class CorrelationIdFilter(logging.Filter):
    """Filtro de logging que injeta o correlation_id atual em cada registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """Configura o logger raiz com formatação uniforme e filtro de Correlation-ID."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [req_id=%(correlation_id)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())

    root_logger = logging.getLogger()
    # Evita duplicação de handlers se chamado múltiplas vezes
    if not any(isinstance(f, CorrelationIdFilter) for h in root_logger.handlers for f in h.filters):
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(level)


logger = logging.getLogger("guia_turista_inteligente")

