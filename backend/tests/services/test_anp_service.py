"""Testes do ranqueamento regulatório ANP: fórmula, tempo de autorização e cruzamento OSM x catálogo."""

from datetime import date

import pytest

from app.services.anp_service import (
    CATALOGO_ANP,
    calcular_anos_autorizacao,
    calcular_ranking_score,
    ranquear_postos,
)

HOJE = date(2026, 11, 27)
# Centro de Piripiri - PI, às margens da BR-343
PIRIPIRI = (-4.2733, -41.7769)
RAIO_KM = 10.0


@pytest.mark.parametrize(
    ("data", "anos"),
    [("2006-03-14", 20), ("2015-11-27", 11), ("2015-11-28", 10), ("2026-01-01", 0), ("2030-01-01", 0)],
)
def test_anos_de_autorizacao_contam_apenas_anos_completos(data: str, anos: int) -> None:
    assert calcular_anos_autorizacao(data, HOJE) == anos


@pytest.mark.parametrize("data", [None, "", "14/03/2006"])
def test_data_de_autorizacao_ausente_ou_invalida(data: str | None) -> None:
    assert calcular_anos_autorizacao(data, HOJE) is None


def test_formula_do_ranking_nos_extremos() -> None:
    assert calcular_ranking_score(5.0, 20, 0.0, RAIO_KM) == 10.0
    assert calcular_ranking_score(0.0, 0, RAIO_KM, RAIO_KM) == 0.0
    # 0,45 * 4/5 + 0,35 * 10/20 + 0,20 * (1 - 5/10) = 0,36 + 0,175 + 0,10 = 0,635
    assert calcular_ranking_score(4.0, 10, 5.0, RAIO_KM) == pytest.approx(6.35, abs=0.05)
    # 0,45 * 3/5 + 0,35 * 4/20 + 0,20 * (1 - 2/10) = 0,27 + 0,07 + 0,16 = 0,50
    assert calcular_ranking_score(3.0, 4, 2.0, RAIO_KM) == 5.0


def test_ranking_limita_os_valores_e_usa_nota_neutra_sem_avaliacao() -> None:
    assert calcular_ranking_score(9.0, 40, 0.0, RAIO_KM) == calcular_ranking_score(5.0, 20, 0.0, RAIO_KM)
    assert calcular_ranking_score(None, 0, 0.0, RAIO_KM) == calcular_ranking_score(3.0, 0, 0.0, RAIO_KM)
    assert calcular_ranking_score(4.0, 10, 50.0, RAIO_KM) == calcular_ranking_score(4.0, 10, RAIO_KM, RAIO_KM)


def test_br343_piripiri_ranqueia_os_postos_do_catalogo_anp() -> None:
    postos = ranquear_postos(*PIRIPIRI, RAIO_KM, elementos_osm=None, hoje=HOJE)

    assert [p["municipio"] for p in postos] == ["Piripiri"] * 3
    assert all(p["rodovia"] == "BR-343" and p["uf"] == "PI" for p in postos)
    scores = [p["ranking_score"] for p in postos]
    assert scores == sorted(scores, reverse=True)

    melhor = postos[0]
    assert melhor["cnpj"] == "00.343.001/0001-10"
    assert melhor["razao_social"] == "Auto Posto Portal de Sete Cidades Ltda"
    assert melhor["avaliacao"] == 4.7
    assert melhor["tempo_autorizacao_anp"] == 20
    assert "Diesel S10" in melhor["combustiveis"]
    assert melhor["distancia_km"] < 2


def test_posto_do_osm_herda_dados_anp_pela_posicao() -> None:
    registro = CATALOGO_ANP[1]
    elemento = {"lat": registro["latitude"] + 0.0005, "lon": registro["longitude"], "tags": {"name": "Posto Caldeirão BR"}}

    postos = ranquear_postos(*PIRIPIRI, RAIO_KM, elementos_osm=[elemento], hoje=HOJE)
    caldeirao = next(p for p in postos if p["cnpj"] == registro["cnpj"])

    assert caldeirao["nome"] == "Posto Caldeirão BR"  # nome do mapa
    assert caldeirao["latitude"] == elemento["lat"]  # posição real do mapa
    assert caldeirao["razao_social"] == registro["razao_social"]  # dado regulatório da ANP
    assert caldeirao["fonte"] == "osm+anp"
    assert sum(1 for p in postos if p["cnpj"] == registro["cnpj"]) == 1  # sem duplicar o registro


def test_posto_do_osm_herda_dados_anp_pelo_cnpj() -> None:
    registro = CATALOGO_ANP[2]
    elemento = {"lat": -4.30, "lon": -41.75, "tags": {"name": "Posto X", "ref:vatin": "00343003000130"}}

    postos = ranquear_postos(*PIRIPIRI, RAIO_KM, elementos_osm=[elemento], hoje=HOJE)
    assert next(p for p in postos if p["nome"] == "Posto X")["razao_social"] == registro["razao_social"]


def test_posto_sem_registro_anp_usa_tags_do_osm_e_perde_posicoes() -> None:
    elemento = {
        "lat": PIRIPIRI[0],
        "lon": PIRIPIRI[1],
        "tags": {"name": "Posto Sem Registro", "operator": "Fulano Combustíveis", "fuel:diesel": "yes", "fuel:ethanol": "yes"},
    }

    postos = ranquear_postos(*PIRIPIRI, RAIO_KM, elementos_osm=[elemento], hoje=HOJE)
    sem_registro = next(p for p in postos if p["nome"] == "Posto Sem Registro")

    assert sem_registro["tempo_autorizacao_anp"] is None
    assert sem_registro["combustiveis"] == ["Etanol", "Diesel"]
    assert sem_registro["razao_social"] == "Fulano Combustíveis"
    # Mesmo exatamente sobre o ponto, fica atrás do posto ANP bem avaliado e autorizado há 20 anos
    assert postos[0]["cnpj"] == "00.343.001/0001-10"


def test_longe_do_catalogo_e_sem_osm_nao_ha_postos() -> None:
    assert ranquear_postos(-15.78, -47.93, RAIO_KM, elementos_osm=None, hoje=HOJE) == []


def test_catalogo_vazio_considera_apenas_o_osm() -> None:
    elemento = {"lat": PIRIPIRI[0], "lon": PIRIPIRI[1], "tags": {}}
    postos = ranquear_postos(*PIRIPIRI, RAIO_KM, elementos_osm=[elemento], catalogo=(), nome_generico="Eletroposto")
    assert [p["nome"] for p in postos] == ["Eletroposto"]
