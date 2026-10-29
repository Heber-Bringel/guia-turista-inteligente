"""Serviço de persistência com isolamento de usuários, escrita atômica e proteção concorrente."""

import asyncio
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.core.config import settings
from app.core.logging_config import logger

_storage_lock = threading.RLock()


def _obter_caminho_arquivo() -> Path:
    """Retorna o caminho resolvido do arquivo viagens.json, garantindo que o diretório exista."""
    caminho = settings.obter_caminho_dados()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


def _estrutura_inicial() -> dict[str, Any]:
    """Cria a estrutura base para o arquivo JSON de persistência."""
    return {
        "versao_schema": "2.0",
        "descricao": "Base consolidada de roteiros turísticos e telemetria por usuário",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total_usuarios": 0,
        "total_roteiros": 0,
        "usuarios": {},
    }


def _ler_dados_sync() -> dict[str, Any]:
    """Lê o arquivo de viagens JSON do disco de forma thread-safe."""
    caminho = _obter_caminho_arquivo()
    if not caminho.exists():
        return _estrutura_inicial()

    try:
        conteudo = caminho.read_text(encoding="utf-8")
        if not conteudo.strip():
            return _estrutura_inicial()
        dados = json.loads(conteudo)
        if not isinstance(dados, dict):
            return _estrutura_inicial()
        if "usuarios" not in dados or not isinstance(dados["usuarios"], dict):
            dados["usuarios"] = {}
        return dados
    except Exception as exc:
        logger.error("Erro ao ler %s: %s. Usando estrutura limpa.", caminho, exc)
        return _estrutura_inicial()


