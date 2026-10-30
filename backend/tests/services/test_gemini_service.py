"""Testes do Gemini sem rede nem chave real: prompt, sanitização, fallback, timeout e streaming."""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import settings
from app.services import gemini_service
from app.services.gemini_service import (
    extrair_atrativos,
    gerar_guia_contingencia,
    gerar_guia_ia_async,
    gerar_guia_ia_com_diagnostico_async,
    gerar_guia_ia_stream_async,
    limpar_formato_texto,
    montar_prompt,
)

pytestmark = pytest.mark.anyio

TEXTO_DA_IA = (
    "Olá! Aqui está o seu guia:\n"
    "**🏛️ IDENTIDADE**: Teresina, capital quente do encontro dos rios.\n"
    "🗺️ ROTEIRO:\n"
    "* Manhã: Passeie pelo Encontro dos Rios.\n"
    "📍 ATRATIVOS: Encontro dos Rios; Ponte Estaiada\n"
    "Boa viagem!"
)


class ModelosFalsos:
    """Imita `client.aio.models` do SDK, registrando os modelos tentados."""

    def __init__(
        self,
        texto: str = "",
        erros: dict[str, Exception] | None = None,
        atraso: float = 0.0,
        pedacos: list[str] | None = None,
        erro_no_fluxo: Exception | None = None,
    ) -> None:
        self.texto = texto
        self.erros = erros or {}
        self.atraso = atraso
        self.pedacos = pedacos or []
        self.erro_no_fluxo = erro_no_fluxo
        self.modelos_tentados: list[str] = []

    async def generate_content(self, *, model: str, contents: str, config: Any = None) -> SimpleNamespace:
        self.modelos_tentados.append(model)
        await asyncio.sleep(self.atraso)
        if model in self.erros:
            raise self.erros[model]
        return SimpleNamespace(text=self.texto)

    async def generate_content_stream(self, *, model: str, contents: str, config: Any = None):
        self.modelos_tentados.append(model)
        if model in self.erros:
            raise self.erros[model]

        async def fluxo():
            for pedaco in self.pedacos:
                yield SimpleNamespace(text=pedaco)
            if self.erro_no_fluxo:
                raise self.erro_no_fluxo

        return fluxo()


@pytest.fixture
def modelos_falsos(monkeypatch: pytest.MonkeyPatch, com_chave_gemini):
    """Instala um cliente Gemini falso; devolve uma função que configura o comportamento dos modelos."""

    def _instalar(**kwargs: Any) -> ModelosFalsos:
        modelos = ModelosFalsos(**kwargs)
        monkeypatch.setattr(
            gemini_service.genai, "Client", lambda api_key: SimpleNamespace(aio=SimpleNamespace(models=modelos))
        )
        return modelos

    return _instalar


# --------------------------------------------------------------------------- prompt


def test_prompt_impoe_os_limites_de_concisao_do_enunciado() -> None:
    prompt = montar_prompt("Brasília - DF", 1, "cultural")

    assert "assistente de bordo ágil e ultra-objetivo" in prompt
    assert "até 20 palavras" in prompt  # identidade e atmosfera
    assert "até 15 palavras" in prompt  # cada turno
    assert "• Manhã: / • Tarde: / • Noite:" in prompt
    assert "de 2 a 3 pratos ou sabores" in prompt
    assert "vestuário e aos horários" in prompt
    assert "NENHUM Markdown" in prompt


def test_prompt_de_varios_dias_numera_o_roteiro() -> None:
    prompt = montar_prompt("Brasília - DF", 3, "cultural")

    assert "• Dia 1:" in prompt and "• Dia 3:" in prompt
    assert "Manhã" not in prompt


@pytest.mark.parametrize(
    ("estilo", "perfil"),
    [
        ("cultural", "Cultural"),
        ("gastronomico", "Gastronômico"),
        ("ecoturismo", "Ecoturismo / Aventura"),
        ("aventura", "Ecoturismo / Aventura"),
        ("familia", "Família"),
        ("romantico", "Romântico / Econômico"),
        ("economico", "Romântico / Econômico"),
    ],
)
def test_prompt_traduz_o_estilo_no_perfil_do_viajante(estilo: str, perfil: str) -> None:
    assert f"Perfil do viajante: {perfil}." in montar_prompt("Natal - RN", 2, estilo)


