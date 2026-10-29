"""Configuração e fixtures compartilhadas do Pytest para o backend FastAPI."""

import os
import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Garante que o diretório 'backend' esteja no sys.path para importação de app.*
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.cache import cache
from app.main import app


@pytest.fixture(autouse=True)
def isolar_ambiente_teste(tmp_path: Path) -> Generator[None, None, None]:
    """Isola os dados de persistência e limpa o cache entre os testes."""
    arquivo_teste = tmp_path / "viagens_teste.json"
    caminho_original = settings.DATA_FILE_PATH

    settings.DATA_FILE_PATH = str(arquivo_teste)
    cache.clear()

    yield

    settings.DATA_FILE_PATH = caminho_original
    cache.clear()
    if arquivo_teste.exists():
        try:
            arquivo_teste.unlink()
        except OSError:
            pass


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Cliente de teste do FastAPI gerenciado com o ciclo de vida (lifespan)."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Cabeçalhos com usuário comum autenticado para testes."""
    return {"X-User-Id": "usr_teste_mikaelle"}


@pytest.fixture
def auth_headers_visitante() -> dict[str, str]:
    """Cabeçalhos com usuário visitante temporário para testes."""
    return {"X-User-Id": "visitante_a1b2c3d4e5f6"}


@pytest.fixture
def auth_headers_outro_usuario() -> dict[str, str]:
    """Cabeçalhos de um segundo usuário para testes de isolamento de histórico."""
    return {"X-User-Id": "usr_outro_viajante"}

