# Serviços de integração com APIs externas (Google OAuth, Open-Meteo e OSRM)

from typing import Any

import httpx

from config import ESTADOS_BRASIL, GOOGLE_CLIENT_ID


def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
    """Valida o token JWT do Google Identity Services junto aos servidores do Google."""
    # Valide o ID token JWT junto ao endpoint de tokeninfo do Google, verificando o status de sucesso (200) e a correspondência do Client ID (aud). Retorne os dados do usuário ou None se inválido.
    return None


def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Obtém (latitude, longitude, nome_formatado) de uma cidade brasileira via Open-Meteo Geocoding."""
    # Consulte a API de Geocoding do Open-Meteo para converter o nome da cidade e UF em coordenadas geográficas no Brasil. Retorne (latitude, longitude, nome_formatado) ou coordenadas zeradas (0.0, 0.0) em caso de falha.
    return None


def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Obtém temperatura, umidade e vento atuais na cidade de destino via Open-Meteo Weather."""
    # Consulte a API de previsão meteorológica do Open-Meteo para obter temperatura, umidade e velocidade do vento atuais nas coordenadas informadas, retornando um dicionário com os valores formatados ou 'N/D'.
    return None


def obter_percurso(
    client: httpx.Client, lat_o: float, lon_o: float, lat_d: float, lon_d: float
) -> dict[str, str]:
    """Calcula distância e tempo de viagem de carro via OSRM."""
    # Calcule a rota rodoviária entre a origem e o destino utilizando a API pública do OSRM, retornando um dicionário com a distância formatada em km e a duração estimada em horas e minutos de carro.
    return None