def _escrever_dados_atomico_sync(dados: dict[str, Any]) -> None:
    """Executa a escrita atômica via arquivo temporário + os.replace para evitar JSON parcial."""
    caminho = _obter_caminho_arquivo()
    diretorio = caminho.parent

    # Atualiza metadados globais
    dados["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    usuarios = dados.get("usuarios", {})
    dados["total_usuarios"] = len(usuarios)
    total_roteiros = 0
    for u in usuarios.values():
        if isinstance(u, dict):
            roteiros = u.get("roteiros") or u.get("viagens") or []
            if isinstance(roteiros, list):
                total_roteiros += len(roteiros)
    dados["total_roteiros"] = total_roteiros

    conteudo_json = json.dumps(dados, ensure_ascii=False, indent=2)

    temp_fd, temp_path = tempfile.mkstemp(dir=diretorio, prefix="viagens_tmp_", suffix=".json")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(conteudo_json)
            f.flush()
            os.fsync(f.fileno())

        # Substituição atômica no filesystem
        os.replace(temp_path, caminho)
    except Exception as exc:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        logger.error("Falha na escrita atômica do arquivo de viagens: %s", exc)
        raise exc


def salvar_nova_viagem_sync(user_id: str, viagem: dict[str, Any]) -> dict[str, Any]:
    """Adiciona uma nova viagem ao histórico do usuário com garantia thread-safe e atômica."""
    with _storage_lock:
        dados = _ler_dados_sync()
        usuarios = dados.setdefault("usuarios", {})
        usuario_dados = usuarios.setdefault(user_id, {"perfil": {"id": user_id}, "roteiros": []})
        roteiros = usuario_dados.setdefault("roteiros", [])

        # Remove se já existia com mesmo id (atualização idempotente)
        roteiro_id = viagem.get("id")
        if roteiro_id:
            roteiros[:] = [r for r in roteiros if r.get("id") != roteiro_id]

        roteiros.insert(0, viagem)
        _escrever_dados_atomico_sync(dados)
        return viagem


def listar_viagens_usuario_sync(user_id: str) -> list[dict[str, Any]]:
    """Lista exclusivamente os roteiros pertencentes ao usuário solicitado (isolamento total)."""
    with _storage_lock:
        dados = _ler_dados_sync()
        usuario_dados = dados.get("usuarios", {}).get(user_id)
        if not usuario_dados or not isinstance(usuario_dados, dict):
            return []
        roteiros = usuario_dados.get("roteiros") or usuario_dados.get("viagens") or []
        return list(roteiros)


def obter_viagem_usuario_sync(user_id: str, roteiro_id: str) -> dict[str, Any] | None:
    """Busca um roteiro específico pelo ID, garantindo posse pelo usuário."""
    with _storage_lock:
        viagens = listar_viagens_usuario_sync(user_id)
        for v in viagens:
            if v.get("id") == roteiro_id:
                return v
        return None


def deletar_viagem_usuario_sync(user_id: str, roteiro_id: str) -> bool:
    """Deleta um roteiro pertencente ao usuário. Retorna True se deletou, False se não encontrado."""
    with _storage_lock:
        dados = _ler_dados_sync()
        usuario_dados = dados.get("usuarios", {}).get(user_id)
        if not usuario_dados or not isinstance(usuario_dados, dict):
            return False

        roteiros = usuario_dados.get("roteiros") or usuario_dados.get("viagens") or []
        tamanho_original = len(roteiros)
        roteiros_filtrados = [r for r in roteiros if r.get("id") != roteiro_id]

        if len(roteiros_filtrados) == tamanho_original:
            return False

        usuario_dados["roteiros"] = roteiros_filtrados
        _escrever_dados_atomico_sync(dados)
        return True


def marcar_atrativo_visitado_sync(
    user_id: str, roteiro_id: str, atrativo_id: str, visitado: bool
) -> dict[str, Any] | None:
    """Atualiza o status de visitação de um atrativo ou parada em um roteiro do usuário."""
    with _storage_lock:
        dados = _ler_dados_sync()
        usuario_dados = dados.get("usuarios", {}).get(user_id)
        if not usuario_dados or not isinstance(usuario_dados, dict):
            return None

        roteiros = usuario_dados.get("roteiros") or usuario_dados.get("viagens") or []
        roteiro_alvo = None
        for r in roteiros:
            if r.get("id") == roteiro_id:
                roteiro_alvo = r
                break

        if not roteiro_alvo:
            return None

        alterado = False
        # Atualiza em atrativos
        for atrativo in roteiro_alvo.get("atrativos", []):
            if atrativo.get("id") == atrativo_id:
                atrativo["visitado"] = visitado
                alterado = True

        # Atualiza em paradas também se corresponder
        for parada in roteiro_alvo.get("paradas", []):
            if parada.get("id") == atrativo_id:
                parada["visitado"] = visitado
                alterado = True

        if alterado:
            _escrever_dados_atomico_sync(dados)

        return roteiro_alvo


# Versões assíncronas que usam asyncio.to_thread para não bloquear o event loop do FastAPI:

async def salvar_nova_viagem(user_id: str, viagem: dict[str, Any]) -> dict[str, Any]:
    """Salva uma nova viagem de forma assíncrona sem bloquear o event loop."""
    return await asyncio.to_thread(salvar_nova_viagem_sync, user_id, viagem)


async def listar_viagens_usuario(user_id: str) -> list[dict[str, Any]]:
    """Lista as viagens do usuário de forma assíncrona."""
    return await asyncio.to_thread(listar_viagens_usuario_sync, user_id)


async def obter_viagem_usuario(user_id: str, roteiro_id: str) -> dict[str, Any] | None:
    """Obtém uma viagem específica de forma assíncrona."""
    return await asyncio.to_thread(obter_viagem_usuario_sync, user_id, roteiro_id)


async def deletar_viagem_usuario(user_id: str, roteiro_id: str) -> bool:
    """Deleta uma viagem do usuário de forma assíncrona."""
    return await asyncio.to_thread(deletar_viagem_usuario_sync, user_id, roteiro_id)


async def marcar_atrativo_visitado(
    user_id: str, roteiro_id: str, atrativo_id: str, visitado: bool
) -> dict[str, Any] | None:
    """Marca visita em atrativo ou parada de forma assíncrona."""
    return await asyncio.to_thread(
        marcar_atrativo_visitado_sync, user_id, roteiro_id, atrativo_id, visitado
    )

