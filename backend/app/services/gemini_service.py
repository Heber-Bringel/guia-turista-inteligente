"""Serviço de IA: guia turístico conciso e chat multi-turno via Google Gemini, multilíngue e com fallback.

O idioma vem do cabeçalho `Accept-Language` (normalizado pelo roteador) e vale para o prompt, para o guia
de contingência e para o chat. Em qualquer idioma, nomes próprios de patrimônios locais são preservados
sem tradução literal (ver `app.services.idiomas`).
"""

import asyncio
import os
import re
import unicodedata
from collections.abc import AsyncGenerator
from typing import Any

from google import genai
from google.genai import types

from app.core.catalogo import GUIAS_CURADOS
from app.core.config import settings
from app.core.logging_config import logger
from app.services.idiomas import (
    IDIOMA_PADRAO,
    NOMES_IDIOMA,
    identificar_patrimonios,
    normalizar_codigo_idioma,
    normalizar_texto,
    preservar_patrimonios,
    textos,
)

# Modelos tentados em ordem; GEMINI_MODEL (variável de ambiente), se definida, tem prioridade
MODELOS_PADRAO = ("gemini-2.5-flash", "gemini-2.5-flash-lite")

PERFIS_VIAJANTE: dict[str, str] = {
    "cultural": "Cultural",
    "gastronomico": "Gastronômico",
    "ecoturismo": "Ecoturismo / Aventura",
    "aventura": "Ecoturismo / Aventura",
    "familia": "Família",
    "romantico": "Romântico / Econômico",
    "economico": "Romântico / Econômico",
}

# Limites de concisão do enunciado
MAX_PALAVRAS_IDENTIDADE = 20
MAX_PALAVRAS_TURNO = 15

TITULO_IDENTIDADE = "🏛️ IDENTIDADE"
TITULO_ROTEIRO = "🗺️ ROTEIRO"
TITULO_GASTRONOMIA = "🍲 GASTRONOMIA"
TITULO_DICA = "💡 DICA PRÁTICA"

# Palavras por fragmento do guia de contingência em streaming (emitido sem espera: primeiro chunk < 300 ms)
CHUNK_PALAVRAS_FALLBACK = 3


def _nome_cidade(destino: str) -> str:
    """Remove o sufixo ' - UF' do destino formatado ('Brasília - DF' -> 'Brasília')."""
    return re.sub(r"\s*-\s*[A-Za-z]{2}$", "", destino.strip()).strip() or "o destino"


def _chave_catalogo(destino: str) -> str:
    """Normaliza o nome da cidade (sem UF, sem acentos, minúsculo) para consultar o catálogo curado."""
    nfkd = unicodedata.normalize("NFKD", _nome_cidade(destino))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def limpar_formato_texto(texto: str) -> str:
    """Remove Markdown, saudações e despedidas residuais de uma resposta de LLM, mantendo texto puro com emojis."""
    if not texto:
        return ""
    limpo = texto.replace("```", "").replace("`", "")
    limpo = re.sub(r"(?m)^[\*\-]\s+", "• ", limpo)  # a lista é convertida antes do negrito/itálico
    limpo = re.sub(r"(?m)^#+\s*", "", limpo)
    limpo = re.sub(r"\*\*([^*]+)\*\*", r"\1", limpo)
    limpo = re.sub(r"\*([^*]+)\*", r"\1", limpo)
    limpo = limpo.replace("**", "").replace("*", "")
    limpo = re.sub(r"__([^_]+)__", r"\1", limpo)
    limpo = re.sub(
        r"(?i)^(olá|ola|com certeza|claro|aqui está|aqui esta|segue|preparado|bem-vindo)[^\n]*\n+",
        "",
        limpo.strip(),
    )
    limpo = re.sub(
        r"(?i)\n+(espero que aproveite|boa viagem|aproveite sua viagem|espero ter ajudado|qualquer dúvida)[^\n]*$",
        "",
        limpo.strip(),
    )
    return re.sub(r"\n{3,}", "\n\n", limpo).strip()


