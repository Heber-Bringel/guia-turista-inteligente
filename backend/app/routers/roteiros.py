"""Rotas do ciclo de vida de roteiros (V3 EDA): planejamento concorrente, chat multilíngue, despacho n8n e DLQ."""

import asyncio
import inspect
import json
import time
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import StreamingResponse

from app.core.circuit_breaker import obter_circuit_breaker
from app.core.dependencies import obter_http_client, obter_idioma, obter_usuario_ativo
from app.core.logging_config import logger
from app.schemas.auth import UsuarioPerfil
from app.schemas.roteiros import (
    AltimetriaInfo,
    AtrativoItem,
    ChatRoteiroRequest,
    ChatRoteiroResponse,
    ClimaInfo,
    CompartilharRoteiroRequest,
    CustosInfo,
    CustosRequest,
    DespacharRoteiroRequest,
    DespacharRoteiroResponse,
    ExportarGpxRequest,
    GeoJsonGeometry,
    GuiaStreamRequest,
    Localidade,
    MapaRotaRequest,
    MarcarVisitaRequest,
    ParadaItem,
    ProviderDiagnostic,
    ProviderStatus,
    RotaAlternativa,
    RoteiroRequest,
    RoteiroResponse,
)
from app.services import gemini_service
from app.services.altimetria_service import calcular_altimetria_async
from app.services.clima_service import obter_clima_async
from app.services.custos_service import calcular_custos_async
from app.services.erros import ServicoIndisponivelError
from app.services.gemini_service import (
    gerar_guia_contingencia,
    gerar_guia_ia_com_diagnostico_async,
    gerar_guia_ia_stream_async,
)
from app.services.geocoding_service import buscar_coordenadas_async
from app.services.gpx_service import gerar_gpx_async
from app.services.n8n_service import (
    agendar_despacho_roteiro_background,
    agendar_dlq_background,
)
from app.services.postos_service import localizar_paradas_async, projetar_paradas
from app.services.rota_service import calcular_rota_osrm_async
from app.services.storage_service import (
    deletar_viagem_usuario,
    listar_viagens_usuario,
    marcar_atrativo_visitado,
    obter_viagem_usuario,
    salvar_nova_viagem,
)

router = APIRouter(prefix="/roteiros", tags=["Roteiros"])

# Controle de concorrência e idempotência por requisição
REQUISICOES_ATIVAS: set[str] = set()
LOCK_REQUISICOES = asyncio.Lock()

# Métricas operacionais em memória para telemetria restrita (ChatOps)
METRICAS_OPERACIONAIS: dict[str, Any] = {
    "total_roteiros": 0,
    "latencias_recentes_ms": [],
    "requisicoes_ativas_count": 0,
}

# Patrimônios locais brasileiros que devem ser preservados sem tradução literal em qualquer idioma
PATRIMONIOS_LOCAIS_REFERENCIA = (
    "Parque Nacional de Sete Cidades",
    "Serra da Capivara",
    "Delta do Parnaíba",
    "Açude Caldeirão",
    "BR-343",
    "Pelourinho",
    "Chapada Diamantina",
    "Lençóis Maranhenses",
    "Fernando de Noronha",
    "Congresso Nacional",
    "Catedral Metropolitana",
    "Praia de Iracema",
)

