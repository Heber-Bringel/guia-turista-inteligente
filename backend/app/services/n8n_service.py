"""Serviço de integração EDA com n8n: despacho assíncrono em BackgroundTasks para DLQ, Multicanal e Clima."""

import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import BackgroundTasks

from app.core.config import settings
from app.core.logging_config import get_correlation_id, logger

# Histórico em memória dos últimos incidentes e despachos (útil para auditoria em ChatOps e testes)
HISTORICO_EVENTOS_N8N: list[dict[str, Any]] = []


def _registrar_evento_memoria(tipo: str, payload: dict[str, Any], status_envio: str) -> None:
    """Mantém registro em memória dos últimos 50 eventos despachados para o n8n."""
    HISTORICO_EVENTOS_N8N.append(
        {
            "tipo": tipo,
            "trace_id": payload.get("trace_id") or payload.get("protocolo"),
            "status_envio": status_envio,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
    )
    if len(HISTORICO_EVENTOS_N8N) > 50:
        HISTORICO_EVENTOS_N8N.pop(0)


def montar_payload_dlq(
    rota: str,
    servico: str,
    erro: Exception | str,
    stack_trace: str | None = None,
    trace_id: str | None = None,
    contexto: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constrói o payload estruturado de incidente para a Dead Letter Queue (turismo-dlq)."""
    uid = trace_id or str(uuid.uuid4())
    if stack_trace is None:
        if isinstance(erro, BaseException) and erro.__traceback__ is not None:
            stack_trace = "".join(traceback.format_exception(type(erro), erro, erro.__traceback__))
        else:
            tb_atual = traceback.format_exc()
            stack_trace = (
                tb_atual
                if tb_atual and "NoneType: None" not in tb_atual
                else f"{type(erro).__name__ if isinstance(erro, BaseException) else 'RuntimeError'}: {erro}"
            )

    return {
        "evento": "incidente_dlq",
        "trace_id": uid,
        "correlation_id": get_correlation_id(),
        "aplicacao": settings.APP_NAME,
        "versao": settings.APP_VERSION,
        "rota": rota,
        "servico": servico,
        "erro": str(erro),
        "tipo_erro": type(erro).__name__ if isinstance(erro, BaseException) else "ErroAplicacao",
        "stack_trace": stack_trace.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "contexto": contexto or {},
    }


async def despachar_evento_dlq(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> bool:
    """Envia assincronamente um incidente para o webhook turismo-dlq do n8n (executado em BackgroundTasks)."""
    url = settings.obter_url_webhook(settings.N8N_WEBHOOK_DLQ)
    trace_id = payload.get("trace_id", "-")
    logger.info(
        "[BackgroundTasks][DLQ] Iniciando envio de incidente trace_id=%s servico=%s para %s",
        trace_id,
        payload.get("servico"),
        url,
    )
    try:
        resposta = await client.post(url, json=payload, timeout=settings.TIMEOUT_N8N)
        resposta.raise_for_status()
        logger.info(
            "[BackgroundTasks][DLQ] Incidente trace_id=%s entregue ao n8n com sucesso (HTTP %s).",
            trace_id,
            resposta.status_code,
        )
        _registrar_evento_memoria("turismo-dlq", payload, f"entregue_http_{resposta.status_code}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[BackgroundTasks][DLQ] Webhook n8n indisponível para trace_id=%s (%s: %s). Incidente retido em log local.",
            trace_id,
            type(exc).__name__,
            exc,
        )
        _registrar_evento_memoria("turismo-dlq", payload, f"retido_local_{type(exc).__name__}")
        return False


def agendar_dlq_background(
    background_tasks: BackgroundTasks,
    client: httpx.AsyncClient,
    rota: str,
    servico: str,
    erro: Exception | str,
    stack_trace: str | None = None,
    trace_id: str | None = None,
    contexto: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gera o UUID de rastreio, loga o agendamento e adiciona o envio da DLQ na fila de BackgroundTasks."""
    payload = montar_payload_dlq(
        rota=rota,
        servico=servico,
        erro=erro,
        stack_trace=stack_trace,
        trace_id=trace_id,
        contexto=contexto,
    )
    logger.info(
        "[BackgroundTasks][DLQ] Tarefa agendada em segundo plano: trace_id=%s | rota=%s | servico=%s",
        payload["trace_id"],
        rota,
        servico,
    )
    background_tasks.add_task(despachar_evento_dlq, client, payload)
    return payload


async def despachar_roteiro_multicanal(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> bool:
    """Envia assincronamente o roteiro personalizado para o webhook turismo-despachar-roteiro (E-mail/WhatsApp)."""
    url = settings.obter_url_webhook(settings.N8N_WEBHOOK_DESPACHAR_ROTEIRO)
    protocolo = payload.get("protocolo", "-")
    canal = payload.get("canal", "-")
    destinatario = payload.get("destinatario", "-")

    logger.info(
        "[BackgroundTasks][Despacho] Iniciando despacho multicanal protocolo=%s canal=%s destinatario=%s para %s",
        protocolo,
        canal,
        destinatario,
        url,
    )
    try:
        resposta = await client.post(url, json=payload, timeout=settings.TIMEOUT_N8N)
        resposta.raise_for_status()
        logger.info(
            "[BackgroundTasks][Despacho] Roteiro protocolo=%s despachado via n8n (%s) com sucesso (HTTP %s).",
            protocolo,
            canal,
            resposta.status_code,
        )
        _registrar_evento_memoria("turismo-despachar-roteiro", payload, f"entregue_http_{resposta.status_code}")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[BackgroundTasks][Despacho] Falha ao acionar webhook n8n para protocolo=%s (%s: %s).",
            protocolo,
            type(exc).__name__,
            exc,
        )
        _registrar_evento_memoria("turismo-despachar-roteiro", payload, f"retido_local_{type(exc).__name__}")
        return False


def agendar_despacho_roteiro_background(
    background_tasks: BackgroundTasks,
    client: httpx.AsyncClient,
    canal: str,
    destinatario: str,
    roteiro: dict[str, Any],
    idioma: str = "pt",
    nome_viajante: str | None = None,
    resumo_guia: str | None = None,
    protocolo: str | None = None,
) -> dict[str, Any]:
    """Agenda o envio do roteiro por E-mail ou WhatsApp em BackgroundTasks para o webhook do n8n."""
    prot = protocolo or f"dsp_{uuid.uuid4().hex[:10]}"
    payload = {
        "evento": "despachar_roteiro",
        "protocolo": prot,
        "canal": canal,
        "destinatario": destinatario,
        "nome_viajante": nome_viajante or "Viajante",
        "idioma": idioma,
        "resumo_guia": resumo_guia or roteiro.get("guia") or "",
        "roteiro": roteiro,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(
        "[BackgroundTasks][Despacho] Tarefa agendada em segundo plano: protocolo=%s | canal=%s | destinatario=%s",
        prot,
        canal,
        destinatario,
    )
    background_tasks.add_task(despachar_roteiro_multicanal, client, payload)
    return payload


async def despachar_evento_clima_n8n(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    """Aciona o webhook do Workflow 4 (Clima Open-Meteo + Orientações Gemini no n8n)."""
    url = settings.obter_url_webhook(settings.N8N_WEBHOOK_CLIMA)
    logger.info(
        "[BackgroundTasks][Clima] Acionando workflow climático n8n para destino=%s em %s",
        payload.get("destino"),
        url,
    )
    try:
        resposta = await client.post(url, json=payload, timeout=settings.TIMEOUT_N8N)
        resposta.raise_for_status()
        dados = resposta.json() if resposta.content else {"status": "ok"}
        _registrar_evento_memoria("turismo-clima", payload, f"entregue_http_{resposta.status_code}")
        return dados if isinstance(dados, dict) else {"resultado": dados}
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[BackgroundTasks][Clima] Webhook de clima n8n indisponível (%s: %s).",
            type(exc).__name__,
            exc,
        )
        _registrar_evento_memoria("turismo-clima", payload, f"retido_local_{type(exc).__name__}")
        return None
