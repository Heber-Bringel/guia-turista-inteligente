"""Pacote de serviços da aplicação FastAPI."""

from app.services.storage_service import (
    deletar_viagem_usuario,
    listar_viagens_usuario,
    marcar_atrativo_visitado,
    obter_viagem_usuario,
    salvar_nova_viagem,
)

__all__ = [
    "deletar_viagem_usuario",
    "listar_viagens_usuario",
    "marcar_atrativo_visitado",
    "obter_viagem_usuario",
    "salvar_nova_viagem",
]