_TEMPLATES_CHAT_MULTILINGUE: dict[str, dict[str, Any]] = {
    "pt": {
        "intro": "Roteiro personalizado para {destino} ({dias} dia(s), ritmo {ritmo}, com {acompanhantes}):",
        "manha": "• Manhã: Explore {patrimonio_1} no início do dia com clima ameno.",
        "tarde": "• Tarde: Visite {patrimonio_2} e aprecie a paisagem regional.",
        "noite": "• Noite: Experiência gastronômica focada em {gastronomia}.",
        "dica": "💡 Dica personalizada: Roteiro ajustado à sua solicitação ({mensagem_curta}).",
        "sugestoes": [
            "Quais restaurantes típicos ficam próximos à rota?",
            "Como adaptar o passeio para dias chuvosos?",
            "Onde abastecer com segurança na BR-343?",
        ],
    },
    "en": {
        "intro": "Personalized itinerary for {destino} ({dias} day(s), {ritmo} pace, traveling with {acompanhantes}):",
        "manha": "• Morning: Visit {patrimonio_1} early for milder temperatures and authentic views.",
        "tarde": "• Afternoon: Explore {patrimonio_2} at a comfortable pace.",
        "noite": "• Evening: Local dining experience featuring {gastronomia}.",
        "dica": "💡 Travel tip: Tailored to your request ({mensagem_curta}) while preserving local heritage names.",
        "sugestoes": [
            "Which traditional restaurants are near the route?",
            "What is the best time to visit Parque Nacional de Sete Cidades?",
            "Where are the ANP-certified fuel stops along BR-343?",
        ],
    },
    "es": {
        "intro": "Itinerario personalizado para {destino} ({dias} día(s), ritmo {ritmo}, con {acompanhantes}):",
        "manha": "• Mañana: Recorra {patrimonio_1} en las primeiras horas de la mañana.",
        "tarde": "• Tarde: Conozca {patrimonio_2} con paradas panorámicas.",
        "noite": "• Noche: Experiencia gastronómica dedicada a {gastronomia}.",
        "dica": "💡 Consejo: Ajustado a su preferencia ({mensagem_curta}) conservando los nombres patrimoniales.",
        "sugestoes": [
            "¿Qué platos típicos probar cerca de la ruta?",
            "¿Cuál es el mejor horario para visitar Parque Nacional de Sete Cidades?",
            "¿Dónde están las estaciones certificadas por la ANP en la BR-343?",
        ],
    },
    "fr": {
        "intro": "Itinéraire personnalisé pour {destino} ({dias} jour(s), rythme {ritmo}, avec {acompanhantes}):",
        "manha": "• Matin: Découvrez {patrimonio_1} dès l'ouverture.",
        "tarde": "• Après-midi: Visitez {patrimonio_2} en toute tranquillité.",
        "noite": "• Soir: Dégustation locale centrée sur {gastronomia}.",
        "dica": "💡 Conseil: Adapté à votre demande ({mensagem_curta}).",
        "sugestoes": [
            "Quels plats régionaux déguster sur le parcours ?",
            "Quel est le meilleur moment pour visiter Parque Nacional de Sete Cidades ?",
        ],
    },
    "zh": {
        "intro": "{destino} 定制行程（{dias} 天，节奏：{ritmo}，同行：{acompanhantes}）：",
        "manha": "• 上午：前往参观 {patrimonio_1}，感受当地自然与历史遗产。",
        "tarde": "• 下午：游览 {patrimonio_2}，享受舒适旅程。",
        "noite": "• 晚上：品尝地道美食（{gastronomia}）。",
        "dica": "💡 贴士：已根据您的需求（{mensagem_curta}）调整行程并保留当地遗产原名。",
        "sugestoes": ["附近有哪些地道餐厅？", "BR-343 沿线有哪些 ANP 认证加油站？"],
    },
    "hi": {
        "intro": "{destino} के लिए व्यक्तिगत यात्रा कार्यक्रम ({dias} दिन, गति: {ritmo}, साथ: {acompanhantes}):",
        "manha": "• सुबह: {patrimonio_1} का भ्रमण करें।",
        "tarde": "• दोपहर: {patrimonio_2} के प्रमुख स्थलों की सैर करें।",
        "noite": "• रात: स्थानीय व्यंजन ({gastronomia}) का आनंद लें।",
        "dica": "💡 सुझाव: आपके अनुरोध ({mensagem_curta}) के अनुसार अनुकूलित।",
        "sugestoes": ["मार्ग के पास कौन से पारंपरिक रेस्तरां हैं?", "BR-343 पर प्रमाणित ईंधन स्टेशन कहाँ हैं?"],
    },
    "ar": {
        "intro": "مسار رحلة مخصص إلى {destino} ({dias} أيام، وتيرة {ritmo}، برفقة {acompanhantes}):",
        "manha": "• الصباح: زيارة {patrimonio_1} في الصباح الباكر.",
        "tarde": "• بعد الظهر: استكشاف {patrimonio_2} بهدوء.",
        "noite": "• المساء: تجربة المأكولات المحلية ({gastronomia}).",
        "dica": "💡 نصيحة: تم تخصيص المسار حسب طلبك ({mensagem_curta}) مع الحفاظ على الأسماء الأصلية للمعالم.",
        "sugestoes": ["ما هي أفضل المطاعم المحلية؟", "أين تقع محطات الوقود المعتمدة على طريق BR-343؟"],
    },
    "ru": {
        "intro": "Персональный маршрут для {destino} ({dias} дн., темп: {ritmo}, компания: {acompanhantes}):",
        "manha": "• Утро: Посетите {patrimonio_1} в утренние часы.",
        "tarde": "• День: Прогулка по {patrimonio_2}.",
        "noite": "• Вечер: Местная гастрономия ({gastronomia}).",
        "dica": "💡 Совет: Маршрут адаптирован под ваш запрос ({mensagem_curta}).",
        "sugestoes": ["Какие традиционные блюда стоит попробовать?", "Где находятся сертифицированные АЗС на BR-343?"],
    },
}


