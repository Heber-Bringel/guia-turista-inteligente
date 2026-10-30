"""Exportação do roteiro em GPX 1.1: waypoints (origem, paradas, destino) e trilha com elevação."""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from itertools import pairwise
from typing import Any

from app.services.geo_utils import distancias_acumuladas_km

GPX_NS = "http://www.topografix.com/GPX/1/1"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
CRIADOR = "Guia do Turista Inteligente"

# Caracteres de controle são ilegais em XML 1.0, mesmo escapados
_CONTROLE_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _texto(valor: Any) -> str:
    return _CONTROLE_XML.sub("", str(valor))


def _coordenada_valida(lat: Any, lon: Any) -> bool:
    """Coordenada numérica dentro dos limites e diferente de (0, 0), que o sistema usa como 'não geocodificado'."""
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= lat_f <= 90 and -180 <= lon_f <= 180 and not (lat_f == 0.0 and lon_f == 0.0)


def _filho(pai: ET.Element, tag: str, texto: Any) -> ET.Element:
    elemento = ET.SubElement(pai, tag)
    elemento.text = _texto(texto)
    return elemento


def _iso_valido(valor: Any) -> str | None:
    """Devolve o instante ISO 8601 se for válido (xsd:dateTime), senão None."""
    if not isinstance(valor, str):
        return None
    try:
        datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return valor


def _elevacao_em(distancia_km: float, perfil: list[dict[str, Any]]) -> float | None:
    """Interpola a altitude (m) à distância dada sobre a polilinha, a partir das amostras do perfil."""
    amostras = [(float(p["distancia_km"]), float(p["altitude_m"])) for p in perfil if "distancia_km" in p and "altitude_m" in p]
    if not amostras:
        return None
    if distancia_km <= amostras[0][0]:
        return amostras[0][1]
    for (d0, a0), (d1, a1) in pairwise(amostras):
        if distancia_km <= d1:
            fracao = (distancia_km - d0) / (d1 - d0) if d1 > d0 else 0.0
            return a0 + (a1 - a0) * fracao
    return amostras[-1][1]


def _waypoint(raiz: ET.Element, lat: Any, lon: Any, nome: str, descricao: str | None, simbolo: str, ele: float | None = None) -> None:
    if not _coordenada_valida(lat, lon):
        return
    wpt = ET.SubElement(raiz, "wpt", {"lat": f"{float(lat):.6f}", "lon": f"{float(lon):.6f}"})
    if ele is not None:
        _filho(wpt, "ele", f"{ele:.1f}")
    _filho(wpt, "name", nome)
    if descricao:
        _filho(wpt, "desc", descricao)
    _filho(wpt, "sym", simbolo)


