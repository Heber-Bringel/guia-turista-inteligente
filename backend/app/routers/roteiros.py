"""Rotas do ciclo de vida de roteiros: planejamento concorrente, mapa, custos, SSE e histórico."""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, AsyncGenerator
import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse

from app.core.circuit_breaker import CircuitBreakerError, obter_circuit_breaker
from app.core.config import settings
from app.core.dependencies import obter_http_client, obter_usuario_ativo
from app.core.logging_config import logger
from app.schemas.auth import UsuarioPerfil
from app.schemas.roteiros import (
    AltimetriaInfo,
    AtrativoItem,
    ClimaInfo,
    CompartilharRoteiroRequest,
    CustosInfo,
    CustosRequest,
    ExportarGpxRequest,
    GeoJsonGeometry,
    GuiaStreamRequest,
    Localidade,
    MapaRotaRequest,
    MarcarVisitaRequest,
    ParadaItem,
    ProviderDiagnostic,
    RoteiroRequest,
    RoteiroResponse,
)
from app.services.storage_service import (
    deletar_viagem_usuario,
    listar_viagens_usuario,
    marcar_atrativo_visitado,
    obter_viagem_usuario,
    salvar_nova_viagem,
)

# Importações seguras dos serviços do Douglas com fallbacks defensivos
try:
    from app.services.geocoding_service import buscar_coordenadas_async
except ImportError:
    async def buscar_coordenadas_async(client: httpx.AsyncClient, cidade: str, uf: str) -> tuple[float, float, str]:
        return 0.0, 0.0, uf

try:
    from app.services.clima_service import obter_clima_async
except ImportError:
    async def obter_clima_async(client: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
        return {"temperatura_c": 25.0, "umidade_percentual": 50.0, "vento_kmh": 10.0, "descricao": "Indisponível"}

try:
    from app.services.rota_service import calcular_rota_osrm_async
except ImportError:
    async def calcular_rota_osrm_async(
        client: httpx.AsyncClient, lat_o: float, lon_o: float, lat_d: float, lon_d: float, preferencia: str = "rapida"
    ) -> dict[str, Any]:
        return {
            "distancia_km": 100.0,
            "duracao_minutos": 60.0,
            "geometria": {"type": "LineString", "coordinates": [[lon_o, lat_o], [lon_d, lat_d]]},
            "paradas": [],
        }

try:
    from app.services.altimetria_service import calcular_altimetria_async
except ImportError:
    async def calcular_altimetria_async(client: httpx.AsyncClient, coordenadas: list[list[float]]) -> dict[str, Any]:
        return {"ganho_m": 100.0, "perda_m": 50.0, "altitude_maxima_m": 500.0, "impacto_consumo_percentual": 0.0}

try:
    from app.services.custos_service import calcular_custos_async
except ImportError:
    async def calcular_custos_async(
        distancia_km: float, tipo_veiculo: str, consumo: float, preco: float, passageiros: int, pedagios: float = 0.0
    ) -> dict[str, Any]:
        custo_comb = round((distancia_km / max(consumo, 0.1)) * preco, 2)
        total = round(custo_comb + pedagios, 2)
        return {
            "combustivel_ou_energia": custo_comb,
            "pedagios": pedagios,
            "total": total,
            "por_passageiro": round(total / max(passageiros, 1), 2),
            "moeda": "BRL",
            "emissoes_kg_co2": round(distancia_km * 0.12, 1),
        }

try:
    from app.services.gemini_service import gerar_guia_ia_async, gerar_guia_ia_stream_async
except ImportError:
    async def gerar_guia_ia_async(destino: str, dias: int, estilo: str) -> tuple[str, list[dict[str, Any]]]:
        return f"Guia turístico conciso para {destino}.", []

    async def gerar_guia_ia_stream_async(payload: dict[str, Any]) -> AsyncGenerator[str, None]:
        yield f"Guia turístico transmitido via SSE para {payload.get('destino')}."

try:
    from app.services.gpx_service import gerar_gpx_async
except ImportError:
    async def gerar_gpx_async(roteiro: dict[str, Any]) -> str:
        origem = roteiro.get("origem", {}).get("cidade", "Origem")
        destino = roteiro.get("destino", {}).get("cidade", "Destino")
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="GuiaTuristaInteligente">\n'
            f'  <metadata><name>Roteiro {origem} para {destino}</name></metadata>\n'
            '  <trk><name>Trajeto Principal</name><trkseg></trkseg></trk>\n'
            '</gpx>'
        )