def _limpar_chunk(chunk: str) -> str:
    """Limpeza mínima de um fragmento de streaming (sem contexto de linha): remove marcas de Markdown."""
    return chunk.replace("`", "").replace("*", "").replace("#", "")


def _descrever_clima(clima_info: dict[str, Any] | None) -> str:
    """Resume o clima em uma frase para o prompt; vazio quando não há dados."""
    if not clima_info:
        return ""
    partes = []
    if clima_info.get("temperatura_c") is not None:
        partes.append(f"{round(float(clima_info['temperatura_c']))} °C")
    if clima_info.get("descricao"):
        partes.append(str(clima_info["descricao"]).lower())
    if clima_info.get("umidade_percentual") is not None:
        partes.append(f"umidade {round(float(clima_info['umidade_percentual']))}%")
    if clima_info.get("vento_kmh") is not None:
        partes.append(f"vento {round(float(clima_info['vento_kmh']))} km/h")
    return ", ".join(partes)


def montar_prompt(
    destino: str,
    dias: int,
    estilo: str,
    clima_info: dict[str, Any] | None = None,
    atrativos: list[dict[str, Any]] | None = None,
    gastronomia: list[str] | None = None,
    incluir_atrativos: bool = False,
    idioma: str = IDIOMA_PADRAO,
) -> str:
    """Monta o prompt do 'assistente de bordo' com os limites de concisão do enunciado.

    Para 1 dia o roteiro usa Manhã/Tarde/Noite; para mais dias, uma linha por dia numerado.
    Com `incluir_atrativos`, pede uma última linha 'ATRATIVOS: a; b; c' que o serviço extrai do texto.
    Fora do português, acrescenta a instrução de idioma e a regra de preservação dos patrimônios locais.
    """
    perfil = PERFIS_VIAJANTE.get(estilo, "Cultural")
    clima = _descrever_clima(clima_info)

    contexto = [f"Destino: {destino}. Duração: {dias} dia(s). Perfil do viajante: {perfil}."]
    if clima:
        contexto.append(f"Clima atual no destino: {clima}.")
    nomes_atrativos = [str(a.get("nome")) for a in (atrativos or []) if a.get("nome")]
    if nomes_atrativos:
        contexto.append(f"Atrativos já sugeridos (priorize-os): {', '.join(nomes_atrativos[:5])}.")
    if gastronomia:
        contexto.append(f"Sabores locais de referência: {', '.join(gastronomia[:5])}.")

    if dias == 1:
        turnos = "• Manhã: / • Tarde: / • Noite:"
    else:
        turnos = "; ".join(f"• Dia {n}:" for n in range(1, dias + 1))

    linhas = [
        "Você é um assistente de bordo ágil e ultra-objetivo. Monte um roteiro minimalista.",
        *contexto,
        "",
        "FORMATO EXATO (cada item numa linha própria, nesta ordem):",
        f"{TITULO_IDENTIDADE}: 1 frase de até {MAX_PALAVRAS_IDENTIDADE} palavras sobre a identidade e a atmosfera local.",
        (
            f"{TITULO_ROTEIRO}: uma linha por turno ({turnos}), cada uma com 1 frase de ação de até "
            f"{MAX_PALAVRAS_TURNO} palavras."
        ),
        f"{TITULO_GASTRONOMIA}: 1 frase citando de 2 a 3 pratos ou sabores e onde saboreá-los.",
        f"{TITULO_DICA}: 1 frase ligando temperatura e tempo ao vestuário e aos horários.",
    ]
    if incluir_atrativos:
        linhas.append("📍 ATRATIVOS: 3 nomes de lugares reais do destino separados por ponto e vírgula, sem descrição.")
    linhas += [
        "",
        (
            "REGRAS: texto puro com emojis; NENHUM Markdown (sem *, #, _ ou crases); sem saudação, "
            "sem despedida e sem nada além do formato acima."
        ),
    ]
    codigo = normalizar_codigo_idioma(idioma)
    if codigo != IDIOMA_PADRAO:
        linhas.append(instrucao_idioma(codigo, identificar_patrimonios(destino, *nomes_atrativos)))
    return "\n".join(linhas)


