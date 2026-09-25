"""Aplicação Flask Principal - Guia do Turista Inteligente (API Gateway em Python)."""

import json
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

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

# Controle de concorrência para leitura e escrita segura no arquivo JSON
DATA_DIR.mkdir(parents=True, exist_ok=True)
lock_arquivo_json = threading.Lock()

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


def criar_estrutura_padrao_viagens() -> dict[str, Any]:
    """Retorna a estrutura inicial do payload JSON de viagens com metadados e provedores."""
    return {
        "versao_schema": "1.0",
        "descricao": "Base consolidada de roteiros turísticos e telemetria por usuário",
        "atualizado_em": datetime.now().isoformat(),
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
        dados_completos["atualizado_em"] = datetime.now().isoformat()

        with VIAGENS_FILE.open("w", encoding="utf-8") as arquivo:
            json.dump(
                dados_completos,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )


def obter_viagens_usuario(user_id: str) -> list[dict[str, Any]]:
    """Recupera os roteiros do visitante em memória ou do usuário logado no JSON."""
    if user_id in viagens_visitante_memoria:
        return viagens_visitante_memoria[user_id]

    dados = carregar_dados_viagens_json()

    usuarios = dados.get("usuarios", {})

    if not isinstance(usuarios, dict):
        return []

    usuario = usuarios.get(user_id, {})

    if not isinstance(usuario, dict):
        return []

    viagens = usuario.get("viagens", [])

    if not isinstance(viagens, list):
        return []

    return viagens


def adicionar_viagem_usuario(
    user_id: str,
    item: dict[str, Any],
    perfil_usuario: dict[str, Any] | None = None,
) -> None:
    """Adiciona um novo roteiro na memória do visitante ou no JSON do usuário logado."""

    # Visitante: mantém os roteiros somente em memória.
    if user_id in viagens_visitante_memoria:
        viagens_visitante_memoria[user_id].append(item)
        return

    # Usuário logado: recupera a base persistida.
    dados = carregar_dados_viagens_json()

    usuarios = dados.setdefault("usuarios", {})

    if user_id not in usuarios:
        usuarios[user_id] = {
            "perfil": perfil_usuario or {},
            "viagens": [],
        }

    usuario = usuarios[user_id]

    if not isinstance(usuario, dict):
        usuario = {
            "perfil": perfil_usuario or {},
            "viagens": [],
        }
        usuarios[user_id] = usuario

    viagens = usuario.setdefault("viagens", [])

    if not isinstance(viagens, list):
        viagens = []
        usuario["viagens"] = viagens

    viagens.append(item)

    dados["total_roteiros"] = sum(
        len(usuario.get("viagens", []))
        for usuario in usuarios.values()
        if isinstance(usuario, dict)
        and isinstance(usuario.get("viagens", []), list)
    )

    dados["total_usuarios"] = len(usuarios)

    salvar_dados_viagens_json(dados)

def remover_viagem_usuario(user_id: str, viagem_id: str) -> None:
    """Remove um roteiro específico pelo ID."""

    # Visitante: remove a viagem somente da memória.
    if user_id in viagens_visitante_memoria:
        viagens = viagens_visitante_memoria[user_id]

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

    viagens = usuario.get("viagens", [])

    if not isinstance(viagens, list):
        return

    usuario["viagens"] = [
        viagem
        for viagem in viagens
        if viagem.get("id") != viagem_id
    ]

    dados["total_roteiros"] = sum(
        len(usuario_item.get("viagens", []))
        for usuario_item in usuarios.values()
        if isinstance(usuario_item, dict)
        and isinstance(usuario_item.get("viagens", []), list)
    )

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

    user_id = f"visitante_{uuid.uuid4().hex}"

    session.clear()

    session["usuario"] = {
        "id": user_id,
        "nome": "Viajante Convidado",
        "email": "visitante@demo.local",
        "foto": "https://lh3.googleusercontent.com/a/default-user=s96-c",
        "picture": "https://lh3.googleusercontent.com/a/default-user=s96-c",
        "visitante": True,
    }

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
            viagens_visitante_memoria.pop(user_id, None)

    session.clear()

    return redirect(url_for("index"))


@app.route("/viagens/criar", methods=["GET", "POST"])
def criar_viagem():
    """Processa o formulário de criação e orquestra os serviços externos."""

    usuario = session.get("usuario")

    if not isinstance(usuario, dict):
        return redirect(url_for("index"))

    if request.method == "GET":
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
            lat_origem, lon_origem, nome_origem = buscar_coordenadas(
                client,
                origem_cidade,
                origem_uf,
            )

            lat_destino, lon_destino, nome_destino = buscar_coordenadas(
                client,
                destino_cidade,
                destino_uf,
            )

            clima_origem = obter_clima(
                client,
                lat_origem,
                lon_origem,
            )

            clima_destino = obter_clima(
                client,
                lat_destino,
                lon_destino,
            )

            percurso = obter_percurso(
                client,
                lat_origem,
                lon_origem,
                lat_destino,
                lon_destino,
            )
            
            dicas_destino, diagnostico_ia = obter_guia_destino_com_diagnostico(
                nome_destino
            )            
            viagem = {
                "id": uuid.uuid4().hex,
                "origem": nome_origem,
                "destino": nome_destino,
                "clima": clima_destino,
                "percurso": percurso,
                "dicas_destino": dicas_destino,
                "diagnostico_ia": diagnostico_ia,
                "criado_em": datetime.now().isoformat(),
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

@app.route("/viagens/deletar/<string:viagem_id>", methods=["GET", "POST"])
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
    if not usuario:
        return None

    user_id: str = usuario.get("id", "")
    if not (user_id.startswith("visitante_") or user_id.startswith("visitante-")):
        return None

    roteiros = viagens_visitante_memoria.get(user_id, [])
    if not roteiros:
        return None

    return user_id, roteiros


@app.route("/viagens/json", methods=["GET"])
@app.route("/api/viagens/json", methods=["GET"])
@app.route("/api/viagens", methods=["GET"])
def ver_viagens_json():
    """Retorna a base consolidada de static/data/viagens.json com suporte dinâmico a visitantes."""
    dados = carregar_dados_viagens_json() or criar_estrutura_padrao_viagens()

    # Mescla as viagens do visitante em memória (se houver sessão ativa)
    visitante = _obter_roteiros_visitante_ativo()
    if visitante:
        user_id, roteiros_mem = visitante
        dados.setdefault("usuarios", {})[user_id] = {
            "perfil": session["usuario"],
            "metadados": {
                "total_roteiros": len(roteiros_mem),
                "criado_em": roteiros_mem[0].get("criado_em", ""),
                "atualizado_em": roteiros_mem[-1].get("criado_em", ""),
            },
            "roteiros": roteiros_mem,
        }

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
