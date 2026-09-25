"""Aplicação Flask Principal - Guia do Turista Inteligente (API Gateway em Python)."""

import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from config import (
    DATA_DIR,
    ESTADOS_BRASIL,
    GOOGLE_CLIENT_ID,
    PORT,
    VIAGENS_FILE,
)
from planejamento import obter_guia_destino_com_diagnostico
from services import (
    buscar_coordenadas,
    obter_clima,
    obter_percurso,
    verificar_token_google,
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "guia-turista-secret-key-2026-python")

# Controle de concorrência reentrante para leitura e escrita segura no arquivo JSON
DATA_DIR.mkdir(parents=True, exist_ok=True)
lock_arquivo_json = threading.RLock()

# Armazenamento volátil de roteiros em memória para sessões de visitantes
viagens_visitante_memoria: dict[str, list[dict[str, Any]]] = {}

# Controle de concorrência e idempotência contra cliques duplicados
requisicoes_ativas: set[str] = set()
requisicoes_recentes: dict[str, float] = {}
lock_requisicoes = threading.Lock()


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 4: Persistência JSON, Sanitização e Manipulação
# ==============================================================================

def sanitizar_entrada(texto: str, max_len: int = 80) -> str:
    """Higieniza entradas de texto removendo HTML, caracteres de controle e espaços extras."""
    texto = re.sub(r"<[^>]*>", "", texto)
    texto = re.sub(r"[\x00-\x1F\x7F]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()[:max_len]


def eh_usuario_visitante(
    user_id: str,
    perfil_usuario: dict[str, Any] | None = None,
) -> bool:
    """Verifica de forma definitiva se o usuário é visitante (mesmo se a memória zerar após reinício)."""
    if isinstance(user_id, str) and user_id.startswith(("visitante", "guest")):
        return True
    return bool(perfil_usuario and isinstance(perfil_usuario, dict) and perfil_usuario.get("visitante") is True)


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

            total_roteiros = 0
            for u in dados_completos["usuarios"].values():
                if isinstance(u, dict):
                    roteiros_u = u.get("roteiros") or u.get("viagens")
                    if isinstance(roteiros_u, list):
                        total_roteiros += len(roteiros_u)
            dados_completos["total_roteiros"] = total_roteiros

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


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 3: Backend Gateway, Sessões, Rotas & Idempotência
# ==============================================================================


@app.route("/")
def index():
    """Exibe a página principal com sessão e roteiros do usuário."""

    usuario = session.get("usuario")

    viagens = []

    if isinstance(usuario, dict):
        user_id = usuario.get("id")

        if isinstance(user_id, str):
            viagens = obter_viagens_usuario(user_id)

    return render_template(
        "index.html",
        usuario=usuario,
        viagens=viagens,
        ufs=ESTADOS_BRASIL.keys(),
        client_id=GOOGLE_CLIENT_ID,
    )


@app.route("/auth/google/callback", methods=["POST"])
def google_callback():
    """Valida o token Google e cria a sessão do usuário."""

    token = request.form.get("credential", "").strip()

    if not token:
        return redirect(url_for("index"))

    with httpx.Client() as client:
        dados_usuario = verificar_token_google(client, token)

    if not dados_usuario:
        return redirect(url_for("index"))

    user_id = dados_usuario.get("sub")

    if not isinstance(user_id, str) or not user_id:
        return redirect(url_for("index"))

    session["usuario"] = {
        "id": user_id,
        "nome": dados_usuario.get("name", "Usuário Google"),
        "email": dados_usuario.get("email", ""),
        "foto": dados_usuario.get("picture", ""),
        "visitante": False,
    }

    return redirect(url_for("index"))


@app.route("/auth/demo", methods=["GET", "POST"])
def login_demo():
    """Cria uma sessão temporária para o visitante."""

    user_id = f"visitante-{uuid.uuid4().hex}"

    session.clear()

    session["usuario"] = {
        "id": user_id,
        "nome": "Viajante Convidado",
        "email": "",
        "foto": "",
        "picture": "",
        "visitante": True,
    }

    with lock_arquivo_json:
        viagens_visitante_memoria[user_id] = []

    return redirect(url_for("index"))


@app.route("/auth/logout", methods=["GET", "POST"])
def logout():
    """Encerra a sessão e descarta a memória de visitante."""

    usuario = session.get("usuario")

    if isinstance(usuario, dict):
        user_id = usuario.get("id")
        visitante = usuario.get("visitante", False)

        if visitante and isinstance(user_id, str):
            with lock_arquivo_json:
                viagens_visitante_memoria.pop(user_id, None)

    session.clear()

    return redirect(url_for("index"))


@app.route("/viagens/criar", methods=["POST"])
def criar_viagem():
    """Processa o formulário de criação e orquestra os serviços externos."""

    usuario = session.get("usuario")

    if not isinstance(usuario, dict):
        return redirect(url_for("index"))

    origem_cidade = sanitizar_entrada(
        request.form.get("origem_cidade", "")
    )

    origem_uf = sanitizar_entrada(
        request.form.get("origem_uf", ""),
        max_len=2,
    ).upper()

    destino_cidade = sanitizar_entrada(
        request.form.get("destino_cidade", "")
    )

    destino_uf = sanitizar_entrada(
        request.form.get("destino_uf", ""),
        max_len=2,
    ).upper()

    if not origem_cidade or not origem_uf or not destino_cidade or not destino_uf:
        return redirect(url_for("index"))

    if origem_uf not in ESTADOS_BRASIL or destino_uf not in ESTADOS_BRASIL:
        return redirect(url_for("index"))

    chave_requisicao = (
        f"{usuario['id']}|"
        f"{origem_cidade.lower()}|"
        f"{origem_uf}|"
        f"{destino_cidade.lower()}|"
        f"{destino_uf}"
    )

    agora = time.time()

    with lock_requisicoes:
        if chave_requisicao in requisicoes_ativas:
            return redirect(url_for("index"))

        ultima_requisicao = requisicoes_recentes.get(chave_requisicao)

        if ultima_requisicao is not None and agora - ultima_requisicao < 10:
            return redirect(url_for("index"))

        requisicoes_ativas.add(chave_requisicao)
        requisicoes_recentes[chave_requisicao] = agora

    try:
        with httpx.Client() as client:
            lat_origem, lon_origem, uf_origem_det = buscar_coordenadas(
                client,
                origem_cidade,
                origem_uf,
            )

            lat_destino, lon_destino, uf_destino_det = buscar_coordenadas(
                client,
                destino_cidade,
                destino_uf,
            )

            # Garante o uso da UF real detectada pelo Geocoding (ex: Teresina / RJ -> corrigido para PI)
            uf_origem_final = uf_origem_det or origem_uf
            uf_destino_final = uf_destino_det or destino_uf

            nome_origem = f"{origem_cidade} - {uf_origem_final}"
            nome_destino = f"{destino_cidade} - {uf_destino_final}"

            clima_destino = obter_clima(
                client,
                lat_destino,
                lon_destino,
            ) or {"temperatura": "N/D", "umidade": "N/D", "vento": "N/D"}

            percurso = obter_percurso(
                client,
                lat_origem,
                lon_origem,
                lat_destino,
                lon_destino,
            ) or {"distancia": "N/D", "tempo": "N/D", "modal": "carro"}

            res_ia = obter_guia_destino_com_diagnostico(nome_destino)
            if isinstance(res_ia, tuple) and len(res_ia) == 2:
                dicas_destino, diagnostico_ia = res_ia
            else:
                dicas_destino = str(res_ia or "Guia temporariamente indisponível.")
                diagnostico_ia = {"status": "fallback", "fallback": True}
            agora_iso = datetime.now(timezone.utc).isoformat()
            viagem = {
                "id": uuid.uuid4().hex[:8],
                "criado_em": agora_iso,
                "origem": nome_origem,
                "destino": nome_destino,
                "geolocalizacao": {
                    "origem": {
                        "cidade": origem_cidade,
                        "uf": uf_origem_final,
                        "latitude": lat_origem,
                        "longitude": lon_origem,
                    },
                    "destino": {
                        "cidade": destino_cidade,
                        "uf": uf_destino_final,
                        "latitude": lat_destino,
                        "longitude": lon_destino,
                    },
                },
                "telemetria": {
                    "clima": clima_destino,
                    "percurso": percurso,
                },
                "clima": clima_destino,
                "percurso": percurso,
                "dicas_destino": dicas_destino,
                "diagnostico_ia": diagnostico_ia,
                "metadados": {
                    "status_requisicao": "sucesso",
                    "status_servicos": {
                        "geocoding_origem": {
                            "status": "sucesso" if lat_origem else "fallback",
                            "mensagem": "Coordenadas localizadas",
                        },
                        "geocoding_destino": {
                            "status": "sucesso" if lat_destino else "fallback",
                            "mensagem": "Coordenadas localizadas",
                        },
                        "inteligencia_artificial": {
                            "status": "sucesso" if diagnostico_ia else "fallback",
                            "modelo": "gemini-3.6-flash",
                            "fallback_utilizado": (
                                diagnostico_ia.get("fallback", False)
                                if isinstance(diagnostico_ia, dict)
                                else False
                            ),
                        },
                    },
                },
            }

            adicionar_viagem_usuario(
                usuario["id"],
                viagem,
                perfil_usuario=usuario,
            )
    finally:
        with lock_requisicoes:
            requisicoes_ativas.discard(chave_requisicao)
    
    return redirect(url_for("index"))

@app.route("/viagens/deletar/<string:viagem_id>", methods=["POST"])
def deletar_viagem(viagem_id: str):
    """Exclui um roteiro da lista do usuário."""

    usuario = session.get("usuario")

    if not isinstance(usuario, dict):
        return redirect(url_for("index"))

    user_id = usuario.get("id")

    if not isinstance(user_id, str) or not user_id:
        return redirect(url_for("index"))

    remover_viagem_usuario(user_id, viagem_id)

    return redirect(url_for("index"))


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 4: Endpoint REST e Error Handlers Globais
# ==============================================================================


def _obter_roteiros_visitante_ativo() -> tuple[str, list[dict[str, Any]]] | None:
    """Retorna (user_id, roteiros) se houver uma sessão de visitante ativa com viagens em memória.

    Encapsula a verificação em cascata: sessão ativa → é visitante → tem roteiros salvos.
    Retorna None se qualquer condição não for satisfeita.
    """
    usuario = session.get("usuario")
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


@app.route("/viagens/json", methods=["GET"])
@app.route("/api/viagens/json", methods=["GET"])
@app.route("/api/viagens", methods=["GET"])
def ver_viagens_json():
    """Retorna a base consolidada de static/data/viagens.json com suporte dinâmico a visitantes."""
    with lock_arquivo_json:
        dados = carregar_dados_viagens_json() or criar_estrutura_padrao_viagens()

        # Mescla as viagens do visitante em memória (se houver sessão ativa)
        visitante = _obter_roteiros_visitante_ativo()
        if visitante:
            user_id, roteiros_mem = visitante
            perfil = dict(session.get("usuario", {}))
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
            dados["total_roteiros"] = sum(
                len(u.get("roteiros", u.get("viagens", [])))
                for u in usuarios.values()
                if isinstance(u, dict)
            )

        return jsonify(dados)


@app.errorhandler(405)
def metodo_nao_permitido(error):
    """Fallback para acessos GET em rotas POST (ex: digitar /viagens/criar na barra de endereços)."""
    return redirect(url_for("index"))


@app.errorhandler(404)
def pagina_nao_encontrada(error):
    """Fallback para rotas inexistentes redirecionando suavemente para a página principal."""
    return redirect(url_for("index"))

@app.errorhandler(500)
def erro_interno(error):
    """Redireciona erros internos do servidor para a página inicial."""

    return redirect(url_for("index"))

if __name__ == "__main__":
    print(f"🌍 Servidor Flask Guia do Turista rodando em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