def instrucao_idioma(idioma: str, patrimonios: list[str]) -> str:
    """Regra de idioma do prompt: responder no idioma pedido sem traduzir nomes próprios de patrimônios."""
    codigo = normalizar_codigo_idioma(idioma)
    exemplos = ", ".join(f'"{p}"' for p in (patrimonios or ["Parque Nacional de Sete Cidades", "BR-343"])[:6])
    return (
        f"IDIOMA: escreva TODA a resposta em {NOMES_IDIOMA[codigo]} (código '{codigo}'), inclusive os títulos. "
        "NOMES PRÓPRIOS: mantenha nomes de patrimônios, parques, monumentos, cidades, rodovias e pratos típicos "
        f"exatamente como no original em português, sem traduzir nem transliterar (ex.: {exemplos}). "
        "Ex.: escreva 'Parque Nacional de Sete Cidades', nunca 'Seven Cities National Park'."
    )


def extrair_atrativos(texto: str) -> tuple[str, list[dict[str, Any]]]:
    """Separa a linha 'ATRATIVOS: a; b; c' do guia e a converte em itens estruturados."""
    atrativos: list[dict[str, Any]] = []
    restante: list[str] = []
    for linha in texto.splitlines():
        achado = re.match(r"^\W*ATRATIVOS\s*:\s*(.+)$", linha.strip(), flags=re.IGNORECASE)
        if achado:
            for nome in (n.strip(" .•-") for n in achado.group(1).split(";")):
                if nome:
                    atrativos.append({"id": f"atr_{len(atrativos) + 1}", "nome": nome, "visitado": False})
        else:
            restante.append(linha)
    return "\n".join(restante).strip(), atrativos


def _resumir(item: str, max_palavras: int) -> str:
    """Primeira oração do item, limitada a `max_palavras` palavras."""
    oracao = re.split(r"[.;:]\s|\s[-–]\s", item.strip())[0]
    return " ".join(oracao.split()[:max_palavras]).rstrip(",")


def _dica_clima(clima_info: dict[str, Any] | None, idioma: str = IDIOMA_PADRAO) -> str | None:
    """Dica de vestuário/horário a partir da temperatura, no idioma pedido, ou None se não houver dado."""
    if not clima_info or clima_info.get("temperatura_c") is None:
        return None
    temp = float(clima_info["temperatura_c"])
    chave = "dica_calor" if temp >= 30 else "dica_ameno" if temp >= 22 else "dica_frio"
    return textos(idioma)[chave].format(t=round(temp))


def _dados_curados(destino: str) -> dict[str, Any] | None:
    chave = _chave_catalogo(destino)
    return next((d for nome, d in GUIAS_CURADOS.items() if nome in chave or chave in nome), None)


def _locais_contingencia(destino: str, idioma: str) -> list[str]:
    """Locais do guia sem IA: catálogo curado, senão patrimônios conhecidos da cidade, senão genéricos."""
    dados = _dados_curados(destino)
    if dados:
        return [_resumir(p, 6) for p in dados["pontos"]]
    patrimonios = [p for p in identificar_patrimonios(destino) if not p.startswith("BR-")]
    if patrimonios:
        return patrimonios
    return [local.format(cidade=_nome_cidade(destino)) for local in textos(idioma)["locais_genericos"]]


