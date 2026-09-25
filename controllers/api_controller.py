"""Controller — endpoint REST /viagens/json e handlers globais de erro (404, 405 e 500)."""

from flask import Blueprint, jsonify, redirect, session, url_for

from models.viagem_repository import montar_payload_consolidado

api_bp = Blueprint("api", __name__)


@api_bp.route("/viagens/json", methods=["GET"])
@api_bp.route("/api/viagens/json", methods=["GET"])
@api_bp.route("/api/viagens", methods=["GET"])
def ver_viagens_json():
    """Retorna a base consolidada de static/data/viagens.json com suporte dinâmico a visitantes."""
    return jsonify(montar_payload_consolidado(session.get("usuario")))


@api_bp.app_errorhandler(405)
def metodo_nao_permitido(error):
    """Fallback para acessos GET em rotas POST (ex: digitar /viagens/criar na barra de endereços)."""
    return redirect(url_for("main.index"))


@api_bp.app_errorhandler(404)
def pagina_nao_encontrada(error):
    """Fallback para rotas inexistentes redirecionando suavemente para a página principal."""
    return redirect(url_for("main.index"))


@api_bp.app_errorhandler(500)
def erro_interno(error):
    """Redireciona erros internos do servidor para a página inicial."""

    return redirect(url_for("main.index"))
