"""Testes do GPX 1.1: XML bem formado, escape de caracteres, estrutura, elevação e roteiros incompletos."""

import xml.etree.ElementTree as ET
from typing import Any

import pytest

from app.services.gpx_service import GPX_NS, gerar_gpx_async

pytestmark = pytest.mark.anyio


def _tag(nome: str) -> str:
    return f"{{{GPX_NS}}}{nome}"


def _roteiro(**extras: Any) -> dict[str, Any]:
    roteiro: dict[str, Any] = {
        "id": "rot_1234",
        "criado_em": "2026-10-29T10:30:00+00:00",
        "origem": {"cidade": "Teresina", "uf": "PI", "latitude": -5.089, "longitude": -42.801},
        "destino": {"cidade": "Brasília", "uf": "DF", "latitude": -15.779, "longitude": -47.929},
        "distancia_km": 1674.6,
        "duracao_minutos": 1298.0,
        "geometria": {
            "type": "LineString",
            "coordinates": [[-42.801, -5.089], [-44.5, -9.0], [-46.0, -12.5], [-47.929, -15.779]],
        },
        "paradas": [
            {"id": "p1", "nome": "Abastecimento estimado (km 410)", "latitude": -8.5, "longitude": -44.2, "distancia_origem_km": 410.0, "estimada": True},
            {"id": "p2", "nome": "Posto Shell", "latitude": -12.0, "longitude": -45.8, "distancia_origem_km": 820.0, "estimada": False},
        ],
        "altimetria": {"ganho_m": 850.0, "perda_m": 220.0, "altitude_maxima_m": 1172.0},
    }
    roteiro.update(extras)
    return roteiro


async def _gerar(roteiro: dict[str, Any]) -> ET.Element:
    return ET.fromstring(await gerar_gpx_async(roteiro))


async def test_gera_gpx_1_1_com_namespace_e_declaracao_xml() -> None:
    xml = await gerar_gpx_async(_roteiro())

    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert '<gpx version="1.1"' in xml
    raiz = ET.fromstring(xml)
    assert raiz.tag == _tag("gpx")
    assert raiz.attrib["version"] == "1.1"
    assert raiz.attrib["creator"]


async def test_contem_waypoints_de_origem_paradas_e_destino_mais_a_trilha() -> None:
    raiz = await _gerar(_roteiro())

    waypoints = raiz.findall(_tag("wpt"))
    assert [w.findtext(_tag("name")) for w in waypoints] == [
        "Origem: Teresina",
        "Abastecimento estimado (km 410)",
        "Posto Shell",
        "Destino: Brasília",
    ]
    assert waypoints[0].attrib == {"lat": "-5.089000", "lon": "-42.801000"}
    assert waypoints[2].findtext(_tag("desc")) == "Parada confirmada no km 820"
    assert "estimada" in waypoints[1].findtext(_tag("desc"))

    pontos = raiz.findall(f"{_tag('trk')}/{_tag('trkseg')}/{_tag('trkpt')}")
    assert len(pontos) == 4
    assert pontos[1].attrib == {"lat": "-9.000000", "lon": "-44.500000"}  # GeoJSON [lon, lat] -> lat/lon do GPX


async def test_ordem_dos_elementos_respeita_o_esquema() -> None:
    raiz = await _gerar(_roteiro())

    nomes = [filho.tag.removeprefix(f"{{{GPX_NS}}}") for filho in raiz]
    assert nomes == ["metadata", "wpt", "wpt", "wpt", "wpt", "trk"]


async def test_metadata_resume_rota_e_relevo_e_define_limites() -> None:
    raiz = await _gerar(_roteiro())
    metadata = raiz.find(_tag("metadata"))
    assert metadata is not None

    assert metadata.findtext(_tag("name")) == "Roteiro Teresina para Brasília"
    descricao = metadata.findtext(_tag("desc")) or ""
    assert "1674.6 km" in descricao and "+850 m / -220 m" in descricao and "altitude máxima 1172 m" in descricao
    assert metadata.findtext(_tag("time")) == "2026-10-29T10:30:00+00:00"
    limites = metadata.find(_tag("bounds"))
    assert limites is not None
    assert limites.attrib == {"minlat": "-15.779000", "minlon": "-47.929000", "maxlat": "-5.089000", "maxlon": "-42.801000"}


