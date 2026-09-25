"""Controller — autenticação (Google OAuth, modo visitante e logout)."""

import uuid

import httpx
from flask import Blueprint, redirect, request, session, url_for

from models.viagem_repository import encerrar_visitante, iniciar_visitante
from services import verificar_token_google

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/auth/google/callback", methods=["POST"])
def google_callback():
    """Valida o token Google e cria a sessão do usuário."""

    token = request.form.get("credential", "").strip()

    if not token:
        return redirect(url_for("main.index"))

    with httpx.Client() as client:
        dados_usuario = verificar_token_google(client, token)

    if not dados_usuario:
        return redirect(url_for("main.index"))

    user_id = dados_usuario.get("sub")

    if not isinstance(user_id, str) or not user_id:
        return redirect(url_for("main.index"))

    session["usuario"] = {
        "id": user_id,
        "nome": dados_usuario.get("name", "Usuário Google"),
        "email": dados_usuario.get("email", ""),
        "foto": dados_usuario.get("picture", ""),
        "visitante": False,
    }

    return redirect(url_for("main.index"))


@auth_bp.route("/auth/demo", methods=["GET", "POST"])
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

    iniciar_visitante(user_id)

    return redirect(url_for("main.index"))


@auth_bp.route("/auth/logout", methods=["GET", "POST"])
def logout():
    """Encerra a sessão e descarta a memória de visitante."""

    usuario = session.get("usuario")

    if isinstance(usuario, dict):
        user_id = usuario.get("id")
        visitante = usuario.get("visitante", False)

        if visitante and isinstance(user_id, str):
            encerrar_visitante(user_id)

    session.clear()

    return redirect(url_for("main.index"))
