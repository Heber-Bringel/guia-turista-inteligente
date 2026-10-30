"""Serviço de IA: guia turístico conciso via Google Gemini (resposta completa e streaming) com fallback."""

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
) -> str:
    """Monta o prompt do 'assistente de bordo' com os limites de concisão do enunciado.

    Para 1 dia o roteiro usa Manhã/Tarde/Noite; para mais dias, uma linha por dia numerado.
    Com `incluir_atrativos`, pede uma última linha 'ATRATIVOS: a; b; c' que o serviço extrai do texto.
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
    return "\n".join(linhas)


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


def _dica_clima(clima_info: dict[str, Any] | None) -> str | None:
    """Dica de vestuário/horário a partir da temperatura, ou None se não houver dado."""
    if not clima_info or clima_info.get("temperatura_c") is None:
        return None
    temp = float(clima_info["temperatura_c"])
    if temp >= 30:
        return f"Com {round(temp)} °C, use roupa leve e protetor solar e passeie cedo ou ao fim da tarde."
    if temp >= 22:
        return f"Com {round(temp)} °C, roupa leve resolve; leve um agasalho fino para a noite."
    return f"Com {round(temp)} °C, leve agasalho e deixe os passeios ao ar livre para o meio do dia."


def gerar_guia_contingencia(destino: str, dias: int = 1, clima_info: dict[str, Any] | None = None) -> str:
    """Guia determinístico no mesmo formato conciso, usado quando a IA está indisponível."""
    cidade = _nome_cidade(destino)
    dados = next(
        (d for chave, d in GUIAS_CURADOS.items() if chave in _chave_catalogo(destino) or _chave_catalogo(destino) in chave),
        None,
    )

    if dados:
        locais = [_resumir(p, 6) for p in dados["pontos"]]
        pratos = [_resumir(c, 5) for c in dados["culinaria"][:3]]
        onde = f"Prove {', '.join(pratos[:-1])} e {pratos[-1]}."
        dica = _dica_clima(clima_info) or f"{_resumir(dados['dica'], 22)}."
    else:
        locais = [f"o centro histórico de {cidade}", "os parques e mirantes da região", "o mercado e a feira locais"]
        onde = "Prove a culinária regional em restaurantes de comida caseira e feiras da cidade."
        dica = _dica_clima(clima_info) or "Passeie ao ar livre nas primeiras horas da manhã, com temperaturas mais amenas."

    if dias == 1:
        roteiro = [f"• Manhã: Visite {locais[0]}.", f"• Tarde: Conheça {locais[1 % len(locais)]}.", f"• Noite: Passeie por {locais[2 % len(locais)]}."]
    else:
        roteiro = [f"• Dia {n}: Explore {locais[(n - 1) % len(locais)]}." for n in range(1, dias + 1)]

    return "\n".join(
        [
            f"{TITULO_IDENTIDADE}: {cidade}, destino de cultura, sabores e paisagens marcantes do Brasil.",
            f"{TITULO_ROTEIRO}:",
            *roteiro,
            f"{TITULO_GASTRONOMIA}: {onde}",
            f"{TITULO_DICA}: {dica}",
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


async def _gerar_texto(prompt: str) -> tuple[str, str]:
    """Chama o Gemini (resposta completa), tentando os modelos em ordem. Retorna (texto, modelo)."""
    client = genai.Client(api_key=_chave_api())
    ultimo_erro: Exception | None = None
    for modelo in _modelos():
        try:
            resposta = await client.aio.models.generate_content(model=modelo, contents=prompt, config=_config_rapida())
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
) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """Gera o guia completo e os atrativos, sem nunca levantar exceção.

    Em ausência de chave, timeout (`TIMEOUT_GEMINI`) ou qualquer falha do provedor, devolve o guia de
    contingência. O terceiro item informa `fallback_utilizado`, `modelo` e `motivo` para o diagnóstico.
    """
    if not _chave_api():
        return (
            gerar_guia_contingencia(destino, dias, clima_info),
            _atrativos_do_catalogo(destino),
            {"status": "fallback", "fallback_utilizado": True, "modelo": None, "motivo": "Chave GEMINI_API_KEY não configurada"},
        )

    prompt = montar_prompt(destino, dias, estilo, clima_info, incluir_atrativos=True)
    try:
        bruto, modelo = await asyncio.wait_for(_gerar_texto(prompt), timeout=settings.TIMEOUT_GEMINI)
    except asyncio.TimeoutError:
        motivo = f"Timeout na chamada ao Gemini (limite de {settings.TIMEOUT_GEMINI:g}s excedido)"
    except Exception as exc:  # noqa: BLE001
        motivo = f"Falha na API Gemini: {type(exc).__name__}"
    else:
        texto, atrativos = extrair_atrativos(limpar_formato_texto(bruto))
        if texto:
            return texto, atrativos, {"status": "sucesso", "fallback_utilizado": False, "modelo": modelo, "motivo": None}
        motivo = "Gemini devolveu resposta vazia"

    logger.warning("Guia IA em contingência: %s", motivo)
    return (
        gerar_guia_contingencia(destino, dias, clima_info),
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

    def contingencia() -> list[str]:
        return _fatiar_em_chunks(gerar_guia_contingencia(destino, dias, clima_info))

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