def _mensagem_diagnostico_segura(exc: Exception, fallback_amigavel: str) -> str:
    """Preserva mensagens tratadas de ServicoIndisponivelError e higieniza exceções internas/cruas."""
    if isinstance(exc, ServicoIndisponivelError):
        return f"Degradação: {exc}"
    return fallback_amigavel


def _selecionar_patrimonios_destino(destino: str, mensagem: str) -> list[str]:
    """Identifica patrimônios locais aplicáveis ao destino ou citados pelo usuário para preservá-los intactos."""
    texto_busca = f"{destino} {mensagem}".lower()
    encontrados: list[str] = []
    for pat in PATRIMONIOS_LOCAIS_REFERENCIA:
        if pat.lower() in texto_busca and pat not in encontrados:
            encontrados.append(pat)

    if any(k in texto_busca for k in ("piripiri", "parnaiba", "parnaíba", "teresina", "piaui", "piauí", "pi")):
        for padrao_pi in ("Parque Nacional de Sete Cidades", "Açude Caldeirão", "Delta do Parnaíba", "BR-343"):
            if padrao_pi not in encontrados:
                encontrados.append(padrao_pi)
    elif "salvador" in texto_busca or "ba" in texto_busca:
        for padrao_ba in ("Pelourinho", "Chapada Diamantina"):
            if padrao_ba not in encontrados:
                encontrados.append(padrao_ba)
    elif "brasilia" in texto_busca or "brasília" in texto_busca or "df" in texto_busca:
        for padrao_df in ("Congresso Nacional", "Catedral Metropolitana"):
            if padrao_df not in encontrados:
                encontrados.append(padrao_df)

    if not encontrados:
        encontrados = ["Parque Nacional de Sete Cidades", "Centro Histórico Cultural"]
    return encontrados


