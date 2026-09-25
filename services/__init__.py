"""Camada de serviços: integrações com APIs externas (Google, Open-Meteo, OSRM e Gemini)."""

from services.clima import obter_clima
from services.contingencia import gerar_guia_contingencia
from services.gemini import obter_guia_destino, obter_guia_destino_com_diagnostico
from services.geocoding import (
    buscar_coordenadas,
    eh_coordenada_de_fallback,
    obter_sigla_uf,
)
from services.google_auth import verificar_token_google
from services.rotas import obter_percurso
from services.sanitizacao import limpar_formato_texto

__all__ = [
    "buscar_coordenadas",
    "eh_coordenada_de_fallback",
    "gerar_guia_contingencia",
    "limpar_formato_texto",
    "obter_clima",
    "obter_guia_destino",
    "obter_guia_destino_com_diagnostico",
    "obter_percurso",
    "obter_sigla_uf",
    "verificar_token_google",
]
