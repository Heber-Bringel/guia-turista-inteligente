"""Cálculo de custos da viagem: combustível ou energia, pedágios, emissões de CO2 e rateio por passageiro."""

from typing import Any

# Emissões diretas aproximadas, em kg de CO2 por litro (combustíveis) ou por kWh (elétrico).
# São valores de referência para estimativa; não substituem inventários oficiais de emissão.
FATOR_EMISSAO_KG_CO2: dict[str, float] = {
    "gasolina": 2.31,
    "combustivel": 2.31,  # tipo genérico do schema: tratado como gasolina
    "hibrido": 2.31,      # o consumo informado (km/L) já reflete a eletrificação
    "etanol": 1.51,
    "diesel": 2.67,
    "eletrico": 0.06,     # média aproximada da matriz elétrica brasileira, kg CO2/kWh
}


async def calcular_custos_async(
    distancia_km: float,
    tipo_veiculo: str,
    consumo: float,
    preco: float,
    passageiros: int,
    pedagios: float = 0.0,
    impacto_relevo_percentual: float = 0.0,
) -> dict[str, Any]:
    """Calcula custo total, rateio e emissões da viagem.

    Unidades: `distancia_km` em km; `consumo` em km/L (combustão) ou km/kWh (elétrico); `preco` em R$/L ou
    R$/kWh; `pedagios` em R$ (valor informado, não estimado); `impacto_relevo_percentual` em % de consumo extra
    causado pelo relevo (vem da altimetria). Valores monetários saem com 2 casas e emissões com 1.

    Regras:
      energia = distancia_km / consumo * (1 + impacto_relevo_percentual / 100)
      combustivel_ou_energia = energia * preco
      total = combustivel_ou_energia + pedagios
      por_passageiro = total / passageiros
      emissoes_kg_co2 = energia * fator do tipo de veículo
    Levanta ValueError para entradas fora do domínio (o roteador trata como falha de custos).
    """
    if distancia_km < 0:
        raise ValueError("Distância não pode ser negativa.")
    if consumo <= 0:
        raise ValueError("Consumo médio deve ser maior que zero.")
    if preco < 0 or pedagios < 0:
        raise ValueError("Preço e pedágios não podem ser negativos.")
    if passageiros < 1:
        raise ValueError("É necessário ao menos 1 passageiro.")

    energia = distancia_km / consumo * (1.0 + max(impacto_relevo_percentual, 0.0) / 100.0)
    custo_energia = energia * preco
    total = custo_energia + pedagios
    fator = FATOR_EMISSAO_KG_CO2.get(tipo_veiculo, FATOR_EMISSAO_KG_CO2["gasolina"])

    return {
        "combustivel_ou_energia": round(custo_energia, 2),
        "pedagios": round(pedagios, 2),
        "total": round(total, 2),
        "por_passageiro": round(total / passageiros, 2),
        "moeda": "BRL",
        "emissoes_kg_co2": round(energia * fator, 1),
    }
