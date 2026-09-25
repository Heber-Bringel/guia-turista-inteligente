"""Model — persistência dos roteiros (JSON thread-safe) e armazenamento volátil dos visitantes."""

import json
import threading
from datetime import datetime, timezone
from typing import Any

from config import DATA_DIR, VIAGENS_FILE

# Controle de concorrência reentrante para leitura e escrita segura no arquivo JSON
DATA_DIR.mkdir(parents=True, exist_ok=True)
lock_arquivo_json = threading.RLock()

# Armazenamento volátil de roteiros em memória para sessões de visitantes
viagens_visitante_memoria: dict[str, list[dict[str, Any]]] = {}


def eh_usuario_visitante(
    user_id: str,
    perfil_usuario: dict[str, Any] | None = None,
) -> bool:
    """Verifica de forma definitiva se o usuário é visitante (mesmo se a memória zerar após reinício)."""
    if isinstance(user_id, str) and user_id.startswith(("visitante", "guest")):
        return True
    return bool(perfil_usuario and isinstance(perfil_usuario, dict) and perfil_usuario.get("visitante") is True)


def _contar_roteiros(usuarios: dict[str, Any]) -> int:
    """Soma os roteiros de todos os usuários (aceita a chave atual 'roteiros' e a legada 'viagens')."""
    total = 0
    for usuario in usuarios.values():
        if isinstance(usuario, dict):
            roteiros = usuario.get("roteiros") or usuario.get("viagens")
            if isinstance(roteiros, list):
                total += len(roteiros)
    return total


def criar_estrutura_padrao_viagens() -> dict[str, Any]:
    """Retorna a estrutura inicial do payload JSON de viagens com metadados e provedores."""
    return {
        "versao_schema": "1.0",
        "descricao": "Base consolidada de roteiros turísticos e telemetria por usuário",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
        "total_usuarios": 0,
        "total_roteiros": 0,
        "provedores": {
            "geocoding": "Open-Meteo Geocoding API",
            "previsao_tempo": "Open-Meteo Forecast API",
            "roteamento": "OSRM Routing Engine",
            "inteligencia_artificial": "Google Gemini (gemini-3.6-flash)",
        },
        "usuarios": {},
    }


def carregar_dados_viagens_json() -> dict[str, Any]:
    """Lê a base completa de viagens de static/data/viagens.json de forma thread-safe."""
    with lock_arquivo_json:
        if not VIAGENS_FILE.exists():
            return criar_estrutura_padrao_viagens()

        try:
            with VIAGENS_FILE.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)

            if not isinstance(dados, dict):
                return criar_estrutura_padrao_viagens()

            return dados

        except (json.JSONDecodeError, OSError):
            return criar_estrutura_padrao_viagens()


def salvar_dados_viagens_json(dados_completos: dict[str, Any]) -> None:
    """Persiste a base hierárquica em static/data/viagens.json com escrita thread-safe."""
    with lock_arquivo_json:
        dados_completos["atualizado_em"] = datetime.now(timezone.utc).isoformat()

        # Proteção defensiva: remove quaisquer nós de visitantes acidentalmente repassados
        usuarios = dados_completos.get("usuarios")
        if isinstance(usuarios, dict):
            dados_completos["usuarios"] = {
                uid: uinfo
                for uid, uinfo in usuarios.items()
                if not eh_usuario_visitante(
                    uid,
                    uinfo.get("perfil") if isinstance(uinfo, dict) else None,
                )
            }
            dados_completos["total_usuarios"] = len(dados_completos["usuarios"])
            dados_completos["total_roteiros"] = _contar_roteiros(dados_completos["usuarios"])

        with VIAGENS_FILE.open("w", encoding="utf-8") as arquivo:
            json.dump(
                dados_completos,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )


def obter_viagens_usuario(user_id: str) -> list[dict[str, Any]]:
    """Recupera os roteiros do visitante em memória ou do usuário logado no JSON."""
    with lock_arquivo_json:
        if eh_usuario_visitante(user_id):
            return list(viagens_visitante_memoria.setdefault(user_id, []))

        dados = carregar_dados_viagens_json()

        usuarios = dados.get("usuarios", {})

        if not isinstance(usuarios, dict):
            return []

        usuario = usuarios.get(user_id, {})

        if not isinstance(usuario, dict):
            return []

        roteiros = usuario.get("roteiros")
        if roteiros is None:
            roteiros = usuario.get("viagens", [])

        if not isinstance(roteiros, list):
            return []

        return list(roteiros)


