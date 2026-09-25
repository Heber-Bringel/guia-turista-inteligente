# Serviços de integração com APIs externas (Google OAuth, Open-Meteo e OSRM)

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
    try:
        resposta = client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": token},
            timeout=4.0,
        )
        resposta.raise_for_status()
        payload: dict[str, Any] = resposta.json()

        # Verifica se o token foi emitido para este projeto (campo 'aud' deve bater com o CLIENT_ID)
        if payload.get("aud") != GOOGLE_CLIENT_ID:
            return None

        return payload

    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001
        return None


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

    Retorna a tupla (latitude, longitude, nome_formatado). Caso a busca falhe,
    aplica fallback retornando as coordenadas da capital da UF informada.
    """
    cidade_limpa = cidade.strip()
    url = "https://geocoding-api.open-meteo.com/v1/search"
    # Consulta pelo nome da cidade (padrão mais compatível da API Open-Meteo para Brasil)
    params: dict[str, str | int] = {"name": cidade_limpa, "count": 5, "language": "pt", "country_codes": "BR"}

    try:
        resposta = client.get(url, params=params, timeout=4.0)
        resposta.raise_for_status()
        resultados = resposta.json().get("results")

        if not resultados and uf:
            # Fallback de busca com cidade e UF combinadas
            params["name"] = f"{cidade_limpa} {uf.strip()}"
            resposta = client.get(url, params=params, timeout=4.0)
            resposta.raise_for_status()
            resultados = resposta.json().get("results")

        if resultados:
            primeiro = resultados[0]
            lat: float = primeiro.get("latitude", 0.0)
            lon: float = primeiro.get("longitude", 0.0)
            nome_cidade = str(primeiro.get("name", cidade_limpa))
            # Remove parênteses como '(Distrito Estadual)'
            if "(" in nome_cidade:
                nome_cidade = nome_cidade.split("(")[0].strip()
            admin1: str = primeiro.get("admin1", "")
            uf_detectada = obter_sigla_uf(admin1, uf) or uf.strip().upper()
            nome_formatado = f"{nome_cidade} - {uf_detectada}" if uf_detectada else nome_cidade
            return lat, lon, nome_formatado

    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001, S110
        pass

    # Fallback: coordenadas da capital da UF informada pelo usuário
    uf_upper = uf.strip().upper()
    nome_fallback = f"{cidade_limpa} - {uf_upper}" if uf_upper else cidade_limpa
    if uf_upper in _COORDS_CAPITAIS:
        lat_cap, lon_cap = _COORDS_CAPITAIS[uf_upper]
        return lat_cap, lon_cap, nome_fallback

    return 0.0, 0.0, nome_fallback


# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 2: Telemetria Climática e Roteamento Rodoviário
# ==============================================================================


def obter_clima(client: httpx.Client, lat: float, lon: float) -> dict[str, str]:
    """Consulta o Open-Meteo Forecast e retorna temperatura (°C), umidade (%) e vento (km/h).

    Caso coordenadas sejam inválidas (0.0, 0.0) ou ocorra timeout (4.0s),
    retorna dicionário de contingência com valores 'N/D'.
    """
    fallback = {
        "temperatura": "N/D",
        "umidade": "N/D",
        "vento": "N/D",
    }

    # Validação rápida de coordenadas zeradas
    if lat == 0.0 and lon == 0.0:
        return fallback

    url = "https://api.open-meteo.com/v1/forecast"
    params: dict[str, str | float] = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
    }

    try:
        resposta = client.get(url, params=params, timeout=4.0)
        resposta.raise_for_status()
        dados = resposta.json()
        current = dados.get("current", {})

        temperatura = current.get("temperature_2m")
        umidade = current.get("relative_humidity_2m")
        vento = current.get("wind_speed_10m")

        if temperatura is None or umidade is None or vento is None:
            return fallback

        return {
            "temperatura": f"{temperatura} °C",
            "umidade": f"{umidade}%",
            "vento": f"{vento} km/h",
        }

    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001
        return fallback


def obter_percurso(
    client: httpx.Client, lat_o: float, lon_o: float, lat_d: float, lon_d: float
) -> dict[str, str]:
    """Consulta o OSRM e calcula distância em km e duração de viagem de carro.

    Em caso de trajetos sem estradas (ex: ilhas) ou timeout (6.0s),
    retorna dicionário com fallback descritivo ('Sem rota direta' / 'Considere voos ou barcos').
    """
    fallback_sem_rota = {
        "distancia": "Sem rota direta",
        "tempo": "Considere voos ou barcos",
        "modal": "outro",
    }

    # Validação de coordenadas nulas
    if (lat_o == 0.0 and lon_o == 0.0) or (lat_d == 0.0 and lon_d == 0.0):
        return fallback_sem_rota

    # OSRM espera coordenadas no formato: {longitude},{latitude};{longitude},{latitude}
    url = f"https://router.project-osrm.org/route/v1/driving/{lon_o},{lat_o};{lon_d},{lat_d}"
    params: dict[str, str] = {"overview": "false"}

    try:
        resposta = client.get(url, params=params, timeout=6.0)
        resposta.raise_for_status()
        dados = resposta.json()

        # Verifica se o OSRM encontrou rota válida
        if dados.get("code") != "Ok":
            return fallback_sem_rota

        routes = dados.get("routes", [])
        if not routes:
            return fallback_sem_rota

        # Verificação defensiva de snap (ilhas/destinos sem malha rodoviária conectada).
        # O OSRM pode 'encaixar' destinos insulares na costa mais próxima. Se o ponto de destino
        # estiver a mais de 10 km (10.000m) da estrada navegável mais próxima, consideramos sem rota direta.
        waypoints = dados.get("waypoints", [])
        if len(waypoints) >= 2:
            dist_snap_destino = waypoints[1].get("distance", 0.0)
            if dist_snap_destino > 10000.0:
                return fallback_sem_rota

        rota = routes[0]
        distancia_metros: float = rota.get("distance", 0.0)
        duracao_segundos: float = rota.get("duration", 0.0)

        # Conversão de unidades: metros para quilômetros com 1 casa decimal
        distancia_km = round(distancia_metros / 1000.0, 1)

        # Conversão de duração: segundos para horas e minutos inteiros
        horas = int(duracao_segundos // 3600)
        minutos = round((duracao_segundos % 3600) / 60.0)

        # Ajuste caso o arredondamento dos minutos resulte em 60
        if minutos == 60:
            horas += 1
            minutos = 0

        if horas > 0:
            tempo_formatado = f"{horas}h {minutos:02d}min de carro"
        else:
            tempo_formatado = f"{minutos}min de carro"

        return {
            "distancia": f"{distancia_km} km",
            "tempo": tempo_formatado,
            "modal": "carro",
        }

    except (httpx.TimeoutException, httpx.HTTPError, Exception):  # noqa: BLE001
        return fallback_sem_rota