@router.post(
    "/planejar",
    response_model=RoteiroResponse,
    summary="Planejar novo roteiro turístico com orquestração assíncrona e DLQ em BackgroundTasks",
    description="Pipeline com 2 estágios de asyncio.gather, propagação de Accept-Language, dados ANP e DLQ assíncrona.",
)
async def planejar_roteiro(
    payload: RoteiroRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
    idioma: Annotated[str, Depends(obter_idioma)],
) -> Any:
    """Orquestra o planejamento assíncrono em múltiplos estágios com tratamento de concorrência e DLQ."""
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
                ProviderDiagnostic(provedor="geocoding", status="disponivel", mensagem="Localidades confirmadas")
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Falha no estágio de geocodificação: %s", exc)
            agendar_dlq_background(
                background_tasks=background_tasks,
                client=client,
                rota="/api/v1/roteiros/planejar",
                servico="geocoding",
                erro=exc,
                contexto={"origem": payload.origem_cidade, "destino": payload.destino_cidade},
            )
            lat_o, lon_o, uf_o_det = 0.0, 0.0, payload.origem_uf
            lat_d, lon_d, uf_d_det = 0.0, 0.0, payload.destino_uf
            diagnosticos.append(
                ProviderDiagnostic(
                    provedor="geocoding",
                    status="indisponivel",
                    mensagem=_mensagem_diagnostico_segura(
                        exc, "Coordenadas aproximadas utilizadas temporariamente."
                    ),
                )
            )

        # Checagem de desconexão entre estágios
        if await request.is_disconnected():
            logger.info("Cliente desconectado após geocodificação: %s", chave_idempotencia)
            return Response(status_code=499)

        # =========================================================================
        # ESTÁGIO 2: Clima e Rota em paralelo com asyncio.gather
        # =========================================================================
        cb_clima = obter_circuit_breaker("clima")
        cb_rota = obter_circuit_breaker("rota")

        async def consultar_clima() -> dict[str, Any]:
            try:
                res = await cb_clima.call(
                    obter_clima_async,
                    client,
                    lat_d,
                    lon_d,
                )
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="clima",
                        status="disponivel",
                        mensagem="Previsão meteorológica atualizada",
                    )
                )
                return res
            except Exception as exc:  # noqa: BLE001
                agendar_dlq_background(
                    background_tasks=background_tasks,
                    client=client,
                    rota="/api/v1/roteiros/planejar",
                    servico="clima",
                    erro=exc,
                    contexto={"destino": payload.destino_cidade},
                )
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="clima",
                        status="indisponivel",
                        mensagem=_mensagem_diagnostico_segura(
                            exc, "Previsão meteorológica temporariamente indisponível."
                        ),
                    )
                )
                return {"temperatura_c": None, "descricao": "Indisponível"}

        async def consultar_rota() -> dict[str, Any]:
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
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="rota",
                        status="disponivel",
                        mensagem="Traçado rodoviário calculado",
                    )
                )
                return res
            except Exception as exc:  # noqa: BLE001
                agendar_dlq_background(
                    background_tasks=background_tasks,
                    client=client,
                    rota="/api/v1/roteiros/planejar",
                    servico="rota",
                    erro=exc,
                    contexto={"origem": payload.origem_cidade, "destino": payload.destino_cidade},
                )
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="rota",
                        status="indisponivel",
                        mensagem=_mensagem_diagnostico_segura(
                            exc, "Rota estimada em linha direta temporariamente."
                        ),
                    )
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
        # ESTÁGIO 3: Altimetria, paradas ANP e guia IA em paralelo; custos em seguida
        # =========================================================================
        cb_alt = obter_circuit_breaker("altimetria")
        cb_postos = obter_circuit_breaker("postos")
        cb_gemini = obter_circuit_breaker("gemini")
        coordenadas_rota = geometria_raw.get("coordinates", [])
        destino_formatado = f"{payload.destino_cidade} - {uf_d_det or payload.destino_uf}"

        async def consultar_altimetria() -> dict[str, Any]:
            try:
                res = await cb_alt.call(calcular_altimetria_async, client, coordenadas_rota)
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="altimetria",
                        status="disponivel",
                        mensagem="Perfil de relevo calculado",
                    )
                )
                return res
            except Exception as exc:  # noqa: BLE001
                agendar_dlq_background(
                    background_tasks=background_tasks,
                    client=client,
                    rota="/api/v1/roteiros/planejar",
                    servico="altimetria",
                    erro=exc,
                )
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="altimetria",
                        status="indisponivel",
                        mensagem="Perfil de relevo simplificado utilizado.",
                    )
                )
                return {"ganho_m": 0.0, "perda_m": 0.0, "altitude_maxima_m": 0.0, "impacto_consumo_percentual": 0.0}

        async def consultar_paradas() -> list[dict[str, Any]]:
            paradas_da_rota = dados_rota.get("paradas")
            if isinstance(paradas_da_rota, list) and paradas_da_rota:
                return paradas_da_rota

            argumentos = (coordenadas_rota, distancia_km, payload.autonomia_km, payload.tipo_veiculo)
            try:
                paradas = await cb_postos.call(localizar_paradas_async, client, *argumentos)
            except Exception as exc:  # noqa: BLE001
                agendar_dlq_background(
                    background_tasks=background_tasks,
                    client=client,
                    rota="/api/v1/roteiros/planejar",
                    servico="postos",
                    erro=exc,
                )
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="postos",
                        status="indisponivel",
                        mensagem="Paradas projetadas pela autonomia do veículo.",
                    )
                )
                return projetar_paradas(*argumentos)

            status_postos: ProviderStatus
            if not paradas:
                mensagem, status_postos = "Rota dentro da autonomia: nenhuma parada necessária", "disponivel"
            elif all(p.get("estimada", True) for p in paradas):
                mensagem, status_postos = "Posições estimadas pela autonomia; postos não confirmados", "parcial"
            else:
                confirmadas = sum(1 for p in paradas if not p.get("estimada", True))
                mensagem = f"{confirmadas} de {len(paradas)} parada(s) confirmada(s) em postos regulados"
                status_postos = "disponivel"
            diagnosticos.append(ProviderDiagnostic(provedor="postos", status=status_postos, mensagem=mensagem))
            return paradas

        async def consultar_guia() -> tuple[str, list[dict[str, Any]]]:
            try:
                sig = inspect.signature(gerar_guia_ia_com_diagnostico_async)
                kwargs_guia: dict[str, Any] = {"clima_info": dados_clima}
                if "idioma" in sig.parameters:
                    kwargs_guia["idioma"] = idioma

                texto, atrativos, info = await cb_gemini.call(
                    gerar_guia_ia_com_diagnostico_async,
                    destino_formatado,
                    payload.dias_estadia,
                    payload.estilo_viagem,
                    **kwargs_guia,
                )
                if info.get("fallback_utilizado"):
                    diagnosticos.append(
                        ProviderDiagnostic(
                            provedor="gemini",
                            status="parcial",
                            mensagem="Guia cultural curado exibido em modo de contingência.",
                        )
                    )
                else:
                    diagnosticos.append(
                        ProviderDiagnostic(
                            provedor="gemini",
                            status="disponivel",
                            mensagem="Guia turístico personalizado gerado.",
                        )
                    )
                return texto, atrativos
            except Exception as exc:  # noqa: BLE001
                agendar_dlq_background(
                    background_tasks=background_tasks,
                    client=client,
                    rota="/api/v1/roteiros/planejar",
                    servico="gemini",
                    erro=exc,
                    contexto={"destino": destino_formatado, "idioma": idioma},
                )
                diagnosticos.append(
                    ProviderDiagnostic(
                        provedor="gemini",
                        status="indisponivel",
                        mensagem="Guia cultural de contingência ativado.",
                    )
                )
                return f"Roteiro cultural de contingência para {destino_formatado}.", []

        dados_altimetria, paradas_brutas, (texto_guia, atrativos_ia) = await asyncio.gather(
            consultar_altimetria(), consultar_paradas(), consultar_guia()
        )

        # Custos (o relevo aumenta o consumo)
        try:
            dados_custos = await calcular_custos_async(
                distancia_km=distancia_km,
                tipo_veiculo=payload.tipo_veiculo,
                consumo=payload.consumo_medio,
                preco=payload.preco_unidade,
                passageiros=payload.passageiros,
                impacto_relevo_percentual=float(dados_altimetria.get("impacto_consumo_percentual") or 0.0),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha no cálculo de custos: %s", exc)
            dados_custos = {"total": 0.0, "combustivel_ou_energia": 0.0, "por_passageiro": 0.0, "moeda": "BRL"}

        # Montagem das paradas preservando todos os atributos regulatórios da ANP (V3)
        paradas_lista: list[ParadaItem] = []
        for i, p in enumerate(paradas_brutas):
            if isinstance(p, dict):
                combustiveis_raw = p.get("combustiveis")
                combustiveis_lista = (
                    [str(c) for c in combustiveis_raw]
                    if isinstance(combustiveis_raw, list)
                    else []
                )
                paradas_lista.append(
                    ParadaItem(
                        id=p.get("id") or f"parada_{i+1}",
                        nome=p.get("nome", f"Parada {i+1}"),
                        latitude=float(p.get("latitude", 0.0)),
                        longitude=float(p.get("longitude", 0.0)),
                        distancia_origem_km=p.get("distancia_origem_km"),
                        estimada=p.get("estimada", True),
                        visitado=bool(p.get("visitado", False)),
                        cnpj=p.get("cnpj"),
                        razao_social=p.get("razao_social"),
                        avaliacao=float(p["avaliacao"]) if p.get("avaliacao") is not None else None,
                        tempo_autorizacao_anp=p.get("tempo_autorizacao_anp"),
                        combustiveis=combustiveis_lista,
                        ranking_score=float(p["ranking_score"]) if p.get("ranking_score") is not None else None,
                        rodovia=p.get("rodovia"),
                        municipio=p.get("municipio"),
                        uf=p.get("uf"),
                    )
                )

        # Rotas alternativas (Sugestão 01 / 02)
        alternativas = [
            RotaAlternativa(
                type="LineString",
                coordinates=alt["geometria"]["coordinates"],
                nome=alt.get("nome"),
                distancia_km=alt.get("distancia_km"),
                duracao_minutos=alt.get("duracao_minutos"),
            )
            for alt in (dados_rota.get("alternativas") or [])
            if isinstance(alt, dict) and alt.get("geometria")
        ]

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
            idioma=idioma,
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
            alternativas=alternativas,
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
                altitude_minima_m=dados_altimetria.get("altitude_minima_m"),
                desnivel_liquido_m=dados_altimetria.get("desnivel_liquido_m"),
                impacto_consumo_percentual=dados_altimetria.get("impacto_consumo_percentual"),
                fonte=dados_altimetria.get("fonte"),
                perfil=dados_altimetria.get("perfil"),
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
    "/chat",
    response_model=ChatRoteiroResponse,
    summary="Diálogo interativo e multilíngue com Gemini para construir roteiro personalizado (V3)",
    description=(
        "Constrói ou refina o roteiro via conversa considerando ritmo de viagem, acompanhantes e gastronomia, "
        "adaptando ao idioma de Accept-Language e preservando nomes próprios de patrimônios locais."
    ),
)
async def conversar_roteiro_chat(
    payload: ChatRoteiroRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
    idioma: Annotated[str, Depends(obter_idioma)],
) -> ChatRoteiroResponse:
    """Processa turno de diálogo com o Gemini, adaptando ao idioma e preservando patrimônios locais."""
    patrimonios = _selecionar_patrimonios_destino(payload.destino, payload.mensagem)

    # Se o módulo gemini_service (Douglas) expuser função dedicada de diálogo/chat, delega a ela
    fn_chat_service = getattr(gemini_service, "conversar_roteiro_ia_async", None) or getattr(
        gemini_service, "dialogar_roteiro_async", None
    )

    if callable(fn_chat_service):
        try:
            resultado = await fn_chat_service(
                destino=payload.destino,
                dias=payload.dias_estadia,
                estilo=payload.estilo_viagem,
                ritmo_viagem=payload.ritmo_viagem,
                acompanhantes=payload.acompanhantes,
                preferencias_gastronomia=payload.preferencias_gastronomia,
                mensagem=payload.mensagem,
                historico=[m.model_dump() for m in payload.historico],
                clima_info=payload.clima_info,
                idioma=idioma,
            )
            if isinstance(resultado, dict):
                return ChatRoteiroResponse(
                    resposta=str(resultado.get("resposta") or ""),
                    idioma=str(resultado.get("idioma") or idioma),
                    destino=payload.destino,
                    roteiro_personalizado=resultado.get("roteiro_personalizado") or resultado.get("resposta"),
                    patrimonios_preservados=resultado.get("patrimonios_preservados") or patrimonios,
                    sugestoes_proximos_passos=resultado.get("sugestoes_proximos_passos") or [],
                    fallback_utilizado=bool(resultado.get("fallback_utilizado", False)),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha no serviço de chat Gemini, acionando DLQ e resposta curada: %s", exc)
            agendar_dlq_background(
                background_tasks=background_tasks,
                client=client,
                rota="/api/v1/roteiros/chat",
                servico="gemini_chat",
                erro=exc,
                contexto={"destino": payload.destino, "idioma": idioma, "usuario": user.id},
            )

    # Construção multilíngue determinística/curada (preservando nomes próprios de patrimônios locais)
    tpl = _TEMPLATES_CHAT_MULTILINGUE.get(idioma, _TEMPLATES_CHAT_MULTILINGUE["pt"])
    pat_1 = patrimonios[0]
    pat_2 = patrimonios[1] if len(patrimonios) > 1 else patrimonios[0]
    msg_curta = payload.mensagem.strip()[:90]

    linhas = [
        tpl["intro"].format(
            destino=payload.destino,
            dias=payload.dias_estadia,
            ritmo=payload.ritmo_viagem,
            acompanhantes=payload.acompanhantes,
        ),
        tpl["manha"].format(patrimonio_1=pat_1),
        tpl["tarde"].format(patrimonio_2=pat_2),
        tpl["noite"].format(gastronomia=payload.preferencias_gastronomia),
        tpl["dica"].format(mensagem_curta=msg_curta),
    ]
    texto_resposta = "\n".join(linhas)

    return ChatRoteiroResponse(
        resposta=texto_resposta,
        idioma=idioma,
        destino=payload.destino,
        roteiro_personalizado=texto_resposta,
        patrimonios_preservados=patrimonios,
        sugestoes_proximos_passos=list(tpl["sugestoes"]),
        fallback_utilizado=False,
    )


@router.post(
    "/despachar",
    response_model=DespacharRoteiroResponse,
    summary="Despachar roteiro personalizado por E-mail ou WhatsApp via n8n (V3)",
    description=(
        "Substitui o download manual direto por uma entrega multicanal exclusiva orientada a eventos "
        "em BackgroundTasks para o webhook turismo-despachar-roteiro do n8n."
    ),
)
async def despachar_roteiro_endpoint(
    payload: DespacharRoteiroRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
    idioma: Annotated[str, Depends(obter_idioma)],
) -> DespacharRoteiroResponse:
    """Valida o roteiro e agenda o envio multicanal (E-mail HTML transacional ou WhatsApp) via n8n."""
    dados_roteiro: dict[str, Any] | None = payload.roteiro

    if dados_roteiro is None and payload.roteiro_id:
        dados_roteiro = await obter_viagem_usuario(user.id, payload.roteiro_id)

    if not dados_roteiro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roteiro não encontrado para despacho multicanal.",
        )

    evento = agendar_despacho_roteiro_background(
        background_tasks=background_tasks,
        client=client,
        canal=payload.canal,
        destinatario=payload.destinatario,
        roteiro=dados_roteiro,
        idioma=idioma,
        nome_viajante=payload.nome_viajante or user.nome,
        resumo_guia=payload.resumo_guia,
    )

    canal_label = "E-mail" if payload.canal == "email" else "WhatsApp"
    return DespacharRoteiroResponse(
        status="agendado",
        protocolo=evento["protocolo"],
        canal=payload.canal,
        destinatario=payload.destinatario,
        idioma=idioma,
        mensagem=(
            f"Seu roteiro está sendo enviado por {canal_label} para {payload.destinatario} "
            f"(protocolo {evento['protocolo']})."
        ),
    )


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
    description="Transmite o guia em chunks SSE (text/event-stream) conforme é gerado, com cancelamento cooperativo.",
)
async def stream_guia(
    payload: GuiaStreamRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
    idioma: Annotated[str, Depends(obter_idioma)],
) -> StreamingResponse:
    """Endpoint de Server-Sent Events (SSE) compatível com o parser ReadableStream do frontend."""
    dados_stream = payload.model_dump()
    dados_stream["idioma"] = idioma

    async def evento_gerador() -> AsyncGenerator[str, None]:
        try:
            generator = gerar_guia_ia_stream_async(dados_stream)
            async for chunk in generator:
                if await request.is_disconnected():
                    logger.info("Cliente desconectou do stream SSE do guia: %s", payload.destino)
                    break

                if chunk:
                    evento = json.dumps({"chunk": chunk, "done": False}, ensure_ascii=False)
                    yield f"data: {evento}\n\n"

            fim = json.dumps({"chunk": "", "done": True}, ensure_ascii=False)
            yield f"data: {fim}\n\n"

        except Exception as exc:  # noqa: BLE001
            logger.error("Erro no streaming do guia IA: %s", exc)
            agendar_dlq_background(
                background_tasks=background_tasks,
                client=client,
                rota="/api/v1/roteiros/stream-guia",
                servico="gemini_stream",
                erro=exc,
                contexto={"destino": payload.destino, "idioma": idioma},
            )
            guia_fallback = gerar_guia_contingencia(
                payload.destino, payload.dias_estadia, payload.clima_info
            )
            erro_evento = json.dumps(
                {
                    "chunk": f"\n\n{guia_fallback}",
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
    summary="Compartilhar roteiro por e-mail via n8n (BackgroundTasks)",
)
async def compartilhar_roteiro(
    payload: CompartilharRoteiroRequest,
    background_tasks: BackgroundTasks,
    user: Annotated[UsuarioPerfil, Depends(obter_usuario_ativo)],
    client: Annotated[httpx.AsyncClient, Depends(obter_http_client)],
    idioma: Annotated[str, Depends(obter_idioma)],
) -> dict[str, str]:
    """Dispara tarefa em segundo plano para envio do roteiro por e-mail via webhook do n8n."""
    viagem = await obter_viagem_usuario(user.id, payload.roteiro_id)
    if not viagem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roteiro não encontrado para compartilhamento.",
        )

    agendar_despacho_roteiro_background(
        background_tasks=background_tasks,
        client=client,
        canal="email",
        destinatario=payload.email_destinatario,
        roteiro=viagem,
        idioma=idioma,
        nome_viajante=user.nome,
    )
    return {"mensagem": f"Roteiro compartilhado com sucesso para {payload.email_destinatario}."}
