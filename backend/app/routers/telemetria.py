"""Rotas de telemetria operacional: métricas JSON e exportador Prometheus em /metrics."""

import time
from typing import Any
from fastapi import APIRouter, BackgroundTasks, Response
from app.core.circuit_breaker import CIRCUIT_BREAKERS
from app.core.logging_config import logger
from app.routers.roteiros import METRICAS_OPERACIONAIS, REQUISICOES_ATIVAS

router = APIRouter(tags=["Telemetria"])


@router.get(
    "/telemetria",
    summary="Métricas operacionais consolidadas e estado dos Circuit Breakers",
)
async def obter_telemetria(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Retorna as métricas operacionais em JSON: latências recentes, total de roteiros e disjuntores."""
    estado_disjuntores = {nome: cb.get_state() for nome, cb in CIRCUIT_BREAKERS.items()}

    def _auditar_background() -> None:
        logger.debug(
            "Auditoria de telemetria executada. Roteiros acumulados: %d",
            METRICAS_OPERACIONAIS["total_roteiros"],
        )

    background_tasks.add_task(_auditar_background)

    latencias = METRICAS_OPERACIONAIS.get("latencias_recentes_ms", [])
    media_latencia = round(sum(latencias) / len(latencias), 2) if latencias else 0.0

    return {
        "status": "online",
        "timestamp_unix": int(time.time()),
        "total_roteiros_calculados": METRICAS_OPERACIONAIS.get("total_roteiros", 0),
        "requisicoes_em_andamento": len(REQUISICOES_ATIVAS),
        "latencia_media_ms": media_latencia,
        "ultimas_latencias_ms": latencias[-10:],
        "circuit_breakers": estado_disjuntores,
    }


@router.get(
    "/metrics",
    summary="Exportador de métricas no formato padrão Prometheus",
    response_class=Response,
)
async def exportar_metricas_prometheus() -> Response:
    """Gera saída em texto plano compatível com raspagem (scrape) do Prometheus."""
    total_roteiros = METRICAS_OPERACIONAIS.get("total_roteiros", 0)
    requisicoes_ativas = len(REQUISICOES_ATIVAS)
    latencias = METRICAS_OPERACIONAIS.get("latencias_recentes_ms", [])
    latencia_media = (sum(latencias) / len(latencias)) if latencias else 0.0

    linhas: list[str] = [
        "# HELP guia_turista_roteiros_total Total acumulado de roteiros planejados",
        "# TYPE guia_turista_roteiros_total counter",
        f"guia_turista_roteiros_total {total_roteiros}",
        "",
        "# HELP guia_turista_requisicoes_ativas Quantidade de requisições sendo processadas no momento",
        "# TYPE guia_turista_requisicoes_ativas gauge",
        f"guia_turista_requisicoes_ativas {requisicoes_ativas}",
        "",
        "# HELP guia_turista_latencia_media_ms Latência média das requisições recentes em milissegundos",
        "# TYPE guia_turista_latencia_media_ms gauge",
        f"guia_turista_latencia_media_ms {latencia_media:.2f}",
        "",
        "# HELP guia_turista_circuit_breaker_status Estado do circuit breaker (1=closed/normal, 2=half_open, 0=open)",
        "# TYPE guia_turista_circuit_breaker_status gauge",
    ]

    for nome, cb in CIRCUIT_BREAKERS.items():
        val = 1 if cb.state.value == "closed" else (2 if cb.state.value == "half_open" else 0)
        linhas.append(f'guia_turista_circuit_breaker_status{{provedor="{nome}"}} {val}')

    conteudo = "\n".join(linhas) + "\n"
    return Response(content=conteudo, media_type="text/plain; version=0.0.4; charset=utf-8")