def adicionar_viagem_usuario(
    user_id: str,
    item: dict[str, Any],
    perfil_usuario: dict[str, Any] | None = None,
) -> None:
    """Adiciona um novo roteiro na memória do visitante ou no JSON do usuário logado."""
    with lock_arquivo_json:
        # Visitante: mantém os roteiros somente em memória (mesmo após reinício do servidor).
        if eh_usuario_visitante(user_id, perfil_usuario):
            viagens_visitante_memoria.setdefault(user_id, []).append(item)
            return

        # Usuário logado: recupera a base persistida.
        dados = carregar_dados_viagens_json()

        usuarios = dados.setdefault("usuarios", {})
        agora_iso = datetime.now(timezone.utc).isoformat()

        # Normaliza o perfil garantindo o campo 'foto' conforme schema
        perfil = dict(perfil_usuario or {})
        if "picture" in perfil and "foto" not in perfil:
            perfil["foto"] = perfil["picture"]

        if user_id not in usuarios or not isinstance(usuarios[user_id], dict):
            usuarios[user_id] = {
                "perfil": perfil,
                "metadados": {
                    "total_roteiros": 0,
                    "criado_em": agora_iso,
                    "atualizado_em": agora_iso,
                },
                "roteiros": [],
            }

        usuario = usuarios[user_id]

        if not usuario.get("perfil") and perfil:
            usuario["perfil"] = perfil

        # Migração defensiva: se o usuário continha a chave legada 'viagens', migra para 'roteiros'
        if "viagens" in usuario and "roteiros" not in usuario:
            usuario["roteiros"] = usuario.pop("viagens")

        roteiros = usuario.setdefault("roteiros", [])

        if not isinstance(roteiros, list):
            roteiros = []
            usuario["roteiros"] = roteiros

        roteiros.append(item)

        # Atualiza metadados do usuário conforme schema
        usuario["metadados"] = {
            "total_roteiros": len(roteiros),
            "criado_em": roteiros[0].get("criado_em", agora_iso) if roteiros else agora_iso,
            "atualizado_em": roteiros[-1].get("criado_em", agora_iso) if roteiros else agora_iso,
        }

        dados["total_usuarios"] = len(usuarios)

        salvar_dados_viagens_json(dados)


def remover_viagem_usuario(user_id: str, viagem_id: str) -> None:
    """Remove um roteiro específico pelo ID."""
    with lock_arquivo_json:
        # Visitante: remove a viagem somente da memória.
        if eh_usuario_visitante(user_id):
            viagens = viagens_visitante_memoria.get(user_id, [])

            viagens_visitante_memoria[user_id] = [
                viagem
                for viagem in viagens
                if viagem.get("id") != viagem_id
            ]

            return

        # Usuário logado: remove a viagem do arquivo JSON.
        dados = carregar_dados_viagens_json()

        usuarios = dados.get("usuarios", {})

        if not isinstance(usuarios, dict):
            return

        usuario = usuarios.get(user_id)

        if not isinstance(usuario, dict):
            return

        if "viagens" in usuario and "roteiros" not in usuario:
            usuario["roteiros"] = usuario.pop("viagens")

        roteiros = usuario.get("roteiros", [])

        if not isinstance(roteiros, list):
            return

        usuario["roteiros"] = [
            roteiro
            for roteiro in roteiros
            if roteiro.get("id") != viagem_id
        ]

        novos_roteiros = usuario["roteiros"]
        usuario["metadados"] = {
            "total_roteiros": len(novos_roteiros),
            "criado_em": novos_roteiros[0].get("criado_em", "") if novos_roteiros else "",
            "atualizado_em": novos_roteiros[-1].get("criado_em", "") if novos_roteiros else "",
        }

        salvar_dados_viagens_json(dados)


def iniciar_visitante(user_id: str) -> None:
    """Reserva a área em memória do visitante recém-criado."""
    with lock_arquivo_json:
        viagens_visitante_memoria[user_id] = []


def encerrar_visitante(user_id: str) -> None:
    """Descarta a memória do visitante ao encerrar a sessão."""
    with lock_arquivo_json:
        viagens_visitante_memoria.pop(user_id, None)


def obter_roteiros_visitante(usuario: Any) -> tuple[str, list[dict[str, Any]]] | None:
    """Retorna (user_id, roteiros) se a sessão for de um visitante com viagens em memória.

    Encapsula a verificação em cascata: sessão ativa → é visitante → tem roteiros salvos.
    Retorna None se qualquer condição não for satisfeita.
    """
    if not usuario or not isinstance(usuario, dict):
        return None

    user_id = str(usuario.get("id", ""))
    if not eh_usuario_visitante(user_id, usuario):
        return None

    with lock_arquivo_json:
        roteiros = viagens_visitante_memoria.get(user_id, [])
        if not roteiros:
            return None

        return user_id, list(roteiros)


def montar_payload_consolidado(usuario_sessao: Any) -> dict[str, Any]:
    """Base consolidada do JSON, mesclada com as viagens em memória do visitante da sessão (se houver)."""
    with lock_arquivo_json:
        dados = carregar_dados_viagens_json() or criar_estrutura_padrao_viagens()

        # Mescla as viagens do visitante em memória (se houver sessão ativa)
        visitante = obter_roteiros_visitante(usuario_sessao)
        if visitante:
            user_id, roteiros_mem = visitante
            perfil = dict(usuario_sessao)
            if "picture" in perfil and "foto" not in perfil:
                perfil["foto"] = perfil["picture"]

            agora_iso = datetime.now(timezone.utc).isoformat()
            dados.setdefault("usuarios", {})[user_id] = {
                "perfil": perfil,
                "metadados": {
                    "total_roteiros": len(roteiros_mem),
                    "criado_em": roteiros_mem[0].get("criado_em", agora_iso) if roteiros_mem else agora_iso,
                    "atualizado_em": roteiros_mem[-1].get("criado_em", agora_iso) if roteiros_mem else agora_iso,
                },
                "roteiros": list(roteiros_mem),
            }

        usuarios = dados.get("usuarios", {})
        if isinstance(usuarios, dict):
            dados["total_usuarios"] = len(usuarios)
            dados["total_roteiros"] = _contar_roteiros(usuarios)

        return dados
