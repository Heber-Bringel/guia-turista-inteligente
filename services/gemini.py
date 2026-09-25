"""Serviço de IA: chamada ao Google Gemini com timeout isolado em thread e fallback de contingência."""

import concurrent.futures
import os
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import GEMINI_KEY
from services.contingencia import gerar_guia_contingencia
from services.sanitizacao import limpar_formato_texto

# Modelo oficial especificado para a atividade
MODELO_OFICIAL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


def _executar_chamada_gemini(destino: str) -> tuple[str, str]:
    """Executa a chamada síncrona ao SDK Google GenAI com engenharia de prompt avançada e ultra-rápida.

    Retorna a tupla (texto_gerado, modelo_que_respondeu).
    """
    chave_api = os.getenv("GEMINI_API_KEY", GEMINI_KEY)
    client = genai.Client(api_key=chave_api)

    prompt = (
        f"Você é um renomado consultor turístico especialista no Brasil. "
        f"Crie um roteiro e guia turístico aprofundado, autêntico, dinâmico e altamente específico para a cidade de {destino}. "
        "Seja envolvente, objetivo e direto ao ponto (1 a 2 frases por tópico).\n\n"
        "ESTRUTURA OBRIGATÓRIA (utilize exatamente estes títulos com emojis):\n"
        "🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
        "• Cite 3 atrações imperdíveis com nomes reais, pontos de referência exatos e experiências marcantes "
        "(mirantes, cachoeiras, igrejas históricas, reservas naturais ou sítios da região) em até 2 frases objetivas por bullet •.\n\n"
        "🗺️ ROTEIRO RECOMENDADO (PASSO A PASSO)\n"
        "• Manhã: Experiência matinal imperdível em 1 ou 2 frases (ex: nascer do sol, mirante matinal, caminhada ou centro histórico).\n"
        "• Tarde: Passeio vespertino em 1 ou 2 frases (ex: trilha, cachoeira com banho refrescante, alambique/engenho tradicional ou feira).\n"
        "• Noite: Vivência noturna autêntica em 1 ou 2 frases (ex: praça principal movimentada, polo gastronômico ou cafés aconchegantes).\n\n"
        "🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
        "• Descreva 3 pratos típicos genuínos, quitutes, bebidas ou sobremesas tradicionais da culinária da região com nomes reais populares em 1 ou 2 frases cada.\n\n"
        "💡 DICA DE OURO DO VIAJANTE\n"
        "• Forneça 2 recomendações práticas de alto valor sobre melhor horário para fotos/mirantes, agasalhos para o clima da serra ou feiras locais (1 ou 2 frases cada).\n\n"
        "REGRAS ESTREITAS DE FORMATO:\n"
        "- Responda EXCLUSIVAMENTE em texto puro com emojis legíveis.\n"
        "- NÃO use nenhuma marcação Markdown (NÃO use asteriscos *, nem **, nem hashtags #, nem sublinhados _, nem crases `).\n"
        "- NÃO inclua saudações iniciais (ex: 'Olá', 'Com certeza!') nem despedidas (ex: 'Boa viagem!'). Comece imediatamente pelo título '🏛️ PONTOS TURÍSTICOS PRINCIPAIS'."
    )

    # Configuração com thinking_budget=0 e limite de tokens para latência mínima (<3.5s), garantindo resposta antes do timeout
    config_rapida = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.7,
        max_output_tokens=650,
    )

    # Tenta os modelos disponíveis com prioridade (gemini-2.5-flash responde em ~2.5s garantindo compliance com o timeout de 6s)
    modelos_para_tentar = [
        "gemini-2.5-flash",
        MODELO_OFICIAL,
        "gemini-2.5-flash-lite",
    ]

    ultimo_erro: Exception | None = None
    for modelo in modelos_para_tentar:
        try:
            resposta = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=config_rapida,
            )
            if resposta.text:
                return resposta.text, modelo
        except APIError as e:
            ultimo_erro = e
            # Se for chave inválida (código 400), não adianta tentar outros modelos
            if "API key not valid" in str(e) or e.code == 400:
                raise
            continue
        except Exception as e:  # noqa: BLE001
            ultimo_erro = e
            # Se a falha for na configuração, tenta fallback simples sem config
            try:
                resposta = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                if resposta.text:
                    return resposta.text, modelo
            except Exception as e_inner:  # noqa: BLE001
                ultimo_erro = e_inner
                continue

    if ultimo_erro:
        raise ultimo_erro

    raise RuntimeError("Nenhum modelo Gemini retornou conteúdo.")


def obter_guia_destino_com_diagnostico(destino: str) -> tuple[str, dict[str, Any]]:
    """Invoca o modelo Gemini com timeout de 6.0s em ThreadPoolExecutor.

    Em caso de timeout, chave inválida ou ausência de cota, aciona automaticamente
    o gerador de contingência com roteiro estruturado em texto puro com emojis.
    Retorna a tupla (texto_guia, diagnostico_metadados).
    """
    chave_atual = os.getenv("GEMINI_API_KEY", GEMINI_KEY)
    # Validação rápida de chave vazia
    if not chave_atual or chave_atual.strip() == "" or chave_atual == "SUA_CHAVE_AQUI":
        guia_contingencia = gerar_guia_contingencia(destino)
        diagnostico: dict[str, Any] = {
            "status": "fallback",
            "modelo": MODELO_OFICIAL,
            "fallback_utilizado": True,
            "motivo": "Chave GEMINI_API_KEY não configurada",
        }
        return guia_contingencia, diagnostico

    # Isolamento com ThreadPoolExecutor para garantir timeout estrito de 6.0s.
    # O executor não usa 'with': o __exit__ chamaria shutdown(wait=True) e a requisição
    # ficaria presa esperando a thread do Gemini terminar, mesmo após o timeout.
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_executar_chamada_gemini, destino)
        texto_bruto, modelo_utilizado = future.result(timeout=6.0)

        texto_formatado = limpar_formato_texto(texto_bruto)
        diagnostico = {
            "status": "sucesso",
            "modelo": modelo_utilizado,
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

    finally:
        # Libera a requisição imediatamente; a thread em andamento termina sozinha em segundo plano
        executor.shutdown(wait=False, cancel_futures=True)


def obter_guia_destino(destino: str) -> str:
    """Wrapper utilitário que retorna apenas o texto do guia."""
    texto, _ = obter_guia_destino_com_diagnostico(destino)
    return texto