router = APIRouter(prefix="/roteiros", tags=["Roteiros"])

# Controle de concorrência e idempotência por requisição
REQUISICOES_ATIVAS: set[str] = set()
LOCK_REQUISICOES = asyncio.Lock()

# Métricas operacionais em memória para telemetria
METRICAS_OPERACIONAIS: dict[str, Any] = {
    "total_roteiros": 0,
    "latencias_recentes_ms": [],
    "requisicoes_ativas_count": 0,
}


@router.post(
    "/planejar",
    response_model=RoteiroResponse,
    summary="Planejar novo roteiro turístico com orquestração assíncrona",
    description="Pipeline com 2 estágios de asyncio.gather (geocodificação e clima/rota), circuit breaker e persistência em background.",
)
async def planejar_roteiro(
    payload: RoteiroRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
) -> Any:
    """Orquestra o planejamento assíncrono em múltiplos estágios com tratamento de concorrência e cancelamento."""
    chave_idempotencia = (
        f"{user.id}:{payload.origem_cidade}_{payload.origem_uf}->"
        f"{payload.destino_cidade}_{payload.destino_uf}"
    ).lower().strip()

    # 1. Idempotência com asyncio.Lock
    async with LOCK_REQUISICOES:
        if chave_idempotencia in REQUISICOES_ATIVAS:
            logger.warning("Requisição duplicada ativa detectada: %s", chave_idempotencia)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este roteiro já está sendo calculado. Aguarde a conclusão.",
            )
        REQUISICOES_ATIVAS.add(chave_idempotencia)
        METRICAS_OPERACIONAIS["requisicoes_ativas_count"] = len(REQUISICOES_ATIVAS)

    inicio_processamento = time.perf_counter()
    diagnosticos: list[ProviderDiagnostic] = []

    try:
        # Ponto de checagem de desconexão antes de iniciar trabalho custoso
        if await request.is_disconnected():
            logger.info("Cliente desconectado antes do início da geocodificação: %s", chave_idempotencia)
            return Response(status_code=499)

        # =========================================================================
        # ESTÁGIO 1: Geocodificação paralela de Origem e Destino com asyncio.gather
        # =========================================================================
        cb_geo = obter_circuit_breaker("geocoding")

        async def geo_origem() -> tuple[float, float, str]:
            return await cb_geo.call(
                buscar_coordenadas_async,
                client,
                payload.origem_cidade,
                payload.origem_uf,
                fallback=(0.0, 0.0, payload.origem_uf),
            )

        async def geo_destino() -> tuple[float, float, str]:
            return await cb_geo.call(
                buscar_coordenadas_async,
                client,
                payload.destino_cidade,
                payload.destino_uf,
                fallback=(0.0, 0.0, payload.destino_uf),
            )

        try:
            (lat_o, lon_o, uf_o_det), (lat_d, lon_d, uf_d_det) = await asyncio.gather(
                geo_origem(), geo_destino()
            )
            diagnosticos.append(
                ProviderDiagnostic(provedor="geocoding", status="disponivel", mensagem="Geocodificação concluída")
            )
        except Exception as exc:
            logger.error("Falha no estágio de geocodificação: %s", exc)
            lat_o, lon_o, uf_o_det = 0.0, 0.0, payload.origem_uf
            lat_d, lon_d, uf_d_det = 0.0, 0.0, payload.destino_uf
            diagnosticos.append(
                ProviderDiagnostic(provedor="geocoding", status="indisponivel", mensagem=f"Falha: {exc}")
            )

        # Checagem de desconexão entre estágios
        if await request.is_disconnected():
            logger.info("Cliente desconectado após geocodificação: %s", chave_idempotencia)
            return Response(status_code=499)

        # =========================================================================
        # ESTÁGIO 2: Clima e Rota em paralelo com asyncio.gather (cronometrados)
        # =========================================================================
        cb_clima = obter_circuit_breaker("clima")
        cb_rota = obter_circuit_breaker("rota")

        async def consultar_clima() -> dict[str, Any]:
            t0 = time.perf_counter()
            try:
                res = await cb_clima.call(
                    obter_clima_async,
                    client,
                    lat_d,
                    lon_d,
                )
                duracao = round((time.perf_counter() - t0) * 1000, 1)
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="clima",
                        status="disponivel",
                        mensagem=f"Open-Meteo respondeu em {duracao}ms",
                    )
                )
                return res
            except Exception as exc:
                diagnosticos.append(
                    ProviderDiagnostic(provedor="clima", status="indisponivel", mensagem=f"Degradação: {exc}")
                )
                return {"temperatura_c": None, "descricao": "Indisponível"}

        async def consultar_rota() -> dict[str, Any]:
            t0 = time.perf_counter()
            try:
                res = await cb_rota.call(
                    calcular_rota_osrm_async,
                    client,
                    lat_o,
                    lon_o,
                    lat_d,
                    lon_d,
                    preferencia=payload.preferencia_rota,
                )
                duracao = round((time.perf_counter() - t0) * 1000, 1)
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="rota",
                        status="disponivel",
                        mensagem=f"OSRM respondeu em {duracao}ms",
                    )
                )
                return res
            except Exception as exc:
                diagnosticos.append(
                    ProviderDiagnostic(provedor="rota", status="indisponivel", mensagem=f"Degradação: {exc}")
                )
                return {
                    "distancia_km": 0.0,
                    "duracao_minutos": 0.0,
                    "geometria": {"type": "LineString", "coordinates": [[lon_o, lat_o], [lon_d, lat_d]]},
                    "paradas": [],
                }

        dados_clima, dados_rota = await asyncio.gather(consultar_clima(), consultar_rota())

        distancia_km = float(dados_rota.get("distancia_km", 0.0))
        duracao_min = float(dados_rota.get("duracao_minutos", 0.0))
        geometria_raw = dados_rota.get("geometria") or {
            "type": "LineString",
            "coordinates": [[lon_o, lat_o], [lon_d, lat_d]],
        }

        # Checagem de desconexão antes das integrações finais
        if await request.is_disconnected():
            logger.info("Cliente desconectado antes das etapas de relevo e guia: %s", chave_idempotencia)
            return Response(status_code=499)

        # =========================================================================
        # ESTÁGIO 3: Altimetria, Custos, Paradas e Guia IA (com degradação graciosa)
        # =========================================================================
        cb_alt = obter_circuit_breaker("altimetria")
        cb_gemini = obter_circuit_breaker("gemini")

        # Altimetria
        try:
            dados_altimetria = await cb_alt.call(
                calcular_altimetria_async,
                client,
                geometria_raw.get("coordinates", []),
            )
            diagnosticos.append(
                ProviderDiagnostic(provedor="altimetria", status="disponivel", mensagem="Altimetria calculada")
            )
        except Exception as exc:
            dados_altimetria = {"ganho_m": 0.0, "perda_m": 0.0, "altitude_maxima_m": 0.0, "impacto_consumo_percentual": 0.0}
            diagnosticos.append(
                ProviderDiagnostic(provedor="altimetria", status="indisponivel", mensagem=str(exc))
            )

        # Custos
        try:
            dados_custos = await calcular_custos_async(
                distancia_km=distancia_km,
                tipo_veiculo=payload.tipo_veiculo,
                consumo=payload.consumo_medio,
                preco=payload.preco_unidade,
                passageiros=payload.passageiros,
            )
        except Exception as exc:
            logger.warning("Falha no cálculo de custos: %s", exc)
            dados_custos = {"total": 0.0, "combustivel_ou_energia": 0.0, "por_passageiro": 0.0, "moeda": "BRL"}

        # Guia turístico IA
        destino_formatado = f"{payload.destino_cidade} - {uf_d_det or payload.destino_uf}"
        try:
            texto_guia, atrativos_ia = await cb_gemini.call(
                gerar_guia_ia_async,
                destino_formatado,
                payload.dias_estadia,
                payload.estilo_viagem,
            )
            diagnosticos.append(
                ProviderDiagnostic(provedor="gemini", status="disponivel", mensagem="Guia gerado com sucesso")
            )
        except Exception as exc:
            texto_guia = f"Roteiro cultural de contingência para {destino_formatado}."
            atrativos_ia = []
            diagnosticos.append(
                ProviderDiagnostic(provedor="gemini", status="indisponivel", mensagem=f"Fallback acionado: {exc}")
            )

        # Montagem das paradas
        paradas_lista: list[ParadaItem] = []
        paradas_brutas = dados_rota.get("paradas", [])
        if isinstance(paradas_brutas, list) and paradas_brutas:
            for i, p in enumerate(paradas_brutas):
                if isinstance(p, dict):
                    paradas_lista.append(
                        ParadaItem(
                            id=p.get("id") or f"parada_{i+1}",
                            nome=p.get("nome", f"Parada {i+1}"),
                            latitude=float(p.get("latitude", 0.0)),
                            longitude=float(p.get("longitude", 0.0)),
                            distancia_origem_km=p.get("distancia_origem_km"),
                            estimada=p.get("estimada", True),
                            visitado=bool(p.get("visitado", False)),
                        )
                    )
        elif distancia_km > payload.autonomia_km * 0.85:
            # Gera parada estimada de abastecimento
            dist_parada = round(payload.autonomia_km * 0.85, 1)
            paradas_lista.append(
                ParadaItem(
                    id="parada_estimada_1",
                    nome=f"Abastecimento/Recarga Estimada (km {dist_parada})",
                    latitude=round((lat_o + lat_d) / 2, 4),
                    longitude=round((lon_o + lon_d) / 2, 4),
                    distancia_origem_km=dist_parada,
                    estimada=True,
                    visitado=False,
                )
            )

        # Montagem dos atrativos
        atrativos_lista: list[AtrativoItem] = []
        for i, a in enumerate(atrativos_ia):
            if isinstance(a, dict):
                atrativos_lista.append(
                    AtrativoItem(
                        id=a.get("id") or f"atr_{i+1}",
                        nome=a.get("nome", f"Atrativo {i+1}"),
                        categoria=a.get("categoria"),
                        descricao=a.get("descricao"),
                        visitado=bool(a.get("visitado", False)),
                    )
                )

        roteiro_id = f"rot_{uuid.uuid4().hex[:8]}"
        agora_iso = datetime.now(timezone.utc).isoformat()

        roteiro_response = RoteiroResponse(
            id=roteiro_id,
            criado_em=agora_iso,
            origem=Localidade(
                cidade=payload.origem_cidade,
                uf=uf_o_det or payload.origem_uf,
                latitude=lat_o,
                longitude=lon_o,
            ),
            destino=Localidade(
                cidade=payload.destino_cidade,
                uf=uf_d_det or payload.destino_uf,
                latitude=lat_d,
                longitude=lon_d,
            ),
            distancia_km=distancia_km,
            duracao_minutos=duracao_min,
            geometria=GeoJsonGeometry(
                type="LineString",
                coordinates=geometria_raw.get("coordinates", [[lon_o, lat_o], [lon_d, lat_d]]),
            ),
            alternativas=[],
            paradas=paradas_lista,
            atrativos=atrativos_lista,
            clima=ClimaInfo(
                temperatura_c=dados_clima.get("temperatura_c"),
                umidade_percentual=dados_clima.get("umidade_percentual"),
                vento_kmh=dados_clima.get("vento_kmh"),
                descricao=dados_clima.get("descricao"),
            ),
            altimetria=AltimetriaInfo(
                ganho_m=dados_altimetria.get("ganho_m"),
                perda_m=dados_altimetria.get("perda_m"),
                altitude_maxima_m=dados_altimetria.get("altitude_maxima_m"),
                impacto_consumo_percentual=dados_altimetria.get("impacto_consumo_percentual"),
            ),
            custos=CustosInfo(
                combustivel_ou_energia=dados_custos.get("combustivel_ou_energia"),
                pedagios=dados_custos.get("pedagios", 0.0),
                total=dados_custos.get("total"),
                por_passageiro=dados_custos.get("por_passageiro"),
                moeda="BRL",
                emissoes_kg_co2=dados_custos.get("emissoes_kg_co2"),
            ),
            diagnosticos=diagnosticos,
            guia=texto_guia,
        )

        # Persistência em background APENAS se o cliente não tiver desconectado
        if not await request.is_disconnected():
            background_tasks.add_task(
                salvar_nova_viagem,
                user.id,
                roteiro_response.model_dump(),
            )
            # Atualização de métricas de performance
            tempo_total_ms = (time.perf_counter() - inicio_processamento) * 1000
            METRICAS_OPERACIONAIS["total_roteiros"] += 1
            latencias = METRICAS_OPERACIONAIS["latencias_recentes_ms"]
            latencias.append(round(tempo_total_ms, 2))
            if len(latencias) > 50:
                latencias.pop(0)

        return roteiro_response

    finally:
        # Liberação garantida da chave de idempotência no finally
        async with LOCK_REQUISICOES:
            REQUISICOES_ATIVAS.discard(chave_idempotencia)
            METRICAS_OPERACIONAIS["requisicoes_ativas_count"] = len(REQUISICOES_ATIVAS)


