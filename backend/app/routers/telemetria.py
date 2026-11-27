"""Rotas de telemetria operacional, suporte ChatOps (protegidos por X-Support-Key) e Prometheus."""

import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.core.circuit_breaker import CIRCUIT_BREAKERS
from app.core.config import settings
from app.core.dependencies import obter_http_client, validar_support_key
from app.core.logging_config import logger
from app.routers.roteiros import METRICAS_OPERACIONAIS, REQUISICOES_ATIVAS
from app.services.n8n_service import HISTORICO_EVENTOS_N8N, agendar_dlq_background

router = APIRouter(tags=["Telemetria & Suporte ChatOps"])

# Marca de inicialização global como fallback caso o lifespan ainda não tenha registrado started_at
_BOOT_TIMESTAMP = time.time()


def _formatar_duracao_humana(segundos_totais: float) -> str:
    """Converte segundos em formato legível 'Xd Yh Zm Ws' para respostas do ChatOps Telegram."""
    seg = max(0, int(segundos_totais))
    dias, resto = divmod(seg, 86400)
    horas, resto = divmod(resto, 3600)
    minutos, segundos = divmod(resto, 60)
    partes: list[str] = []
    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0 or dias > 0:
        partes.append(f"{horas}h")
    if minutos > 0 or horas > 0 or dias > 0:
        partes.append(f"{minutos}m")
    partes.append(f"{segundos}s")
    return " ".join(partes)


def _obter_uptime_segundos(request: Request) -> float:
    """Calcula o uptime real desde o início do lifespan em app.state.started_at."""
    inicio = getattr(request.app.state, "started_at", _BOOT_TIMESTAMP)
    return max(0.0, time.time() - float(inicio))


# =============================================================================
# 1. /status e /suporte/status (Protegido por X-Support-Key)
# =============================================================================

