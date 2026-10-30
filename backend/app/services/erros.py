"""Erros compartilhados pelos serviços de dados, com mensagens legíveis para os diagnósticos da API."""

import httpx


class ServicoIndisponivelError(RuntimeError):
    """Provedor externo sem resposta utilizável (timeout, HTTP de erro ou dados inválidos).

    O roteador grava `str(exc)` no diagnóstico do provedor, então a mensagem precisa ser autoexplicativa.
    """


def falha_http(provedor: str, exc: Exception) -> ServicoIndisponivelError:
    """Converte uma exceção do httpx em ServicoIndisponivelError, pois `str(TimeoutException)` costuma vir vazio."""
    if isinstance(exc, httpx.TimeoutException):
        motivo = "tempo limite excedido"
    elif isinstance(exc, httpx.HTTPStatusError):
        motivo = f"HTTP {exc.response.status_code}"
    else:
        motivo = type(exc).__name__
    return ServicoIndisponivelError(f"{provedor} indisponível ({motivo})")