async def test_caracteres_especiais_sao_escapados_e_preservados() -> None:
    nome = 'Posto "Três Irmãos" & Cia <24h> \'Centro\''
    roteiro = _roteiro(paradas=[{"nome": nome, "latitude": -8.5, "longitude": -44.2, "estimada": False}])

    xml = await gerar_gpx_async(roteiro)

    assert "&amp;" in xml and "&lt;24h&gt;" in xml
    raiz = ET.fromstring(xml)  # XML bem formado
    assert raiz.findall(_tag("wpt"))[1].findtext(_tag("name")) == nome


async def test_caracteres_de_controle_ilegais_em_xml_sao_removidos() -> None:
    roteiro = _roteiro(paradas=[{"nome": "Posto\x00 com\x0b controle", "latitude": -8.5, "longitude": -44.2}])

    raiz = await _gerar(roteiro)

    assert raiz.findall(_tag("wpt"))[1].findtext(_tag("name")) == "Posto com controle"


async def test_sem_perfil_nao_escreve_elevacao() -> None:
    raiz = await _gerar(_roteiro())
    assert raiz.findall(f".//{_tag('ele')}") == []


async def test_com_perfil_cada_ponto_da_trilha_recebe_elevacao_interpolada() -> None:
    perfil = [
        {"distancia_km": 0.0, "altitude_m": 100.0},
        {"distancia_km": 500.0, "altitude_m": 900.0},
        {"distancia_km": 1000.0, "altitude_m": 500.0},
    ]
    raiz = await _gerar(_roteiro(altimetria={"ganho_m": 800.0, "perda_m": 400.0, "perfil": perfil}))

    elevacoes = [float(p.findtext(_tag("ele"))) for p in raiz.findall(f".//{_tag('trkpt')}")]
    assert len(elevacoes) == 4
    assert elevacoes[0] == 100.0
    assert elevacoes[-1] == 500.0  # a trilha (~1.270 km) passa da última amostra (1.000 km): mantém a altitude final
    assert all(100.0 <= e <= 900.0 for e in elevacoes)
    # origem e destino também levam elevação, e <ele> vem antes de <name> no waypoint
    origem = raiz.findall(_tag("wpt"))[0]
    assert [c.tag.removeprefix(f"{{{GPX_NS}}}") for c in origem][:2] == ["ele", "name"]


async def test_roteiro_incompleto_gera_gpx_valido_apenas_com_metadata() -> None:
    # Formato mínimo que o histórico pode conter (sem coordenadas nem geometria)
    xml = await gerar_gpx_async({"id": "rot_gpx_123", "origem": {"cidade": "A"}, "destino": {"cidade": "B"}})

    assert 'gpx version="1.1"' in xml
    raiz = ET.fromstring(xml)
    assert raiz.findtext(f"{_tag('metadata')}/{_tag('name')}") == "Roteiro A para B"
    assert raiz.findall(_tag("wpt")) == [] and raiz.find(_tag("trk")) is None
    assert raiz.find(f"{_tag('metadata')}/{_tag('bounds')}") is None


async def test_sem_geometria_usa_linha_reta_entre_origem_e_destino() -> None:
    raiz = await _gerar(_roteiro(geometria={"type": "LineString", "coordinates": []}))

    pontos = raiz.findall(f".//{_tag('trkpt')}")
    assert [(p.attrib["lat"], p.attrib["lon"]) for p in pontos] == [("-5.089000", "-42.801000"), ("-15.779000", "-47.929000")]


async def test_coordenadas_zeradas_e_invalidas_sao_ignoradas() -> None:
    roteiro = _roteiro(
        origem={"cidade": "Origem", "uf": "PI", "latitude": 0.0, "longitude": 0.0},  # marcador de "não geocodificado"
        paradas=[{"nome": "Fora do mundo", "latitude": 95.0, "longitude": -44.0}, {"nome": "Sem coordenadas"}],
    )

    raiz = await _gerar(roteiro)

    assert [w.findtext(_tag("name")) for w in raiz.findall(_tag("wpt"))] == ["Destino: Brasília"]


async def test_data_invalida_e_omitida_do_metadata() -> None:
    raiz = await _gerar(_roteiro(criado_em="ontem à tarde"))
    assert raiz.find(f"{_tag('metadata')}/{_tag('time')}") is None