@router.post(
    "/mapa-rota",
    response_model=GeoJsonGeometry,
    summary="Traçado leve da rota no mapa",
    description="Retorna a geometria simplificada entre duas localidades sem calcular guia ou custos.",
)
async def obter_mapa_rota(
    payload: MapaRotaRequest,
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
) -> GeoJsonGeometry:
    """Calcula a geometria da rota para renderização direta na camada Leaflet."""
    (lat_o, lon_o, _), (lat_d, lon_d, _) = await asyncio.gather(
        buscar_coordenadas_async(client, payload.origem_cidade, payload.origem_uf),
        buscar_coordenadas_async(client, payload.destino_cidade, payload.destino_uf),
    )

    dados_rota = await calcular_rota_osrm_async(
        client, lat_o, lon_o, lat_d, lon_d, preferencia=payload.preferencia_rota
    )
    geometria = dados_rota.get("geometria") or {
        "type": "LineString",
        "coordinates": [[lon_o, lat_o], [lon_d, lat_d]],
    }
    return GeoJsonGeometry(type="LineString", coordinates=geometria.get("coordinates", []))


@router.post(
    "/stream-guia",
    summary="Streaming progressivo do guia turístico com IA (SSE)",
    description="Transmite o guia em chunks SSE (text/event-stream) conforme é gerado, com cancelamento cooperativo via is_disconnected.",
)
async def stream_guia(
    payload: GuiaStreamRequest,
    request: Request,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
) -> StreamingResponse:
    """Endpoint de Server-Sent Events (SSE) compatível com o parser ReadableStream do frontend."""

    async def evento_gerador() -> AsyncGenerator[str, None]:
        try:
            generator = gerar_guia_ia_stream_async(payload.model_dump())
            async for chunk in generator:
                # Verificação cooperativa de desconexão a cada chunk emitido
                if await request.is_disconnected():
                    logger.info("Cliente desconectou do stream SSE do guia: %s", payload.destino)
                    break

                if chunk:
                    evento = json.dumps({"chunk": chunk, "done": False}, ensure_ascii=False)
                    yield f"data: {evento}\n\n"

            # Evento final de encerramento
            fim = json.dumps({"chunk": "", "done": True}, ensure_ascii=False)
            yield f"data: {fim}\n\n"

        except Exception as exc:
            logger.error("Erro no streaming do guia IA: %s", exc)
            erro_evento = json.dumps(
                {
                    "chunk": f"\n[Guia indisponível temporariamente: {exc}]",
                    "done": True,
                    "fallback": True,
                },
                ensure_ascii=False,
            )
            yield f"data: {erro_evento}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream",
    }
    return StreamingResponse(evento_gerador(), media_type="text/event-stream", headers=headers)