def gerar_guia_contingencia(
    destino: str,
    dias: int = 1,
    clima_info: dict[str, Any] | None = None,
    idioma: str = IDIOMA_PADRAO,
) -> str:
    """Guia determinístico no mesmo formato conciso, usado quando a IA está indisponível.

    Os textos de apoio seguem o idioma pedido; nomes de lugares e pratos ficam no original (patrimônios).
    """
    codigo = normalizar_codigo_idioma(idioma)
    txt = textos(codigo)
    cidade = _nome_cidade(destino)
    dados = _dados_curados(destino)
    locais = _locais_contingencia(destino, codigo)

    if dados:
        pratos = [_resumir(c, 5) for c in dados["culinaria"][:3]]
        onde = txt["prove"].format(pratos=", ".join(pratos)) if codigo != IDIOMA_PADRAO else (
            f"Prove {', '.join(pratos[:-1])} e {pratos[-1]}."
        )
        dica_padrao = f"{_resumir(dados['dica'], 22)}." if codigo == IDIOMA_PADRAO else txt["dica_generica"]
    else:
        onde = txt["gastronomia_generica"]
        dica_padrao = txt["dica_generica"]
    dica = _dica_clima(clima_info, codigo) or dica_padrao

    manha, tarde, noite = txt["turnos"]
    if codigo == IDIOMA_PADRAO:
        if dias == 1:
            roteiro = [f"• Manhã: Visite {locais[0]}.", f"• Tarde: Conheça {locais[1 % len(locais)]}.", f"• Noite: Passeie por {locais[2 % len(locais)]}."]
        else:
            roteiro = [f"• Dia {n}: Explore {locais[(n - 1) % len(locais)]}." for n in range(1, dias + 1)]
    elif dias == 1:
        roteiro = [f"• {turno}: {locais[i % len(locais)]}." for i, turno in enumerate((manha, tarde, noite))]
    else:
        roteiro = [f"• {txt['dia'].format(n=n)}: {locais[(n - 1) % len(locais)]}." for n in range(1, dias + 1)]

    titulo_identidade, titulo_roteiro, titulo_gastronomia, titulo_dica = txt["titulos"]
    return "\n".join(
        [
            f"{titulo_identidade}: {txt['identidade'].format(cidade=cidade)}",
            f"{titulo_roteiro}:",
            *roteiro,
            f"{titulo_gastronomia}: {onde}",
            f"{titulo_dica}: {dica}",
        ]
    )


def _atrativos_do_catalogo(destino: str) -> list[dict[str, Any]]:
    """Atrativos do catálogo curado (id, nome, descrição) para destinos conhecidos; vazio nos demais."""
    chave = _chave_catalogo(destino)
    for nome_chave, dados in GUIAS_CURADOS.items():
        if nome_chave in chave or chave in nome_chave:
            itens = []
            for i, ponto in enumerate(dados["pontos"][:3], start=1):
                nome, _, descricao = ponto.partition(":")
                itens.append({"id": f"atr_{i}", "nome": nome.strip(), "descricao": descricao.strip() or None, "visitado": False})
            return itens
    return []


def _chave_api() -> str:
    """Chave configurada; vazia ou o placeholder do .env.example contam como ausente."""
    chave = (os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY or "").strip()
    return "" if chave in ("", "SUA_CHAVE_AQUI", "SUA_CHAVE_GEMINI_AQUI") else chave


def _modelos() -> list[str]:
    preferido = os.getenv("GEMINI_MODEL", "").strip()
    return [preferido, *MODELOS_PADRAO] if preferido else list(MODELOS_PADRAO)


def _config_rapida(max_tokens: int = 400) -> types.GenerateContentConfig:
    """Configuração de baixa latência: sem raciocínio interno e saída curta (o guia é minimalista)."""
    return types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.7,
        max_output_tokens=max_tokens,
    )


async def _gerar_texto(
    prompt: str | list[dict[str, Any]], config: types.GenerateContentConfig | None = None
) -> tuple[str, str]:
    """Chama o Gemini (resposta completa), tentando os modelos em ordem. Retorna (texto, modelo).

    `prompt` pode ser um texto único ou a lista de turnos (`role` + `parts`) de um diálogo.
    """
    client = genai.Client(api_key=_chave_api())
    ultimo_erro: Exception | None = None
    for modelo in _modelos():
        try:
            resposta = await client.aio.models.generate_content(
                model=modelo, contents=prompt, config=config or _config_rapida()
            )
            if resposta.text:
                return resposta.text, modelo
        except Exception as exc:  # noqa: BLE001 - qualquer falha do SDK deve acionar o próximo modelo/fallback
            ultimo_erro = exc
            logger.warning("Gemini (%s) falhou: %s", modelo, type(exc).__name__)
    raise ultimo_erro or RuntimeError("Nenhum modelo Gemini retornou conteúdo.")


