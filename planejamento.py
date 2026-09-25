# Módulo de Inteligência Artificial Gemini & Fallback (Guia Turístico e Culinária)

import concurrent.futures
import os
import re
from typing import Any

from google import genai
from google.genai.errors import APIError

from config import GEMINI_KEY

# Modelo oficial especificado para a atividade
MODELO_OFICIAL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# ==============================================================================
# 👤 RESPONSABILIDADE DO ALUNO 2: Inteligência Artificial (Gemini AI) & Fallback
# ==============================================================================


def limpar_formato_texto(texto: str) -> str:
    """Remove marcações residuais de markdown (** ou *), hashtags, crases e saudações, mantendo apenas emojis."""
    if not texto:
        return ""

    # Remove crases de blocos de código e formatação inline
    texto_limpo = texto.replace("```", "").replace("`", "")

    # Converte marcadores de lista markdown (* ou -) em bullets amigáveis (•)
    texto_limpo = re.sub(r"(?m)^[\*\-]\s+", "• ", texto_limpo)

    # Remove marcadores de cabeçalho markdown (# Título, ## Subtítulo)
    texto_limpo = re.sub(r"(?m)^#+\s*", "", texto_limpo)

    # Remove marcações de negrito e itálico (**texto**, *texto*, __texto__)
    texto_limpo = re.sub(r"\*\*([^*]+)\*\*", r"\1", texto_limpo)
    texto_limpo = re.sub(r"\*([^*]+)\*", r"\1", texto_limpo)
    texto_limpo = texto_limpo.replace("**", "").replace("*", "")
    texto_limpo = re.sub(r"__([^_]+)__", r"\1", texto_limpo)

    # Remove saudações conversacionais típicas de LLM na primeira linha
    texto_limpo = re.sub(
        r"(?i)^(olá|ola|com certeza|claro|aqui está|aqui esta|segue|preparado|bem-vindo)[^\n]*\n+",
        "",
        texto_limpo.strip(),
    )

    # Remove despedidas e mensagens de encerramento no final
    texto_limpo = re.sub(
        r"(?i)\n+(espero que aproveite|boa viagem|aproveite sua viagem|espero ter ajudado|qualquer dúvida)[^\n]*$",
        "",
        texto_limpo.strip(),
    )

    # Normaliza múltiplas linhas em branco para espaçamento uniforme
    texto_limpo = re.sub(r"\n{3,}", "\n\n", texto_limpo)

    return texto_limpo.strip()


def gerar_guia_contingencia(destino: str) -> str:
    """Gera roteiro estruturado determinístico em texto puro com emojis em caso de falha da IA."""
    nome_destino = destino.strip() or "Destino Selecionado"
    return (
        f"🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
        f"• Explore os principais cartões-postais e o centro histórico de {nome_destino}.\n"
        f"• Visite os parques naturais, praças centrais e mirantes panorâmicos da região.\n"
        f"• Conheça os museus e monumentos culturais mais emblemáticos da cidade.\n\n"
        f"🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
        f"• Saboreie os pratos típicos regionais e ingredientes tradicionais em mercados locais.\n"
        f"• Experimente as sobremesas clássicas, frutas nativas e bebidas tradicionais.\n"
        f"• Desfrute da hospitalidade nos restaurantes e feiras gastronômicas de {nome_destino}.\n\n"
        f"💡 DICA DE OURO DO VIAJANTE\n"
        f"• Priorize passeios matinais para evitar o calor intenso e filas nas atrações mais populares.\n"
        f"• Mantenha sempre hidratação constante e verifique horários de funcionamento com antecedência."
    )


def _executar_chamada_gemini(destino: str) -> str:
    """Executa a chamada síncrona ao SDK Google GenAI com engenharia de prompt restritiva."""
    client = genai.Client(api_key=GEMINI_KEY)

    prompt = (
        f"Você é um consultor turístico especialista no Brasil. Crie um guia turístico conciso para a cidade de {destino}.\n\n"
        "ESTRUTURA OBRIGATÓRIA:\n"
        "O guia DEVE conter exatamente estas 3 seções, cada uma encabeçada pelo título com emoji indicado:\n"
        "🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
        "(Liste de 2 a 3 atrações imperdíveis com descrições breves)\n\n"
        "🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
        "(Cite 2 pratos ou comidas típicas indispensáveis para provar)\n\n"
        "💡 DICA DE OURO DO VIAJANTE\n"
        "(1 recomendação prática valiosa de melhor horário, transporte ou segredo local)\n\n"
        "REGRAS E RESTRIÇÕES ESTREITAS:\n"
        "- Responda EXCLUSIVAMENTE em texto puro com emojis.\n"
        "- NÃO utilize nenhuma marcação Markdown (NÃO use asteriscos *, nem **, nem hashtags #, nem crases `).\n"
        "- NÃO inclua saudações iniciais (ex: 'Olá', 'Com certeza! Aqui está...') nem despedidas (ex: 'Boa viagem!').\n"
        "- Comece a resposta imediatamente pelo título '🏛️ PONTOS TURÍSTICOS PRINCIPAIS'."
    )

    # Tenta os modelos disponíveis com prioridade
    modelos_para_tentar = [
        MODELO_OFICIAL,
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    ultimo_erro: Exception | None = None
    for modelo in modelos_para_tentar:
        try:
            resposta = client.models.generate_content(
                model=modelo,
                contents=prompt,
            )
            if resposta.text:
                return resposta.text
        except APIError as e:
            ultimo_erro = e
            # Se for chave inválida (código 400), não adianta tentar outros modelos
            if "API key not valid" in str(e) or e.code == 400:
                raise
            continue
        except Exception as e:
            ultimo_erro = e
            raise

    if ultimo_erro:
        raise ultimo_erro

    raise RuntimeError("Nenhum modelo Gemini retornou conteúdo.")


def obter_guia_destino_com_diagnostico(destino: str) -> tuple[str, dict[str, Any]]:
    """Invoca o modelo 'gemini-3.6-flash' com timeout de 6.0s em ThreadPoolExecutor.

    Em caso de timeout, chave inválida ou ausência de cota, aciona automaticamente
    o gerador de contingência com roteiro estruturado em texto puro com emojis.
    Retorna a tupla (texto_guia, diagnostico_metadados).
    """
    # Validação rápida de chave vazia
    if not GEMINI_KEY or GEMINI_KEY.strip() == "" or GEMINI_KEY == "SUA_CHAVE_AQUI":
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico: dict[str, Any] = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": "Chave GEMINI_API_KEY não configurada",
        }
        return guia_contingencia, diagnostico

    # Isolamento com ThreadPoolExecutor para garantir timeout estrito de 6.0s
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_executar_chamada_gemini, destino)
            texto_bruto = future.result(timeout=6.0)

        texto_formatado = limpar_formato_texto(texto_bruto)
        diagnostico = {
            "status": "sucesso",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": False,
        }
        return texto_formatado, diagnostico

    except concurrent.futures.TimeoutError:
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": "Timeout na chamada à API Gemini (limite de 6.0s excedido)",
        }
        return guia_contingencia, diagnostico

    except Exception as erro:  # noqa: BLE001
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": f"Falha na API Gemini: {erro}",
        }
        return guia_contingencia, diagnostico


def obter_guia_destino(destino: str) -> str:
    """Wrapper utilitário que retorna apenas o texto do guia."""
    texto, _ = obter_guia_destino_com_diagnostico(destino)
    return texto
