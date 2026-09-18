# Módulo de Inteligência Artificial para Turismo com Gemini / Fallback

from google import genai

from config import GEMINI_KEY


def obter_guia_destino(destino: str) -> str:
    """Gera guia com pontos turísticos, culinária e dica de ouro usando a IA Gemini."""
    # Utilize a SDK do Google GenAI com a GEMINI_KEY para gerar um guia turístico estruturado com pontos turísticos, culinária local e dica de ouro para o destino informado, fornecendo um texto de fallback caso a IA esteja indisponível.
    return None