async def gerar_guia_ia_com_diagnostico_async(
    destino: str,
    dias: int,
    estilo: str,
    clima_info: dict[str, Any] | None = None,
    idioma: str = IDIOMA_PADRAO,
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Gera o guia completo e os atrativos no idioma pedido, sem nunca levantar exceção.

    Em ausência de chave, timeout (`TIMEOUT_GEMINI`) ou qualquer falha do provedor, devolve o guia de
    contingência. O terceiro item informa `fallback_utilizado`, `modelo` e `motivo` para o diagnóstico.
    """
    if not _chave_api():
        return (
            gerar_guia_contingencia(destino, dias, clima_info, idioma),
            _atrativos_do_catalogo(destino),
            {"status": "fallback", "fallback_utilizado": True, "modelo": None, "motivo": "Chave GEMINI_API_KEY não configurada"},
        )

    prompt = montar_prompt(destino, dias, estilo, clima_info, incluir_atrativos=True, idioma=idioma)
    try:
        bruto, modelo = await asyncio.wait_for(_gerar_texto(prompt), timeout=settings.TIMEOUT_GEMINI)
    except asyncio.TimeoutError:
        motivo = f"Timeout na chamada ao Gemini (limite de {settings.TIMEOUT_GEMINI:g}s excedido)"
    except Exception as exc:  # noqa: BLE001
        motivo = f"Falha na API Gemini: {type(exc).__name__}"
    else:
        texto, atrativos = extrair_atrativos(preservar_patrimonios(limpar_formato_texto(bruto)))
        if texto:
            return texto, atrativos, {"status": "sucesso", "fallback_utilizado": False, "modelo": modelo, "motivo": None}
        motivo = "Gemini devolveu resposta vazia"

    logger.warning("Guia IA em contingência: %s", motivo)
    return (
        gerar_guia_contingencia(destino, dias, clima_info, idioma),
        _atrativos_do_catalogo(destino),
        {"status": "fallback", "fallback_utilizado": True, "modelo": None, "motivo": motivo},
    )


async def gerar_guia_ia_async(destino: str, dias: int, estilo: str) -> tuple[str, list[dict[str, Any]]]:
    """Interface usada pelo roteador de planejamento: (texto do guia, atrativos). Veja a variante com diagnóstico."""
    texto, atrativos, _ = await gerar_guia_ia_com_diagnostico_async(destino, dias, estilo)
    return texto, atrativos


def _fatiar_em_chunks(texto: str, palavras_por_chunk: int = CHUNK_PALAVRAS_FALLBACK) -> list[str]:
    """Quebra o texto em fragmentos de poucas palavras preservando espaços e quebras de linha."""
    pedacos = re.findall(r"\S+\s*", texto)
    return ["".join(pedacos[i : i + palavras_por_chunk]) for i in range(0, len(pedacos), palavras_por_chunk)]


async def gerar_guia_ia_stream_async(payload: dict[str, Any]) -> AsyncGenerator[str, None]:
    """Gerador assíncrono de fragmentos de texto do guia, consumido pelo endpoint SSE.

    Cada fragmento é emitido assim que o Gemini o produz (cada espera é limitada por `TIMEOUT_GEMINI`). Sem
    chave ou se a falha ocorrer antes do primeiro fragmento, o guia de contingência é emitido em fragmentos
    curtos e imediatos. Falha no meio do fluxo propaga a exceção, que o endpoint converte em evento de erro.
    """
    destino = str(payload.get("destino") or "")
    dias = int(payload.get("dias_estadia") or 1)
    clima_info = payload.get("clima_info") or {}
    idioma = normalizar_codigo_idioma(str(payload.get("idioma") or IDIOMA_PADRAO))

    def contingencia() -> list[str]:
        return _fatiar_em_chunks(gerar_guia_contingencia(destino, dias, clima_info, idioma))

    if not _chave_api():
        for chunk in contingencia():
            yield chunk
        return

    prompt = montar_prompt(
        destino,
        dias,
        str(payload.get("estilo_viagem") or "cultural"),
        clima_info,
        payload.get("atrativos"),
        payload.get("gastronomia"),
        idioma=idioma,
    )
    client = genai.Client(api_key=_chave_api())
    emitiu = False
    ultimo_erro: Exception | None = None

    for modelo in _modelos():
        try:
            stream = await asyncio.wait_for(
                client.aio.models.generate_content_stream(model=modelo, contents=prompt, config=_config_rapida(500)),
                timeout=settings.TIMEOUT_GEMINI,
            )
            iterador = stream.__aiter__()
            while True:
                try:
                    parte = await asyncio.wait_for(iterador.__anext__(), timeout=settings.TIMEOUT_GEMINI)
                except StopAsyncIteration:
                    break
                texto = _limpar_chunk(parte.text or "")
                if texto:
                    emitiu = True
                    yield texto
            if emitiu:
                return
        except Exception as exc:
            ultimo_erro = exc
            logger.warning("Streaming Gemini (%s) falhou: %s", modelo, type(exc).__name__)
            if emitiu:
                raise  # já enviamos parte do guia: não dá para trocar de modelo sem duplicar texto

    logger.warning("Streaming do guia em contingência (%s)", type(ultimo_erro).__name__ if ultimo_erro else "resposta vazia")
    for chunk in contingencia():
        yield chunk


# --------------------------------------------------------------------------- chat multi-turno (V3)

# Histórico máximo enviado ao Gemini (turnos mais recentes), para limitar custo e latência
MAX_TURNOS_HISTORICO = 12
MAX_SUGESTOES = 3

# Ritmo de viagem -> quantidade de atividades por dia no roteiro
ATIVIDADES_POR_RITMO: dict[str, int] = {
    "tranquilo": 2,
    "leve": 2,
    "relaxado": 2,
    "moderado": 3,
    "equilibrado": 3,
    "intenso": 4,
    "acelerado": 4,
}


def atividades_por_dia(ritmo: str) -> int:
    """Atividades diárias para o ritmo informado (moderado = 3 quando o ritmo não é reconhecido)."""
    normalizado = normalizar_texto(ritmo)
    return next((n for chave, n in ATIVIDADES_POR_RITMO.items() if chave in normalizado), 3)


def montar_instrucoes_chat(
    destino: str,
    dias: int,
    estilo: str,
    ritmo_viagem: str,
    acompanhantes: str,
    preferencias_gastronomia: str,
    idioma: str = IDIOMA_PADRAO,
    clima_info: dict[str, Any] | None = None,
    patrimonios: list[str] | None = None,
) -> str:
    """Instrução de sistema do diálogo: contexto da viagem, formato do roteiro, idioma e patrimônios."""
    perfil = PERFIS_VIAJANTE.get(estilo, "Cultural")
    clima = _descrever_clima(clima_info)
    patrimonios = patrimonios if patrimonios is not None else identificar_patrimonios(destino)
    linhas = [
        (
            "Você é um guia de viagem brasileiro conversando com um viajante para construir, turno a turno, "
            "um roteiro personalizado. Considere todo o histórico: quando o viajante pedir um ajuste, devolva o "
            "roteiro completo já ajustado, não apenas a mudança."
        ),
        f"Destino: {destino}. Duração: {dias} dia(s). Perfil: {perfil}.",
        f"Ritmo de viagem: {ritmo_viagem} (no máximo {atividades_por_dia(ritmo_viagem)} atividades por dia, com pausas).",
        f"Acompanhantes: {acompanhantes} (adapte horários, deslocamentos e segurança a eles).",
        f"Preferências gastronômicas: {preferencias_gastronomia} (indique pratos e onde prová-los).",
    ]
    if clima:
        linhas.append(f"Clima atual no destino: {clima}.")
    if patrimonios:
        linhas.append(f"Patrimônios locais relevantes: {', '.join(patrimonios)}.")
    linhas += [
        "",
        "FORMATO (texto puro, sem Markdown, sem saudação nem despedida):",
        "1ª linha: resumo do roteiro em 1 frase.",
        "Depois, uma linha por dia começando com '• ' e o rótulo do dia no idioma da resposta.",
        "Uma linha começando com '🍲' sobre a gastronomia e uma linha começando com '💡' com uma dica prática.",
        (
            f"Última linha, exatamente: SUGESTOES: pergunta 1 | pergunta 2 | pergunta 3 ({MAX_SUGESTOES} perguntas "
            "curtas que o viajante poderia fazer a seguir, no idioma da resposta; a palavra SUGESTOES fica sem tradução)."
        ),
        "",
        instrucao_idioma(idioma, patrimonios),
    ]
    return "\n".join(linhas)


def historico_para_conteudo(historico: list[dict[str, Any]] | None, mensagem: str) -> list[dict[str, Any]]:
    """Converte o histórico do chat (`role` user/assistant + `content`) nos turnos do Gemini (user/model)."""
    turnos: list[dict[str, Any]] = []
    for item in (historico or [])[-MAX_TURNOS_HISTORICO:]:
        texto = str(item.get("content") or "").strip()
        if not texto:
            continue
        papel = "model" if item.get("role") == "assistant" else "user"
        turnos.append({"role": papel, "parts": [{"text": texto}]})
    turnos.append({"role": "user", "parts": [{"text": mensagem.strip()}]})
    return turnos


def extrair_sugestoes(texto: str) -> tuple[str, list[str]]:
    """Separa a linha 'SUGESTOES: a | b | c' da resposta do chat."""
    sugestoes: list[str] = []
    restante: list[str] = []
    for linha in texto.splitlines():
        achado = re.match(r"^\W*SUGEST(?:OES|ÕES)\s*[:：]\s*(.+)$", linha.strip(), flags=re.IGNORECASE)
        if achado:
            sugestoes.extend(s.strip(" .•-") for s in re.split(r"\s*[|｜]\s*", achado.group(1)) if s.strip(" .•-"))
        else:
            restante.append(linha)
    return "\n".join(restante).strip(), sugestoes[:MAX_SUGESTOES]


def gerar_resposta_chat_contingencia(
    destino: str,
    dias: int,
    ritmo_viagem: str,
    acompanhantes: str,
    preferencias_gastronomia: str,
    mensagem: str,
    idioma: str = IDIOMA_PADRAO,
    clima_info: dict[str, Any] | None = None,
    patrimonios: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Roteiro determinístico do chat no idioma pedido (texto, sugestões), usado sem IA disponível.

    Distribui os patrimônios locais (e os pontos do catálogo curado) pelos dias conforme o ritmo, sempre
    com os nomes próprios no original.
    """
    codigo = normalizar_codigo_idioma(idioma)
    txt = textos(codigo)
    patrimonios = patrimonios if patrimonios is not None else identificar_patrimonios(destino, mensagem)
    genericos = [local.format(cidade=_nome_cidade(destino)) for local in txt["locais_genericos"]]
    locais = list(
        dict.fromkeys(
            [*(p for p in patrimonios if not p.startswith("BR-")), *_locais_contingencia(destino, codigo), *genericos]
        )
    )
    por_dia = atividades_por_dia(ritmo_viagem)

    linhas = [txt["chat_intro"].format(destino=destino, dias=dias, ritmo=ritmo_viagem, acompanhantes=acompanhantes)]
    for n in range(dias):
        do_dia = [locais[(n * por_dia + i) % len(locais)] for i in range(min(por_dia, len(locais)))]
        linhas.append(f"• {txt['dia'].format(n=n + 1)}: {' → '.join(do_dia)}")
    linhas.append(f"🍲 {txt['chat_gastronomia'].format(gastronomia=preferencias_gastronomia)}")
    dica = _dica_clima(clima_info, codigo) or txt["dica_generica"]
    pedido = preservar_patrimonios(" ".join(mensagem.split()))[:90]
    linhas.append(f"💡 {dica} {txt['chat_ajuste'].format(pedido=pedido)}" if pedido else f"💡 {dica}")
    return "\n".join(linhas), list(txt["chat_sugestoes"])


def _config_chat(instrucoes: str) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=instrucoes,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.7,
        max_output_tokens=900,
    )


