"""Aplicação Flask Principal - Guia do Turista Inteligente."""

from typing import Any

import httpx
from flask import Flask, redirect, render_template, request, url_for

from config import ESTADOS_BRASIL, PORT
from planejamento import obter_guia_destino
from services import buscar_coordenadas, obter_clima, obter_percurso

app = Flask(__name__)

# Banco de dados de viagens em memória: lista de dicionários com cada roteiro planejado
viagens_db: list[dict[str, Any]] = []


@app.route("/", methods=["GET"])
def index():
    # Renderiza a página principal com o formulário e a lista de roteiros salvos.
    # Renderize o template 'index.html' passando a lista de UFs (disponíveis em config.py como ESTADOS_BRASIL) e a lista de viagens salvas em memória (viagens_db).
    return render_template("index.html", ufs=list(ESTADOS_BRASIL.keys()), viagens=viagens_db)


@app.route("/viagens/criar", methods=["POST"])
def criar_viagem():
    # Processa o formulário de criação de viagem consumindo as APIs externas com HTTPX e IA Gemini.
    # Obtenha os dados enviados pelo formulário via request.form (origem_cidade, origem_uf, destino_cidade, destino_uf), orquestre as chamadas com httpx.Client() para obter coordenadas (origem e destino), previsão do tempo no destino e percurso rodoviário via services.py, gere as dicas turísticas via planejamento.py, adicione o novo roteiro à lista viagens_db e redirecione para a página inicial ('/').
    return redirect(url_for("index"))


@app.route("/viagens/deletar/<string:viagem_id>", methods=["POST"])
def deletar_viagem(viagem_id: str):
    # Remove um roteiro da lista em memória a partir do seu identificador.
    # Localize e remova o roteiro com o id correspondente da lista viagens_db e redirecione o usuário de volta para a rota principal ('/').
    return redirect(url_for("index"))


if __name__ == "__main__":
    print(f"🌍 Servidor Flask Guia do Turista rodando em http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