def test_prompt_inclui_clima_atrativos_e_gastronomia_quando_informados() -> None:
    prompt = montar_prompt(
        "Brasília - DF",
        2,
        "cultural",
        clima_info={"temperatura_c": 28.5, "descricao": "Céu limpo", "umidade_percentual": 35, "vento_kmh": 12},
        atrativos=[{"nome": "Catedral Metropolitana"}],
        gastronomia=["Galinhada com pequi"],
    )

    assert "28 °C" in prompt or "29 °C" in prompt
    assert "céu limpo" in prompt and "umidade 35%" in prompt and "vento 12 km/h" in prompt
    assert "Catedral Metropolitana" in prompt
    assert "Galinhada com pequi" in prompt


def test_prompt_so_pede_linha_de_atrativos_quando_solicitado() -> None:
    assert "ATRATIVOS" not in montar_prompt("Natal - RN", 1, "cultural")
    assert "ATRATIVOS" in montar_prompt("Natal - RN", 1, "cultural", incluir_atrativos=True)


# --------------------------------------------------------------------------- sanitização


def test_limpar_formato_remove_markdown_saudacao_e_despedida() -> None:
    sujo = (
        "Olá viajante! Aqui está seu guia completo:\n"
        "# Salvador - Bahia\n"
        "**🏛️ PONTOS TURÍSTICOS PRINCIPAIS**\n"
        "* **Pelourinho**: Centro histórico.\n"
        "- `Farol da Barra`: Pôr do sol.\n\n\n\n"
        "Espero ter ajudado e boa viagem!"
    )

    limpo = limpar_formato_texto(sujo)

    assert "*" not in limpo and "`" not in limpo and "#" not in limpo
    assert "Olá viajante" not in limpo
    assert "boa viagem" not in limpo.lower()
    assert "• Pelourinho: Centro histórico." in limpo
    assert "• Farol da Barra: Pôr do sol." in limpo
    assert "\n\n\n" not in limpo


def test_limpar_formato_de_texto_vazio() -> None:
    assert limpar_formato_texto("") == ""


def test_extrair_atrativos_separa_a_linha_estruturada_do_guia() -> None:
    texto, atrativos = extrair_atrativos("🏛️ IDENTIDADE: X.\n📍 ATRATIVOS: Encontro dos Rios; Ponte Estaiada ; \nFim")

    assert "ATRATIVOS" not in texto and texto.endswith("Fim")
    assert atrativos == [
        {"id": "atr_1", "nome": "Encontro dos Rios", "visitado": False},
        {"id": "atr_2", "nome": "Ponte Estaiada", "visitado": False},
    ]


# --------------------------------------------------------------------------- contingência


def test_contingencia_de_cidade_curada_segue_o_formato_conciso() -> None:
    guia = gerar_guia_contingencia("Teresina - PI")
    linhas = guia.splitlines()

    assert linhas[0].startswith("🏛️ IDENTIDADE: Teresina")
    assert [linha.split(":")[0] for linha in linhas if linha.startswith("•")] == ["• Manhã", "• Tarde", "• Noite"]
    assert any(linha.startswith("🍲 GASTRONOMIA: Prove") for linha in linhas)
    assert any(linha.startswith("💡 DICA PRÁTICA:") for linha in linhas)
    assert "*" not in guia


def test_contingencia_numera_os_dias_quando_ha_mais_de_um() -> None:
    guia = gerar_guia_contingencia("Fortaleza - CE", dias=3)

    assert [linha.split(":")[0] for linha in guia.splitlines() if linha.startswith("•")] == ["• Dia 1", "• Dia 2", "• Dia 3"]


def test_contingencia_de_cidade_desconhecida_e_generica_mas_completa() -> None:
    guia = gerar_guia_contingencia("Pirenópolis - GO")

    assert "Pirenópolis" in guia
    for titulo in ("IDENTIDADE", "ROTEIRO", "GASTRONOMIA", "DICA PRÁTICA"):
        assert titulo in guia


