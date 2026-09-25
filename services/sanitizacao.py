"""Sanitização por regex: remove Markdown, saudações e despedidas das respostas de LLM."""

import re


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