@router.get(
    "/status",
    summary="Status operacional do sistema para ChatOps Telegram (protegido por X-Support-Key)",
)
@router.get(
    "/suporte/status",
    summary="Status operacional do sistema para ChatOps Telegram (protegido por X-Support-Key)",
)
async def obter_status_suporte(
    request: Request,
    _support_key: Annotated[str, Depends(validar_support_key)],
) -> dict[str, Any]:
    """Retorna o diagnóstico geral do microsserviço FastAPI V3 e estado dos disjuntores."""
    uptime_s = _obter_uptime_segundos(request)
    estado_disjuntores = {nome: cb.get_state() for nome, cb in CIRCUIT_BREAKERS.items()}
    http_client_ativo = (
        hasattr(request.app.state, "http_client")
        and isinstance(request.app.state.http_client, httpx.AsyncClient)
        and not request.app.state.http_client.is_closed
    )
    return {
        "comando": "/status",
        "status": "online",
        "aplicacao": settings.APP_NAME,
        "versao": settings.APP_VERSION,
        "arquitetura": "EDA FastAPI + n8n + BackgroundTasks",
        "http_pool_ativo": http_client_ativo,
        "uptime_segundos": round(uptime_s, 2),
        "uptime_humano": _formatar_duracao_humana(uptime_s),
        "n8n_webhooks": {
            "dlq": settings.obter_url_webhook(settings.N8N_WEBHOOK_DLQ),
            "despachar_roteiro": settings.obter_url_webhook(settings.N8N_WEBHOOK_DESPACHAR_ROTEIRO),
            "clima": settings.obter_url_webhook(settings.N8N_WEBHOOK_CLIMA),
        },
        "circuit_breakers": estado_disjuntores,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# 2. /uptime e /suporte/uptime (Protegido por X-Support-Key)
# =============================================================================

@router.get(
    "/uptime",
    summary="Tempo de atividade contínuo do servidor (protegido por X-Support-Key)",
)
@router.get(
    "/suporte/uptime",
    summary="Tempo de atividade contínuo do servidor (protegido por X-Support-Key)",
)
async def obter_uptime_suporte(
    request: Request,
    _support_key: Annotated[str, Depends(validar_support_key)],
) -> dict[str, Any]:
    """Retorna o tempo de atividade (uptime) exato desde a inicialização da aplicação."""
    inicio = getattr(request.app.state, "started_at", _BOOT_TIMESTAMP)
    uptime_s = _obter_uptime_segundos(request)
    iniciado_em_iso = datetime.fromtimestamp(float(inicio), tz=timezone.utc).isoformat()
    return {
        "comando": "/uptime",
        "status": "online",
        "iniciado_em": iniciado_em_iso,
        "uptime_segundos": round(uptime_s, 2),
        "uptime_formatado": _formatar_duracao_humana(uptime_s),
        "versao": settings.APP_VERSION,
    }


# =============================================================================
# 3. /telemetria e /suporte/telemetria (Protegido por X-Support-Key)
# =============================================================================

@router.get(
    "/telemetria",
    summary="Métricas operacionais consolidadas e Circuit Breakers (protegido por X-Support-Key)",
)
@router.get(
    "/suporte/telemetria",
    summary="Métricas operacionais consolidadas e Circuit Breakers (protegido por X-Support-Key)",
)
async def obter_telemetria(
    background_tasks: BackgroundTasks,
    _support_key: Annotated[str, Depends(validar_support_key)],
) -> dict[str, Any]:
    """Retorna as métricas operacionais em JSON restritas à equipe de suporte via X-Support-Key."""
    estado_disjuntores = {nome: cb.get_state() for nome, cb in CIRCUIT_BREAKERS.items()}

    def _auditar_background() -> None:
        logger.info(
            "[BackgroundTasks][Telemetria] Auditoria de telemetria consultada via ChatOps. Roteiros acumulados: %d",
            METRICAS_OPERACIONAIS["total_roteiros"],
        )

    background_tasks.add_task(_auditar_background)

    latencias = METRICAS_OPERACIONAIS.get("latencias_recentes_ms", [])
    media_latencia = round(sum(latencias) / len(latencias), 2) if latencias else 0.0

    return {
        "comando": "/telemetria",
        "status": "online",
        "timestamp_unix": int(time.time()),
        "total_roteiros_calculados": METRICAS_OPERACIONAIS.get("total_roteiros", 0),
        "requisicoes_em_andamento": len(REQUISICOES_ATIVAS),
        "latencia_media_ms": media_latencia,
        "ultimas_latencias_ms": latencias[-10:],
        "eventos_n8n_recentes": len(HISTORICO_EVENTOS_N8N),
        "circuit_breakers": estado_disjuntores,
    }


# =============================================================================
# 4. /testardlq e /suporte/testardlq (Protegido por X-Support-Key)
# =============================================================================

@router.get(
    "/testardlq",
    summary="Simula falha controlada e dispara incidente real para a DLQ via BackgroundTasks",
)
@router.post(
    "/testardlq",
    summary="Simula falha controlada e dispara incidente real para a DLQ via BackgroundTasks",
)
@router.get(
    "/suporte/testardlq",
    summary="Simula falha controlada e dispara incidente real para a DLQ via BackgroundTasks",
)
@router.post(
    "/suporte/testardlq",
    summary="Simula falha controlada e dispara incidente real para a DLQ via BackgroundTasks",
)
async def testar_dlq_suporte(
    request: Request,
    background_tasks: BackgroundTasks,
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
    _support_key: Annotated[str, Depends(validar_support_key)],
) -> dict[str, Any]:
    """Simula uma exceção controlada de integração externa e agenda envio para turismo-dlq em BackgroundTasks.

    Não expõe stack trace na resposta HTTP; o stack trace completo e o UUID de rastreio vão em segundo plano
    para o webhook turismo-dlq do n8n (Workflow 1 -> Alerta Markdown no Telegram).
    """
    trace_id = str(uuid.uuid4())
    try:
        raise RuntimeError(
            "Falha simulada pelo comando ChatOps /testardlq: Timeout no provedor externo durante orquestração EDA."
        )
    except RuntimeError as exc:
        stack_capturado = traceback.format_exc()
        incidente = agendar_dlq_background(
            background_tasks=background_tasks,
            client=client,
            rota=str(request.url.path),
            servico="chatops_testardlq",
            erro=exc,
            stack_trace=stack_capturado,
            trace_id=trace_id,
            contexto={"origem": "ChatOps Telegram /testardlq", "metodo": request.method},
        )

    return {
        "comando": "/testardlq",
        "status": "incidente_agendado_dlq",
        "trace_id": incidente["trace_id"],
        "webhook_destino": settings.obter_url_webhook(settings.N8N_WEBHOOK_DLQ),
        "execucao": "BackgroundTasks",
        "mensagem": (
            f"Incidente de teste gerado e agendado em BackgroundTasks para a DLQ (UUID: {incidente['trace_id']})."
        ),
        "timestamp": incidente["timestamp"],
    }


# =============================================================================
# 5. Exportador Prometheus (/metrics)
# =============================================================================

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