@pytest.mark.parametrize(
    ("temperatura", "trecho"),
    [(34.0, "protetor solar"), (25.0, "agasalho fino"), (15.0, "leve agasalho")],
)
def test_contingencia_ajusta_a_dica_ao_clima(temperatura: float, trecho: str) -> None:
    guia = gerar_guia_contingencia("Natal - RN", clima_info={"temperatura_c": temperatura})
    assert trecho in guia


def test_contingencia_aceita_destino_sem_uf_e_com_acentos() -> None:
    assert "Brasília" in gerar_guia_contingencia("Brasília")


# --------------------------------------------------------------------------- resposta completa


async def test_sem_chave_devolve_contingencia_e_atrativos_do_catalogo(sem_chave_gemini) -> None:
    texto, atrativos, diagnostico = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert texto.startswith("🏛️ IDENTIDADE")
    assert diagnostico["fallback_utilizado"] is True
    assert "não configurada" in diagnostico["motivo"]
    assert atrativos[0]["nome"] == "Parque Ambiental Encontro dos Rios"
    assert all(a["visitado"] is False for a in atrativos)


async def test_placeholder_do_env_example_conta_como_sem_chave(monkeypatch: pytest.MonkeyPatch, sem_chave_gemini) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "SUA_CHAVE_GEMINI_AQUI")

    _, _, diagnostico = await gerar_guia_ia_com_diagnostico_async("Natal - RN", 1, "cultural")

    assert diagnostico["fallback_utilizado"] is True


async def test_interface_do_roteador_devolve_tupla_texto_atrativos(sem_chave_gemini) -> None:
    texto, atrativos = await gerar_guia_ia_async("Natal - RN", 2, "aventura")

    assert isinstance(texto, str) and "Dia 2" in texto
    assert atrativos == []  # Natal não está no catálogo curado


async def test_resposta_da_ia_e_higienizada_e_os_atrativos_extraidos(modelos_falsos) -> None:
    modelos = modelos_falsos(texto=TEXTO_DA_IA)

    texto, atrativos, diagnostico = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert diagnostico == {"status": "sucesso", "fallback_utilizado": False, "modelo": "gemini-2.5-flash", "motivo": None}
    assert modelos.modelos_tentados == ["gemini-2.5-flash"]
    assert "Olá" not in texto and "Boa viagem" not in texto and "*" not in texto and "ATRATIVOS" not in texto
    assert "• Manhã: Passeie pelo Encontro dos Rios." in texto
    assert [a["nome"] for a in atrativos] == ["Encontro dos Rios", "Ponte Estaiada"]


async def test_modelo_da_variavel_de_ambiente_e_tentado_primeiro(monkeypatch: pytest.MonkeyPatch, modelos_falsos) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-modelo-escolhido")
    modelos = modelos_falsos(texto=TEXTO_DA_IA)

    await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert modelos.modelos_tentados == ["gemini-modelo-escolhido"]


async def test_falha_no_primeiro_modelo_tenta_o_proximo(modelos_falsos) -> None:
    modelos = modelos_falsos(texto=TEXTO_DA_IA, erros={"gemini-2.5-flash": RuntimeError("429 cota")})

    _, _, diagnostico = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert modelos.modelos_tentados == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    assert diagnostico["modelo"] == "gemini-2.5-flash-lite" and diagnostico["fallback_utilizado"] is False


async def test_falha_em_todos_os_modelos_aciona_a_contingencia(modelos_falsos) -> None:
    erro = RuntimeError("chave inválida")
    modelos_falsos(erros={"gemini-2.5-flash": erro, "gemini-2.5-flash-lite": erro})

    texto, _, diagnostico = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert texto.startswith("🏛️ IDENTIDADE")
    assert diagnostico["fallback_utilizado"] is True
    assert diagnostico["motivo"] == "Falha na API Gemini: RuntimeError"
    assert "chave inválida" not in diagnostico["motivo"]  # detalhes do provedor não vazam para o diagnóstico


async def test_resposta_vazia_aciona_a_contingencia(modelos_falsos) -> None:
    modelos_falsos(texto="")

    _, _, diagnostico = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert diagnostico["fallback_utilizado"] is True


