"""Testes do chat multi-turno e do suporte multilíngue, sem rede nem chave real do Gemini."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import settings
from app.services import gemini_service
from app.services.gemini_service import (
    atividades_por_dia,
    conversar_roteiro_ia_async,
    extrair_sugestoes,
    gerar_guia_contingencia,
    gerar_guia_ia_com_diagnostico_async,
    gerar_resposta_chat_contingencia,
    historico_para_conteudo,
    montar_instrucoes_chat,
    montar_prompt,
)
from app.services.idiomas import (
    NOMES_IDIOMA,
    TEXTOS,
    identificar_patrimonios,
    normalizar_codigo_idioma,
    preservar_patrimonios,
)

IDIOMAS = tuple(NOMES_IDIOMA)
PATRIMONIOS_PIRIPIRI = ["Parque Nacional de Sete Cidades", "Açude Caldeirão", "BR-343"]

CONTEXTO = {
    "destino": "Piripiri - PI",
    "dias": 2,
    "estilo": "ecoturismo",
    "ritmo_viagem": "tranquilo",
    "acompanhantes": "família com crianças",
    "preferencias_gastronomia": "doces caseiros e cajuína",
}


class ModelosChatFalsos:
    """Imita `client.aio.models`, guardando o que foi enviado ao Gemini."""

    def __init__(self, texto: str = "", erro: Exception | None = None, atraso: float = 0.0) -> None:
        self.texto = texto
        self.erro = erro
        self.atraso = atraso
        self.chamadas: list[dict[str, Any]] = []

    async def generate_content(self, *, model: str, contents: Any, config: Any = None) -> SimpleNamespace:
        self.chamadas.append({"model": model, "contents": contents, "config": config})
        await asyncio.sleep(self.atraso)
        if self.erro:
            raise self.erro
        return SimpleNamespace(text=self.texto)


@pytest.fixture
def chat_falso(monkeypatch: pytest.MonkeyPatch, com_chave_gemini):
    def _instalar(**kwargs: Any) -> ModelosChatFalsos:
        modelos = ModelosChatFalsos(**kwargs)
        monkeypatch.setattr(
            gemini_service.genai, "Client", lambda api_key: SimpleNamespace(aio=SimpleNamespace(models=modelos))
        )
        return modelos

    return _instalar


# --------------------------------------------------------------------------- idiomas e patrimônios


@pytest.mark.parametrize(
    ("entrada", "codigo"),
    [("en-US", "en"), ("pt_BR", "pt"), ("ZH", "zh"), ("ar", "ar"), ("de-DE", "pt"), ("", "pt"), (None, "pt")],
)
def test_normaliza_o_codigo_do_idioma(entrada: str | None, codigo: str) -> None:
    assert normalizar_codigo_idioma(entrada) == codigo


def test_todos_os_idiomas_tem_os_mesmos_textos() -> None:
    chaves = set(TEXTOS["pt"])
    assert set(TEXTOS) == set(IDIOMAS)
    assert all(set(TEXTOS[codigo]) == chaves for codigo in IDIOMAS)


def test_identifica_patrimonios_da_cidade_e_os_citados() -> None:
    assert identificar_patrimonios("Piripiri - PI") == PATRIMONIOS_PIRIPIRI
    # Citado por tradução literal: entra com o nome original e antes dos patrimônios da cidade
    assert identificar_patrimonios("Teresina - PI", "Can we visit the Capybara Mountains?")[0] == "Serra da Capivara"
    assert identificar_patrimonios("Cidade Qualquer - GO") == []


@pytest.mark.parametrize(
    ("traduzido", "original"),
    [
        ("Visit the Seven Cities National Park at dawn.", "Visit Parque Nacional de Sete Cidades at dawn."),
        ("Recorra el Parque Nacional de Siete Ciudades.", "Recorra el Parque Nacional de Sete Cidades."),
        ("Découvrez le Parc national des Sept Villes.", "Découvrez le Parque Nacional de Sete Cidades."),
        ("Посетите Национальный парк Семь городов.", "Посетите Parque Nacional de Sete Cidades."),
        ("参观七城国家公园。", "参观Parque Nacional de Sete Cidades。"),
        ("Boat tour in the parnaiba delta.", "Boat tour in Delta do Parnaíba."),
        ("Climb Sugarloaf Mountain.", "Climb Pão de Açúcar."),
    ],
)
def test_traducoes_literais_voltam_ao_nome_original(traduzido: str, original: str) -> None:
    assert preservar_patrimonios(traduzido) == original


def test_preservar_nao_altera_texto_que_ja_usa_os_nomes_originais() -> None:
    texto = "Day 1: Parque Nacional de Sete Cidades → Açude Caldeirão, via BR-343."
    assert preservar_patrimonios(texto) == texto


# --------------------------------------------------------------------------- prompts


def test_guia_em_portugues_nao_ganha_instrucao_de_idioma() -> None:
    assert "IDIOMA:" not in montar_prompt("Piripiri - PI", 1, "cultural")


@pytest.mark.parametrize("idioma", [c for c in IDIOMAS if c != "pt"])
def test_guia_em_outro_idioma_pede_o_idioma_e_preserva_patrimonios(idioma: str) -> None:
    prompt = montar_prompt("Piripiri - PI", 1, "cultural", idioma=idioma)
    assert NOMES_IDIOMA[idioma] in prompt
    assert '"Parque Nacional de Sete Cidades"' in prompt and '"BR-343"' in prompt


def test_instrucoes_do_chat_incluem_ritmo_acompanhantes_gastronomia_e_idioma() -> None:
    instrucoes = montar_instrucoes_chat(**{k: CONTEXTO[k] for k in CONTEXTO}, idioma="fr", clima_info={"temperatura_c": 33})

    assert "tranquilo (no máximo 2 atividades por dia" in instrucoes
    assert "família com crianças" in instrucoes
    assert "doces caseiros e cajuína" in instrucoes
    assert "33 °C" in instrucoes
    assert NOMES_IDIOMA["fr"] in instrucoes
    assert "Parque Nacional de Sete Cidades" in instrucoes
    assert "SUGESTOES:" in instrucoes


@pytest.mark.parametrize(("ritmo", "n"), [("tranquilo", 2), ("Bem intenso!", 4), ("moderado", 3), ("qualquer", 3)])
def test_atividades_por_dia_seguem_o_ritmo(ritmo: str, n: int) -> None:
    assert atividades_por_dia(ritmo) == n


def test_historico_vira_turnos_user_model_com_a_mensagem_atual_no_fim() -> None:
    historico = [
        {"role": "user", "content": "Quero ir a Piripiri"},
        {"role": "assistant", "content": "Roteiro inicial..."},
        {"role": "user", "content": "   "},
    ]
    turnos = historico_para_conteudo(historico, "Inclua o Açude Caldeirão")

    assert [t["role"] for t in turnos] == ["user", "model", "user"]
    assert turnos[-1]["parts"][0]["text"] == "Inclua o Açude Caldeirão"


def test_historico_longo_e_limitado_aos_turnos_mais_recentes() -> None:
    historico = [{"role": "user", "content": f"msg {i}"} for i in range(40)]
    turnos = historico_para_conteudo(historico, "atual")
    assert len(turnos) == gemini_service.MAX_TURNOS_HISTORICO + 1
    assert turnos[0]["parts"][0]["text"] == "msg 28"


def test_extrai_ate_tres_sugestoes_da_ultima_linha() -> None:
    texto, sugestoes = extrair_sugestoes("• Day 1: Parque Nacional de Sete Cidades\nSUGESTOES: A? | B? | C? | D?")
    assert texto == "• Day 1: Parque Nacional de Sete Cidades"
    assert sugestoes == ["A?", "B?", "C?"]


# --------------------------------------------------------------------------- contingências multilíngues


@pytest.mark.parametrize("idioma", IDIOMAS)
def test_chat_sem_ia_responde_no_idioma_preservando_patrimonios(idioma: str) -> None:
    texto, sugestoes = gerar_resposta_chat_contingencia(
        CONTEXTO["destino"], 2, "tranquilo", "família", "cajuína", "Quero ver o Seven Cities National Park", idioma
    )

    assert texto.splitlines()[0].startswith(TEXTOS[idioma]["chat_intro"].split("{")[0])
    assert "Parque Nacional de Sete Cidades" in texto and "Açude Caldeirão" in texto
    assert "Seven Cities" not in texto
    assert TEXTOS[idioma]["dia"].format(n=2) in texto
    assert sugestoes == list(TEXTOS[idioma]["chat_sugestoes"])


def test_chat_sem_ia_respeita_o_ritmo_por_dia() -> None:
    tranquilo, _ = gerar_resposta_chat_contingencia("Salvador - BA", 1, "tranquilo", "casal", "acarajé", "oi")
    intenso, _ = gerar_resposta_chat_contingencia("Salvador - BA", 1, "intenso", "casal", "acarajé", "oi")

    linha_dia = lambda texto: next(linha for linha in texto.splitlines() if linha.startswith("• "))
    assert linha_dia(tranquilo).count("→") == 1
    assert linha_dia(intenso).count("→") == 3


@pytest.mark.parametrize("idioma", IDIOMAS)
def test_guia_de_contingencia_usa_os_titulos_do_idioma(idioma: str) -> None:
    guia = gerar_guia_contingencia("Piripiri - PI", 1, {"temperatura_c": 34}, idioma)
    for titulo in TEXTOS[idioma]["titulos"]:
        assert titulo in guia
    assert "Parque Nacional de Sete Cidades" in guia


# --------------------------------------------------------------------------- serviço do chat


@pytest.mark.anyio
async def test_chat_sem_chave_usa_contingencia_no_idioma(sem_chave_gemini) -> None:
    resultado = await conversar_roteiro_ia_async(**CONTEXTO, mensagem="Plan a calm trip", idioma="en-US")

    assert resultado["fallback_utilizado"] is True
    assert resultado["idioma"] == "en"
    assert resultado["resposta"].startswith("Itinerary for Piripiri - PI")
    assert resultado["roteiro_personalizado"] == resultado["resposta"]
    assert resultado["patrimonios_preservados"] == PATRIMONIOS_PIRIPIRI


@pytest.mark.anyio
async def test_chat_envia_o_historico_e_as_instrucoes_ao_gemini(chat_falso) -> None:
    modelos = chat_falso(
        texto=(
            "Olá! Aqui está:\n"
            "**Calm two-day trip** in Piripiri.\n"
            "• Day 1: Seven Cities National Park at sunrise.\n"
            "• Day 2: Cauldron Reservoir with the kids.\n"
            "SUGESTOES: Where to eat cajuína? | Rainy day plan? | Fuel on BR-343?"
        )
    )
    historico = [
        {"role": "user", "content": "I want to visit Piripiri"},
        {"role": "assistant", "content": "Great! How many days?"},
    ]

    resultado = await conversar_roteiro_ia_async(**CONTEXTO, mensagem="Two days, calm pace", historico=historico, idioma="en")

    chamada = modelos.chamadas[0]
    assert [t["role"] for t in chamada["contents"]] == ["user", "model", "user"]
    assert "família com crianças" in chamada["config"].system_instruction
    assert NOMES_IDIOMA["en"] in chamada["config"].system_instruction

    assert resultado["fallback_utilizado"] is False
    assert "Parque Nacional de Sete Cidades" in resultado["resposta"]
    assert "Açude Caldeirão" in resultado["resposta"]
    assert "Seven Cities" not in resultado["resposta"] and "**" not in resultado["resposta"]
    assert "SUGESTOES" not in resultado["resposta"]
    assert resultado["sugestoes_proximos_passos"] == ["Where to eat cajuína?", "Rainy day plan?", "Fuel on BR-343?"]


@pytest.mark.anyio
async def test_chat_sem_linha_de_sugestoes_usa_as_padrao_do_idioma(chat_falso) -> None:
    chat_falso(texto="• Día 1: Parque Nacional de Sete Cidades")
    resultado = await conversar_roteiro_ia_async(**CONTEXTO, mensagem="hola", idioma="es")
    assert resultado["sugestoes_proximos_passos"] == list(TEXTOS["es"]["chat_sugestoes"])


@pytest.mark.anyio
@pytest.mark.parametrize("modelos_kwargs", [{"erro": RuntimeError("quota")}, {"texto": ""}])
async def test_chat_com_falha_do_gemini_nao_levanta_e_cai_na_contingencia(chat_falso, modelos_kwargs) -> None:
    chat_falso(**modelos_kwargs)
    resultado = await conversar_roteiro_ia_async(**CONTEXTO, mensagem="привет", idioma="ru")

    assert resultado["fallback_utilizado"] is True
    assert resultado["resposta"].startswith("Маршрут в Piripiri - PI")
    assert resultado["motivo"]


@pytest.mark.anyio
async def test_chat_com_timeout_cai_na_contingencia(monkeypatch: pytest.MonkeyPatch, chat_falso) -> None:
    monkeypatch.setattr(settings, "TIMEOUT_GEMINI", 0.05)
    chat_falso(texto="tarde demais", atraso=1.0)

    resultado = await conversar_roteiro_ia_async(**CONTEXTO, mensagem="oi")
    assert resultado["fallback_utilizado"] is True
    assert "Timeout" in resultado["motivo"]


@pytest.mark.anyio
async def test_guia_com_idioma_restaura_patrimonios_traduzidos(chat_falso) -> None:
    chat_falso(texto="🏛️ IDENTITY: gateway to the Seven Cities National Park.\n📍 ATRATIVOS: Seven Cities National Park")

    texto, atrativos, info = await gerar_guia_ia_com_diagnostico_async("Piripiri - PI", 1, "cultural", idioma="en")

    assert info["fallback_utilizado"] is False
    assert "Parque Nacional de Sete Cidades" in texto
    assert atrativos[0]["nome"] == "Parque Nacional de Sete Cidades"


@pytest.mark.anyio
async def test_guia_sem_chave_usa_contingencia_no_idioma(sem_chave_gemini) -> None:
    texto, _, _ = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural", idioma="es")
    assert texto.startswith("🏛️ IDENTIDAD: Teresina")
