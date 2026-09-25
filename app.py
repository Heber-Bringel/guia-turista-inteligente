"""Aplicação Flask Principal - Guia do Turista Inteligente (API Gateway em Python).

Arquitetura MVC:
    models/       → persistência dos roteiros (JSON thread-safe) e visitantes em memória
    controllers/  → rotas HTTP (Blueprints), validação de entrada, PRG e idempotência
    templates/    → views (Jinja2) e static/ (CSS/JS)
    services/     → integrações externas (Google OAuth, Open-Meteo, OSRM e Gemini)
"""

import os

from flask import Flask

from config import PORT
from controllers import registrar_controllers


def create_app() -> Flask:
    """Fábrica da aplicação Flask."""
    aplicacao = Flask(__name__)
    aplicacao.secret_key = os.getenv("SECRET_KEY", "guia-turista-secret-key-2026-python")
    registrar_controllers(aplicacao)
    return aplicacao


app = create_app()

if __name__ == "__main__":
    print(f"🌍 Servidor Flask Guia do Turista rodando em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