async def test_timeout_aciona_a_contingencia_sem_esperar_o_provedor(monkeypatch: pytest.MonkeyPatch, modelos_falsos) -> None:
    monkeypatch.setattr(settings, "TIMEOUT_GEMINI", 0.05)
    modelos_falsos(texto=TEXTO_DA_IA, atraso=5.0)

    loop = asyncio.get_running_loop()
    inicio = loop.time()
    _, _, diagnostico = await gerar_guia_ia_com_diagnostico_async("Teresina - PI", 1, "cultural")

    assert loop.time() - inicio < 1.0
    assert diagnostico["fallback_utilizado"] is True
    assert diagnostico["motivo"].startswith("Timeout")


# --------------------------------------------------------------------------- streaming


async def _consumir(payload: dict[str, Any]) -> list[str]:
    return [chunk async for chunk in gerar_guia_ia_stream_async(payload)]


PAYLOAD = {"destino": "Teresina - PI", "dias_estadia": 1, "estilo_viagem": "cultural", "clima_info": {}, "atrativos": []}


async def test_stream_sem_chave_emite_a_contingencia_em_varios_fragmentos(sem_chave_gemini) -> None:
    chunks = await _consumir(PAYLOAD)

    assert len(chunks) > 5
    assert all(chunks)  # nenhum fragmento vazio
    assert "".join(chunks) == gerar_guia_contingencia("Teresina - PI", 1, {})  # sem perder nem duplicar texto


async def test_stream_repassa_os_fragmentos_na_ordem_e_remove_markdown(modelos_falsos) -> None:
    modelos_falsos(pedacos=["🏛️ IDENT", "IDADE: **Teresina**", ", capital", "", " quente `agora`."])

    chunks = await _consumir(PAYLOAD)

    assert chunks == ["🏛️ IDENT", "IDADE: Teresina", ", capital", " quente agora."]


async def test_stream_falha_antes_do_primeiro_fragmento_cai_na_contingencia(modelos_falsos) -> None:
    erro = RuntimeError("503")
    modelos_falsos(erros={"gemini-2.5-flash": erro, "gemini-2.5-flash-lite": erro})

    texto = "".join(await _consumir(PAYLOAD))

    assert texto == gerar_guia_contingencia("Teresina - PI", 1, {})


async def test_stream_falha_antes_do_primeiro_fragmento_tenta_o_proximo_modelo(modelos_falsos) -> None:
    modelos = modelos_falsos(pedacos=["ok"], erros={"gemini-2.5-flash": RuntimeError("429")})

    assert await _consumir(PAYLOAD) == ["ok"]
    assert modelos.modelos_tentados == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


async def test_stream_falha_no_meio_propaga_o_erro_sem_duplicar_texto(modelos_falsos) -> None:
    modelos = modelos_falsos(pedacos=["parte 1"], erro_no_fluxo=ConnectionError("queda"))
    recebidos: list[str] = []

    with pytest.raises(ConnectionError):
        async for chunk in gerar_guia_ia_stream_async(PAYLOAD):
            recebidos.append(chunk)

    assert recebidos == ["parte 1"]
    assert modelos.modelos_tentados == ["gemini-2.5-flash"]  # não trocou de modelo depois de emitir texto


async def test_stream_usa_o_payload_no_prompt(monkeypatch: pytest.MonkeyPatch, modelos_falsos) -> None:
    capturado: dict[str, str] = {}
    modelos = modelos_falsos(pedacos=["ok"])
    original = modelos.generate_content_stream

    async def espiao(*, model: str, contents: str, config: Any = None):
        capturado["prompt"] = contents
        return await original(model=model, contents=contents, config=config)

    monkeypatch.setattr(modelos, "generate_content_stream", espiao)

    await _consumir(
        {**PAYLOAD, "dias_estadia": 3, "estilo_viagem": "familia", "atrativos": [{"nome": "Parque da Cidadania"}], "gastronomia": ["Maria Isabel"]}
    )

    prompt = capturado["prompt"]
    assert "Teresina - PI" in prompt and "3 dia(s)" in prompt and "Família" in prompt
    assert "Parque da Cidadania" in prompt and "Maria Isabel" in prompt
