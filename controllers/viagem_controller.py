"""Controller — criação e exclusão de roteiros (PRG + idempotência contra cliques duplos)."""

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from flask import Blueprint, redirect, request, session, url_for

from config import ESTADOS_BRASIL
from controllers.validacao import sanitizar_entrada
from models.viagem_repository import adicionar_viagem_usuario, remover_viagem_usuario
from services import (
    buscar_coordenadas,
    eh_coordenada_de_fallback,
    obter_clima,
    obter_guia_destino_com_diagnostico,
    obter_percurso,
)

viagens_bp = Blueprint("viagens", __name__)

# Controle de concorrência e idempotência contra cliques duplicados
requisicoes_ativas: set[str] = set()
requisicoes_recentes: dict[str, float] = {}
lock_requisicoes = threading.Lock()


def _status_geocoding(lat: float, lon: float, uf: str) -> dict[str, str]:
    """Descreve no metadado se as coordenadas foram localizadas ou vieram do fallback (capital da UF)."""
    if eh_coordenada_de_fallback(lat, lon, uf):
        return {
            "status": "fallback",
            "mensagem": "Cidade não localizada; usadas as coordenadas da capital da UF",
        }
    return {"status": "sucesso", "mensagem": "Coordenadas localizadas"}


def _gerar_roteiro(
    origem_cidade: str,
    origem_uf: str,
    destino_cidade: str,
    destino_uf: str,
) -> dict[str, Any]:
    """Orquestra geocoding, clima, rota e IA e devolve o roteiro pronto para ser persistido."""
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
            diagnostico_ia = {"status": "fallback", "modelo": "indisponível", "fallback_utilizado": True}
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
                    "geocoding_origem": _status_geocoding(lat_origem, lon_origem, uf_origem_final),
                    "geocoding_destino": _status_geocoding(lat_destino, lon_destino, uf_destino_final),
                    "inteligencia_artificial": {
                        "status": diagnostico_ia.get("status", "fallback"),
                        "modelo": diagnostico_ia.get("modelo", ""),
                        "fallback_utilizado": diagnostico_ia.get("fallback_utilizado", False),
                    },
                },
            },
        }

    return viagem


@viagens_bp.route("/viagens/criar", methods=["POST"])
def criar_viagem():
    """Processa o formulário de criação e orquestra os serviços externos."""

    usuario = session.get("usuario")

    if not isinstance(usuario, dict):
        return redirect(url_for("main.index"))

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
        return redirect(url_for("main.index"))

    if origem_uf not in ESTADOS_BRASIL or destino_uf not in ESTADOS_BRASIL:
        return redirect(url_for("main.index"))

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
            return redirect(url_for("main.index"))

        ultima_requisicao = requisicoes_recentes.get(chave_requisicao)

        if ultima_requisicao is not None and agora - ultima_requisicao < 10:
            return redirect(url_for("main.index"))

        requisicoes_ativas.add(chave_requisicao)
        requisicoes_recentes[chave_requisicao] = agora

    try:
        viagem = _gerar_roteiro(origem_cidade, origem_uf, destino_cidade, destino_uf)

        adicionar_viagem_usuario(
            usuario["id"],
            viagem,
            perfil_usuario=usuario,
        )
    finally:
        with lock_requisicoes:
            requisicoes_ativas.discard(chave_requisicao)

    return redirect(url_for("main.index"))


@viagens_bp.route("/viagens/deletar/<string:viagem_id>", methods=["POST"])
def deletar_viagem(viagem_id: str):
    """Exclui um roteiro da lista do usuário."""

    usuario = session.get("usuario")

    if not isinstance(usuario, dict):
        return redirect(url_for("main.index"))

    user_id = usuario.get("id")

    if not isinstance(user_id, str) or not user_id:
        return redirect(url_for("main.index"))

    remover_viagem_usuario(user_id, viagem_id)

    return redirect(url_for("main.index"))