async def gerar_gpx_async(roteiro: dict[str, Any]) -> str:
    """Gera o XML GPX 1.1 do roteiro (dicionário no formato de `RoteiroResponse`).

    Conteúdo: `metadata` (nome, resumo de distância/relevo, data e limites), um `wpt` para a origem, cada parada
    e o destino, e uma `trk` com a geometria da rota. Se `altimetria.perfil` existir, os pontos recebem `<ele>`.
    Tolera roteiros incompletos: o que não tiver coordenadas válidas é omitido e o arquivo continua válido.
    """
    origem = roteiro.get("origem") or {}
    destino = roteiro.get("destino") or {}
    nome_origem = _texto(origem.get("cidade") or "Origem")
    nome_destino = _texto(destino.get("cidade") or "Destino")
    altimetria = roteiro.get("altimetria") or {}
    perfil = altimetria.get("perfil") or []

    coordenadas = [c for c in (roteiro.get("geometria") or {}).get("coordinates") or [] if len(c) >= 2]
    if not coordenadas and _coordenada_valida(origem.get("latitude"), origem.get("longitude")) and _coordenada_valida(
        destino.get("latitude"), destino.get("longitude")
    ):
        coordenadas = [[origem["longitude"], origem["latitude"]], [destino["longitude"], destino["latitude"]]]
    coordenadas = [c for c in coordenadas if _coordenada_valida(c[1], c[0])]

    acumuladas = distancias_acumuladas_km(coordenadas) if len(coordenadas) >= 2 else [0.0] * len(coordenadas)
    distancia_viaria = float(roteiro.get("distancia_km") or 0.0)
    # Perfil e trilha são medidos sobre a polilinha; a distância das paradas é viária, então converte pela escala
    escala = (acumuladas[-1] / distancia_viaria) if distancia_viaria > 0 and acumuladas and acumuladas[-1] > 0 else 1.0

    raiz = ET.Element(
        "gpx",
        {
            "version": "1.1",
            "creator": CRIADOR,
            "xmlns": GPX_NS,
            "xmlns:xsi": XSI_NS,
            "xsi:schemaLocation": f"{GPX_NS} http://www.topografix.com/GPX/1/1/gpx.xsd",
        },
    )

    # Ordem exigida pelo esquema: metadata, wpt*, rte*, trk*
    resumo = []
    if distancia_viaria:
        resumo.append(f"{distancia_viaria:g} km")
    if roteiro.get("duracao_minutos"):
        resumo.append(f"{float(roteiro['duracao_minutos']) / 60:.1f} h")
    if altimetria.get("ganho_m") is not None and altimetria.get("perda_m") is not None:
        resumo.append(f"+{altimetria['ganho_m']:g} m / -{altimetria['perda_m']:g} m de relevo")
    if altimetria.get("altitude_maxima_m") is not None:
        resumo.append(f"altitude máxima {altimetria['altitude_maxima_m']:g} m")

    metadata = ET.SubElement(raiz, "metadata")
    _filho(metadata, "name", f"Roteiro {nome_origem} para {nome_destino}")
    if resumo:
        _filho(metadata, "desc", " · ".join(resumo))
    instante = _iso_valido(roteiro.get("criado_em"))
    if instante:
        _filho(metadata, "time", instante)
    if coordenadas:
        ET.SubElement(
            metadata,
            "bounds",
            {
                "minlat": f"{min(c[1] for c in coordenadas):.6f}",
                "minlon": f"{min(c[0] for c in coordenadas):.6f}",
                "maxlat": f"{max(c[1] for c in coordenadas):.6f}",
                "maxlon": f"{max(c[0] for c in coordenadas):.6f}",
            },
        )

    total = acumuladas[-1] if acumuladas else 0.0
    _waypoint(raiz, origem.get("latitude"), origem.get("longitude"), f"Origem: {nome_origem}", origem.get("uf"), "Flag, Green", _elevacao_em(0.0, perfil))
    for i, parada in enumerate(roteiro.get("paradas") or [], start=1):
        km = parada.get("distancia_origem_km")
        ele = _elevacao_em(float(km) * escala, perfil) if km is not None else None
        tipo = "estimada" if parada.get("estimada", True) else "confirmada"
        detalhe = f"Parada {tipo}" + (f" no km {km:g}" if km is not None else "")
        _waypoint(raiz, parada.get("latitude"), parada.get("longitude"), parada.get("nome") or f"Parada {i}", detalhe, "Gas Station", ele)
    _waypoint(raiz, destino.get("latitude"), destino.get("longitude"), f"Destino: {nome_destino}", destino.get("uf"), "Flag, Red", _elevacao_em(total, perfil))

    if coordenadas:
        trk = ET.SubElement(raiz, "trk")
        _filho(trk, "name", f"Trajeto {nome_origem} - {nome_destino}")
        segmento = ET.SubElement(trk, "trkseg")
        for (lon, lat, *_), km in zip(coordenadas, acumuladas):
            ponto = ET.SubElement(segmento, "trkpt", {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})
            ele = _elevacao_em(km, perfil)
            if ele is not None:
                _filho(ponto, "ele", f"{ele:.1f}")

    ET.indent(raiz, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(raiz, encoding="unicode")
