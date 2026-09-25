"""Script de Testes Automatizados para a parte do Douglas Leone (Aluno 2).

Testa:
1. Telemetria de Clima (Open-Meteo) com coordenadas reais e fallback (0.0, 0.0)
2. Roteamento Rodoviário (OSRM) com trajeto regular (km e duração)
3. Roteamento Rodoviário OSRM para ilhas sem estrada (Fernando de Noronha - PE) [TESTE 5 DO PROFESSOR]
4. Sanitização Regex (limpeza de Markdown, saudações e despedidas de LLM)
5. Fallback da IA Gemini com chave inválida ('CHAVE_INVALIDA') sem erro 500 [TESTE 2 DO PROFESSOR]
"""

import os
import sys
import httpx

import config
import planejamento
from services import obter_clima, obter_percurso
from planejamento import limpar_formato_texto, obter_guia_destino_com_diagnostico


def testar_clima():
    print("=" * 70)
    print("🌤️ 1. TESTE DE TELEMETRIA CLIMÁTICA (Open-Meteo Weather)")
    print("=" * 70)

    with httpx.Client() as client:
        # Cenário A: Coordenadas reais de Brasília
        clima_bsb = obter_clima(client, -15.779, -47.929)
        print(f"✅ Brasília (-15.779, -47.929): {clima_bsb}")
        assert "°C" in clima_bsb["temperatura"], "Temperatura deve conter unidade °C"
        assert "%" in clima_bsb["umidade"], "Umidade deve conter unidade %"
        assert "km/h" in clima_bsb["vento"], "Vento deve conter unidade km/h"

        # Cenário B: Coordenadas nulas (fallback)
        clima_null = obter_clima(client, 0.0, 0.0)
        print(f"✅ Coordenadas Zeradas (0.0, 0.0) -> Fallback: {clima_null}")
        assert clima_null["temperatura"] == "N/D"
        assert clima_null["umidade"] == "N/D"
        assert clima_null["vento"] == "N/D"


def testar_percurso():
    print("\n" + "=" * 70)
    print("🚗 2. TESTE DE ROTEAMENTO RODOVIÁRIO (OSRM)")
    print("=" * 70)

    with httpx.Client() as client:
        # Cenário A: Teresina -> Brasília
        percurso_bsb = obter_percurso(client, -5.089, -42.801, -15.779, -47.929)
        print(f"✅ Trajeto Teresina -> Brasília: {percurso_bsb}")
        assert "km" in percurso_bsb["distancia"], "Distância deve estar em km"
        assert "de carro" in percurso_bsb["tempo"], "Tempo deve conter 'de carro'"
        assert percurso_bsb["modal"] == "carro"

        # Cenário B: Destino em ilha sem estrada (Fernando de Noronha - PE) [TESTE 5 DO PROFESSOR]
        # Origem: Recife (-8.054, -34.881) -> Destino: Fernando de Noronha (-3.840, -32.410)
        percurso_ilha = obter_percurso(client, -8.054, -34.881, -3.840, -32.410)
        print(f"✅ [TESTE 5 PROFESSOR] Recife -> Fernando de Noronha (Ilha): {percurso_ilha}")
        assert percurso_ilha["distancia"] == "Sem rota direta", "Ilhas devem retornar 'Sem rota direta'"
        assert percurso_ilha["tempo"] == "Considere voos ou barcos", "Ilhas devem sugerir voos ou barcos"


def testar_sanitizacao_regex():
    print("\n" + "=" * 70)
    print("🧹 3. TESTE DE SANITIZAÇÃO REGEX (limpar_formato_texto)")
    print("=" * 70)

    texto_sujo = (
        "Olá viajante! Aqui está seu guia completo para sua viagem:\n"
        "# Salvador - Bahia\n"
        "**🏛️ PONTOS TURÍSTICOS PRINCIPAIS**\n"
        "* **Pelourinho**: Centro histórico com casarões coloniais.\n"
        "* **Farol da Barra**: Ponto clássico para ver o pôr do sol.\n\n"
        "## 🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
        "- **Acarajé**: Bolinho frito no azeite de dendê.\n"
        "- **Moqueca Baiana**: Prato tradicional com peixe fresco.\n\n"
        "### 💡 DICA DE OURO DO VIAJANTE\n"
        "Use roupas leves e mantenha-se hidratado.\n"
        "Espero ter ajudado e boa viagem!"
    )

    texto_limpo = limpar_formato_texto(texto_sujo)
    print("Texto higienizado:")
    print("-" * 50)
    print(texto_limpo)
    print("-" * 50)

    assert "**" not in texto_limpo, "Não deve conter asteriscos de negrito"
    assert "Olá viajante" not in texto_limpo, "Saudação inicial deve ser removida"
    assert "boa viagem" not in texto_limpo.lower(), "Despedida final deve ser removida"
    assert "• Pelourinho" in texto_limpo, "Marcadores de lista devem ser convertidos para bullet (•)"
    print("✅ Sanitização Regex validada com sucesso!")


def testar_fallback_gemini():
    print("\n" + "=" * 70)
    print("🤖 4. TESTE DO FALLBACK DA IA GEMINI [TESTE 2 DO PROFESSOR]")
    print("=" * 70)

    # Simula a ação ao vivo do professor: export GEMINI_API_KEY="CHAVE_INVALIDA"
    os.environ["GEMINI_API_KEY"] = "CHAVE_INVALIDA"
    config.GEMINI_KEY = "CHAVE_INVALIDA"
    planejamento.GEMINI_KEY = "CHAVE_INVALIDA"

    print("Simulando execução com GEMINI_API_KEY='CHAVE_INVALIDA'...")
    guia, diag = obter_guia_destino_com_diagnostico("Florianópolis - SC")

    print(f"✅ Status do Diagnóstico: {diag.get('status')}")
    print(f"✅ Fallback Utilizado: {diag.get('fallback_utilizado')}")
    print(f"✅ Modelo Informado: {diag.get('modelo')}")
    print(f"✅ Motivo Capturado: {diag.get('motivo')[:80]}...")
    print("\nGuia de Contingência Estruturado Gerado:")
    print("-" * 50)
    print(guia)
    print("-" * 50)

    assert diag["fallback_utilizado"] is True, "Fallback deve estar ativo"
    assert diag["status"] == "fallback", "Status deve ser fallback"
    assert "🏛️ PONTOS TURÍSTICOS PRINCIPAIS" in guia, "Deve conter a seção de pontos turísticos"
    assert "🍲 CULINÁRIA LOCAL & GASTRONOMIA" in guia, "Deve conter a seção de culinária"
    assert "💡 DICA DE OURO DO VIAJANTE" in guia, "Deve conter a seção de dica de ouro"
    print("✅ Teste 2 do professor (Fallback da IA) aprovado com sucesso sem erro 500!")


if __name__ == "__main__":
    try:
        testar_clima()
        testar_percurso()
        testar_sanitizacao_regex()
        testar_fallback_gemini()
        print("\n" + "🎉" * 25)
        print("TODOS OS TESTES DO DOUGLAS (ALUNO 2) PASSARAM COM SUCESSO!")
        print("🎉" * 25)
    except AssertionError as e:
        print(f"\n❌ Falha no teste: {e}")
        sys.exit(1)
