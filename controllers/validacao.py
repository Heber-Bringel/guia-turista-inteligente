"""Sanitização de entradas do usuário (compartilhada pelos controllers)."""

import re


def sanitizar_entrada(texto: str, max_len: int = 80) -> str:
    """Higieniza entradas de texto removendo HTML, caracteres de controle e espaços extras."""
    texto = re.sub(r"<[^>]*>", "", texto)
    texto = re.sub(r"[\x00-\x1F\x7F]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()[:max_len]
