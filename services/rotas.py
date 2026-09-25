"""Serviço de roteamento rodoviário (OSRM): distância em km e duração de viagem de carro."""

import httpx


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
