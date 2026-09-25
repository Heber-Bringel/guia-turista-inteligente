"""Controller — página principal."""

from flask import Blueprint, render_template, session

from config import ESTADOS_BRASIL, GOOGLE_CLIENT_ID
from models.viagem_repository import obter_viagens_usuario

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
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
