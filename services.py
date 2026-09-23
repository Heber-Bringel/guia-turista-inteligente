# Serviços de integração com APIs externas (Google OAuth, Open-Meteo e OSRM)

import re
import unicodedata
from typing import Any

import httpx

from config import ESTADOS_BRASIL, GOOGLE_CLIENT_ID

# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 1: APIs REST, Autenticação JWT e Geocodificação
# ==============================================================================


def verificar_token_google(client: httpx.Client, token: str) -> dict[str, Any] | None:
    """Valida o token JWT no endpoint oficial 'https://oauth2.googleapis.com/tokeninfo'.

    Verifica se o token foi emitido para o GOOGLE_CLIENT_ID configurado no projeto
    e retorna o payload do usuário (sub, name, email, picture) ou None se for inválido.
    """
    # TODO (Aluno 1): Implementar a validação do token JWT junto à API do Google OAuth2
    pass


def obter_sigla_uf(admin1: str, uf_informada: str = "") -> str:
    """Converte o estado retornado pela API (admin1) para a sigla oficial de 2 letras (ex: 'PI').

    Caso a API retorne um nome completo (ex: 'Piauí'), normaliza para a sigla 'PI'.
    Caso contrário, utiliza a UF informada como fallback se for válida.
    """

    def _normalizar(texto: str) -> str:
        """Remove acentos e converte para minúsculas para comparação robusta."""
        return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower().strip()

    admin1_normalizado = _normalizar(admin1)

    # Monta mapa invertido: nome normalizado → sigla (ex: "piaui" → "PI")
    mapa_nome_para_sigla = {_normalizar(nome): sigla for sigla, nome in ESTADOS_BRASIL.items()}

    # Tenta encontrar pelo nome normalizado do campo admin1
    if admin1_normalizado in mapa_nome_para_sigla:
        return mapa_nome_para_sigla[admin1_normalizado]

    # Fallback: verifica se o próprio admin1 já é uma sigla válida (ex: "PI")
    admin1_upper = admin1.strip().upper()
    if admin1_upper in ESTADOS_BRASIL:
        return admin1_upper

    # Fallback final: usa a UF informada pelo usuário, se válida
    uf_upper = uf_informada.strip().upper()
    if uf_upper in ESTADOS_BRASIL:
        return uf_upper

    return ""


def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Consulta o Open-Meteo Geocoding com filtro Brasil (country_codes=BR) e timeout=4.0s.

    Retorna a tupla (latitude, longitude, nome_formatado). Caso a busca falhe,
    aplica fallback seguro retornando (0.0, 0.0, "Cidade - UF").
    """
    # TODO (Aluno 1): Implementar a consulta à API de Geocodificação Open-Meteo com filtro Brasil
    pass


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 2: Telemetria Climática e Roteamento Rodoviário
# ==============================================================================


def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Consulta o Open-Meteo Forecast e retorna temperatura (°C), umidade (%) e vento (km/h).

    Caso coordenadas sejam inválidas (0.0, 0.0) ou ocorra timeout (4.0s),
    retorna dicionário de contingência com valores 'N/D'.
    """
    # TODO (Aluno 2): Implementar a consulta à API Open-Meteo Forecast com timeout e fallback
    pass


def obter_percurso(
    client: httpx.Client, lat_o: float, lon_o: float, lat_d: float, lon_d: float
) -> dict[str, str]:
    """Consulta o OSRM e calcula distância em km e duração de viagem de carro.

    Em caso de trajetos sem estradas (ex: ilhas) ou timeout (6.0s),
    retorna dicionário com fallback descritivo ('Sem rota direta' / 'Considere voos ou barcos').
    """
    # TODO (Aluno 2): Implementar o cálculo de rota e distância via OSRM com conversão de unidades
    pass
