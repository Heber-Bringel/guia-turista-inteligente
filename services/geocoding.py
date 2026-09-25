"""Serviço de geocodificação (Open-Meteo Geocoding) e normalização da UF."""

import unicodedata

import httpx

from config import ESTADOS_BRASIL


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


# Coordenadas aproximadas das capitais de cada UF para uso como fallback de geocoding
_COORDS_CAPITAIS: dict[str, tuple[float, float]] = {
    "AC": (-9.974, -67.824),   # Rio Branco
    "AL": (-9.666, -35.735),   # Maceió
    "AP": (0.034, -51.066),    # Macapá
    "AM": (-3.119, -60.022),   # Manaus
    "BA": (-12.972, -38.501),  # Salvador
    "CE": (-3.717, -38.543),   # Fortaleza
    "DF": (-15.779, -47.929),  # Brasília
    "ES": (-20.319, -40.338),  # Vitória
    "GO": (-16.686, -49.264),  # Goiânia
    "MA": (-2.530, -44.302),   # São Luís
    "MT": (-15.601, -56.098),  # Cuiabá
    "MS": (-20.469, -54.620),  # Campo Grande
    "MG": (-19.919, -43.939),  # Belo Horizonte
    "PA": (-1.455, -48.503),   # Belém
    "PB": (-7.115, -34.863),   # João Pessoa
    "PR": (-25.429, -49.271),  # Curitiba
    "PE": (-8.054, -34.881),   # Recife
    "PI": (-5.089, -42.801),   # Teresina
    "RJ": (-22.906, -43.173),  # Rio de Janeiro
    "RN": (-5.795, -35.210),   # Natal
    "RS": (-30.034, -51.217),  # Porto Alegre
    "RO": (-8.761, -63.900),   # Porto Velho
    "RR": (2.819, -60.673),    # Boa Vista
    "SC": (-27.597, -48.549),  # Florianópolis
    "SP": (-23.549, -46.633),  # São Paulo
    "SE": (-10.916, -37.073),  # Aracaju
    "TO": (-10.249, -48.324),  # Palmas
}


def buscar_coordenadas(
    client: httpx.Client, cidade: str, uf: str = ""
) -> tuple[float, float, str]:
    """Consulta o Open-Meteo Geocoding com filtro Brasil (country_codes=BR) e timeout=4.0s.

    Retorna a tupla (latitude, longitude, uf_oficial_detectada). Caso a busca falhe,
    aplica fallback retornando as coordenadas da capital da UF informada.
    """
    nome_busca = f"{cidade.strip()} {uf.strip()}".strip()
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params: dict[str, str | int] = {
        "name": nome_busca,
        "count": 5,
        "language": "pt",
        "country_codes": "BR",
    }

    try:
        resposta = client.get(url, params=params, timeout=4.0)
        resposta.raise_for_status()
        resultados = resposta.json().get("results")

        if resultados:
            primeiro = resultados[0]
            lat: float = primeiro.get("latitude", 0.0)
            lon: float = primeiro.get("longitude", 0.0)
            admin1: str = primeiro.get("admin1", "")
            uf_detectada = obter_sigla_uf(admin1, uf)
            return lat, lon, uf_detectada

    except (httpx.TimeoutException, httpx.HTTPError, Exception):
        pass

    # Fallback: coordenadas da capital da UF informada pelo usuário
    uf_upper = uf.strip().upper()
    if uf_upper in _COORDS_CAPITAIS:
        lat_cap, lon_cap = _COORDS_CAPITAIS[uf_upper]
        return lat_cap, lon_cap, uf_upper

    return 0.0, 0.0, f"{cidade.strip()} - {uf.strip()}"