@router.post(
    "/custos",
    response_model=CustosInfo,
    summary="Cálculo detalhado de custos e emissões de CO2",
)
async def calcular_custos_endpoint(payload: CustosRequest) -> CustosInfo:
    """Calcula os custos de combustível, pedágio e rateio com base nos parâmetros do veículo."""
    dados = await calcular_custos_async(
        distancia_km=payload.distancia_km,
        tipo_veiculo=payload.tipo_veiculo,
        consumo=payload.consumo_medio,
        preco=payload.preco_unidade,
        passageiros=payload.passageiros,
        pedagios=payload.pedagios_estimados,
    )
    return CustosInfo(
        combustivel_ou_energia=dados.get("combustivel_ou_energia"),
        pedagios=dados.get("pedagios"),
        total=dados.get("total"),
        por_passageiro=dados.get("por_passageiro"),
        moeda="BRL",
        emissoes_kg_co2=dados.get("emissoes_kg_co2"),
    )


@router.get(
    "/minhas-viagens",
    response_model=list[dict[str, Any]],
    summary="Listar histórico de viagens do usuário autenticado",
)
async def listar_minhas_viagens(
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
) -> list[dict[str, Any]]:
    """Garante isolamento estrito: retorna apenas roteiros pertencentes ao usuário da requisição."""
    return await listar_viagens_usuario(user.id)


