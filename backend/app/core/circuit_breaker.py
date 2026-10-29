"""Implementação assíncrona do padrão Circuit Breaker para resiliência de serviços externos."""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Coroutine
from app.core.logging_config import logger


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Exceção levantada quando uma chamada é bloqueada com o circuito aberto."""


class CircuitBreaker:
    """Controlador de resiliência com estados Closed, Open e Half-Open."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max_trials: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_trials = half_open_max_trials

        self.state: CircuitState = CircuitState.CLOSED
        self.failure_count: int = 0
        self.success_count: int = 0
        self.last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    def get_state(self) -> dict[str, Any]:
        """Retorna o estado atual estruturado para telemetria."""
        tempo_aberto = (
            max(0.0, self.recovery_timeout - (time.time() - self.last_failure_time))
            if self.state == CircuitState.OPEN
            else 0.0
        )
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "tempo_restante_aberto_segundos": round(tempo_aberto, 2),
        }

    async def _before_call(self) -> None:
        """Verifica se a chamada é permitida conforme o estado atual."""
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time >= self.recovery_timeout:
                logger.warning(
                    "CircuitBreaker '%s': Janela de recuperação atingida. Movendo para HALF-OPEN.",
                    self.name,
                )
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerError(
                    f"CircuitBreaker '{self.name}' está ABERTO. Chamada cancelada preventivamente."
                )

    async def _on_success(self) -> None:
        """Registra sucesso na chamada."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_trials:
                logger.info(
                    "CircuitBreaker '%s': Prova de recuperação bem-sucedida. Movendo para CLOSED.",
                    self.name,
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    async def _on_failure(self, exc: Exception) -> None:
        """Registra falha e avalia transição para OPEN."""
        self.last_failure_time = time.time()
        self.failure_count += 1
        logger.warning(
            "CircuitBreaker '%s': Falha detectada (%s: %s). Total consecutivo: %d.",
            self.name,
            type(exc).__name__,
            exc,
            self.failure_count,
        )

        if self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    "CircuitBreaker '%s': Limiar de falhas (%d) atingido. Circuito ABERTO por %.1fs.",
                    self.name,
                    self.failure_threshold,
                    self.recovery_timeout,
                )

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        fallback: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Executa uma corotina protegida pelo Circuit Breaker, acionando fallback em falhas."""
        async with self._lock:
            try:
                await self._before_call()
            except CircuitBreakerError as cbe:
                if fallback is not None:
                    if callable(fallback):
                        return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
                    return fallback
                raise cbe

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                await self._on_success()
            return result
        except Exception as exc:
            async with self._lock:
                await self._on_failure(exc)
            if fallback is not None:
                if callable(fallback):
                    return await fallback(*args, **kwargs) if asyncio.iscoroutinefunction(fallback) else fallback(*args, **kwargs)
                return fallback
            raise


# Registro central de disjuntores por serviço
CIRCUIT_BREAKERS: dict[str, CircuitBreaker] = {
    "geocoding": CircuitBreaker("geocoding", failure_threshold=3, recovery_timeout=30.0),
    "clima": CircuitBreaker("clima", failure_threshold=3, recovery_timeout=20.0),
    "rota": CircuitBreaker("rota", failure_threshold=3, recovery_timeout=30.0),
    "altimetria": CircuitBreaker("altimetria", failure_threshold=3, recovery_timeout=20.0),
    "postos": CircuitBreaker("postos", failure_threshold=3, recovery_timeout=20.0),
    "gemini": CircuitBreaker("gemini", failure_threshold=2, recovery_timeout=45.0),
}


def obter_circuit_breaker(name: str) -> CircuitBreaker:
    """Obtém ou instancia um circuit breaker para o provedor especificado."""
    if name not in CIRCUIT_BREAKERS:
        CIRCUIT_BREAKERS[name] = CircuitBreaker(name)
    return CIRCUIT_BREAKERS[name]