async def conversar_roteiro_ia_async(
    destino: str,
    dias: int,
    estilo: str,
    ritmo_viagem: str,
    acompanhantes: str,
    preferencias_gastronomia: str,
    mensagem: str,
    historico: list[dict[str, Any]] | None = None,
    clima_info: dict[str, Any] | None = None,
    idioma: str = IDIOMA_PADRAO,
) -> dict[str, Any]:
    """Processa um turno do diálogo de construção do roteiro, sem nunca levantar exceção.

    Chamado por `POST /api/v1/roteiros/chat`. Devolve `resposta` (texto exibido no chat),
    `roteiro_personalizado` (o mesmo texto, pronto para o despacho por E-mail/WhatsApp), `idioma`,
    `patrimonios_preservados`, `sugestoes_proximos_passos`, `fallback_utilizado`, `modelo` e `motivo`.
    Sem chave, em timeout ou falha do Gemini, responde com o roteiro determinístico no mesmo idioma.
    """
    codigo = normalizar_codigo_idioma(idioma)
    textos_conversa = [mensagem, *(str(h.get("content") or "") for h in (historico or []))]
    patrimonios = identificar_patrimonios(destino, *textos_conversa)

    def resultado(
        texto: str, sugestoes: list[str], fallback: bool, modelo: str | None, motivo: str | None
    ) -> dict[str, Any]:
        return {
            "resposta": texto,
            "roteiro_personalizado": texto,
            "idioma": codigo,
            "patrimonios_preservados": patrimonios,
            "sugestoes_proximos_passos": sugestoes,
            "fallback_utilizado": fallback,
            "modelo": modelo,
            "motivo": motivo,
        }

    def contingencia(motivo: str) -> dict[str, Any]:
        texto, sugestoes = gerar_resposta_chat_contingencia(
            destino, dias, ritmo_viagem, acompanhantes, preferencias_gastronomia, mensagem, codigo, clima_info, patrimonios
        )
        return resultado(texto, sugestoes, True, None, motivo)

    if not _chave_api():
        return contingencia("Chave GEMINI_API_KEY não configurada")

    instrucoes = montar_instrucoes_chat(
        destino, dias, estilo, ritmo_viagem, acompanhantes, preferencias_gastronomia, codigo, clima_info, patrimonios
    )
    conteudo = historico_para_conteudo(historico, mensagem)
    try:
        bruto, modelo = await asyncio.wait_for(
            _gerar_texto(conteudo, _config_chat(instrucoes)), timeout=settings.TIMEOUT_GEMINI
        )
    except asyncio.TimeoutError:
        motivo = f"Timeout na chamada ao Gemini (limite de {settings.TIMEOUT_GEMINI:g}s excedido)"
    except Exception as exc:  # noqa: BLE001
        motivo = f"Falha na API Gemini: {type(exc).__name__}"
    else:
        texto, sugestoes = extrair_sugestoes(preservar_patrimonios(limpar_formato_texto(bruto)))
        if texto:
            return resultado(texto, sugestoes or list(textos(codigo)["chat_sugestoes"]), False, modelo, None)
        motivo = "Gemini devolveu resposta vazia"

    logger.warning("Chat do roteiro em contingência: %s", motivo)
    return contingencia(motivo)
