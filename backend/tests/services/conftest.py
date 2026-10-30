"""Fixtures dos testes dos serviços de dados: clientes HTTP simulados, sem rede e sem chave real."""

from collections.abc import Callable

import httpx
import pytest

from app.core.config import settings

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def anyio_backend() -> str:
    """Os testes assíncronos rodam apenas em asyncio."""
    return "asyncio"


@pytest.fixture
def criar_client() -> Callable[[Handler], httpx.AsyncClient]:
    """Fábrica de `httpx.AsyncClient` cujas respostas vêm de uma função, sem nenhuma chamada de rede."""

    def _criar(handler: Handler) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return _criar


@pytest.fixture
def sem_chave_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove a chave do Gemini do ambiente e das configurações."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")


@pytest.fixture
def com_chave_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Define uma chave fictícia (o SDK é substituído por um cliente falso nos testes)."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
