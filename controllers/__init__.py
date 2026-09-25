"""Camada Controller: rotas HTTP organizadas em Blueprints do Flask."""

from flask import Flask

from controllers.api_controller import api_bp
from controllers.auth_controller import auth_bp
from controllers.main_controller import main_bp
from controllers.viagem_controller import viagens_bp


def registrar_controllers(app: Flask) -> None:
    """Registra todos os Blueprints na aplicação."""
    for blueprint in (main_bp, auth_bp, viagens_bp, api_bp):
        app.register_blueprint(blueprint)