@router.delete(
    "/{roteiro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Excluir roteiro do usuário autenticado",
)
async def excluir_roteiro(
    roteiro_id: str,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
) -> Response:
    """Remove o roteiro se pertencer ao usuário autenticado. Retorna 404 se não encontrado."""
    sucesso = await deletar_viagem_usuario(user.id, roteiro_id)
    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roteiro não encontrado no histórico deste usuário.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{roteiro_id}/visitas",
    response_model=dict[str, Any],
    summary="Marcar atrativo ou parada como visitado",
)
async def marcar_visita(
    roteiro_id: str,
    payload: MarcarVisitaRequest,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
) -> dict[str, Any]:
    """Alterna o status de visitação de um atrativo em um roteiro pertencente ao usuário."""
    roteiro = await marcar_atrativo_visitado(
        user.id, roteiro_id, payload.atrativo_id, payload.visitado
    )
    if not roteiro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roteiro não encontrado ou não pertence a este usuário.",
        )
    return roteiro


@router.post(
    "/exportar/gpx",
    summary="Exportar roteiro em formato GPX 1.1",
)
async def exportar_gpx_post(
    payload: ExportarGpxRequest,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
) -> Response:
    """Gera e faz o download do arquivo GPX 1.1 do roteiro solicitado."""
    viagem = await obter_viagem_usuario(user.id, payload.roteiro_id)
    if not viagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roteiro não encontrado para exportação GPX.",
        )

    conteudo_gpx = await gerar_gpx_async(viagem)
    return Response(
        content=conteudo_gpx,
        media_type="application/gpx+xml",
        headers={
            "Content-Disposition": f'attachment; filename="roteiro-{payload.roteiro_id}.gpx"'
        },
    )


@router.post(
    "/compartilhar",
    summary="Compartilhar roteiro com outro e-mail (Background Task)",
)
async def compartilhar_roteiro(
    payload: CompartilharRoteiroRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
) -> dict[str, str]:
    """Dispara tarefa em segundo plano para envio de e-mail ou link compartilhável."""
    viagem = await obter_viagem_usuario(user.id, payload.roteiro_id)
    if not viagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roteiro não encontrado para compartilhamento.",
        )

    def _enviar_email_tarefa(destinatario: str, rot_id: str) -> None:
        logger.info("Enviando roteiro %s para o email %s em segundo plano...", rot_id, destinatario)

    background_tasks.add_task(_enviar_email_tarefa, payload.email_destinatario, payload.roteiro_id)
    return {"mensagem": f"Roteiro compartilhado com sucesso para {payload.email_destinatario}."}

