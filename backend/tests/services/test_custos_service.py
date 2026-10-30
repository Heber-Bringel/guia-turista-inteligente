"""Testes dos custos: combustível/energia, pedágios, rateio, emissões e validação das entradas."""

from typing import Any

import pytest

from app.services.custos_service import FATOR_EMISSAO_KG_CO2, calcular_custos_async

pytestmark = pytest.mark.anyio


async def test_gasolina_com_pedagio_e_rateio() -> None:
    # 600 km / 12 km/L = 50 L; 50 L * R$ 6,00 = R$ 300,00
    custos = await calcular_custos_async(600.0, "gasolina", 12.0, 6.0, passageiros=2, pedagios=40.0)

    assert custos == {
        "combustivel_ou_energia": 300.0,
        "pedagios": 40.0,
        "total": 340.0,
        "por_passageiro": 170.0,
        "moeda": "BRL",
        "emissoes_kg_co2": 115.5,  # 50 L * 2,31 kg CO2/L
    }


async def test_impacto_do_relevo_aumenta_energia_custo_e_emissoes() -> None:
    sem_relevo = await calcular_custos_async(600.0, "gasolina", 12.0, 6.0, 1)
    com_relevo = await calcular_custos_async(600.0, "gasolina", 12.0, 6.0, 1, impacto_relevo_percentual=10.0)

    assert com_relevo["combustivel_ou_energia"] == 330.0  # 55 L * R$ 6,00
    assert com_relevo["combustivel_ou_energia"] == pytest.approx(sem_relevo["combustivel_ou_energia"] * 1.10)
    assert com_relevo["emissoes_kg_co2"] > sem_relevo["emissoes_kg_co2"]


async def test_impacto_negativo_e_ignorado() -> None:
    custos = await calcular_custos_async(600.0, "gasolina", 12.0, 6.0, 1, impacto_relevo_percentual=-50.0)
    assert custos["combustivel_ou_energia"] == 300.0


async def test_veiculo_eletrico_usa_kwh_e_fator_proprio() -> None:
    # 300 km / 6 km/kWh = 50 kWh; 50 kWh * R$ 0,90 = R$ 45,00
    custos = await calcular_custos_async(300.0, "eletrico", 6.0, 0.9, 1)

    assert custos["combustivel_ou_energia"] == 45.0
    assert custos["emissoes_kg_co2"] == 3.0  # 50 kWh * 0,06 kg CO2/kWh


@pytest.mark.parametrize(("tipo", "fator"), sorted(FATOR_EMISSAO_KG_CO2.items()))
async def test_cada_tipo_de_veiculo_usa_seu_fator_de_emissao(tipo: str, fator: float) -> None:
    custos = await calcular_custos_async(100.0, tipo, 10.0, 5.0, 1)  # 10 unidades de energia
    assert custos["emissoes_kg_co2"] == round(10.0 * fator, 1)


async def test_tipo_desconhecido_cai_no_fator_da_gasolina() -> None:
    custos = await calcular_custos_async(100.0, "foguete", 10.0, 5.0, 1)
    assert custos["emissoes_kg_co2"] == 23.1


async def test_rateio_arredonda_em_centavos() -> None:
    custos = await calcular_custos_async(100.0, "gasolina", 10.0, 10.0, passageiros=3)  # total R$ 100,00
    assert custos["por_passageiro"] == 33.33


async def test_distancia_zero_custa_apenas_pedagio() -> None:
    custos = await calcular_custos_async(0.0, "gasolina", 10.0, 6.0, 2, pedagios=10.0)
    assert (custos["combustivel_ou_energia"], custos["total"], custos["por_passageiro"]) == (0.0, 10.0, 5.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"distancia_km": -1.0},
        {"consumo": 0.0},
        {"consumo": -3.0},
        {"preco": -1.0},
        {"pedagios": -5.0},
        {"passageiros": 0},
    ],
    ids=["distancia-negativa", "consumo-zero", "consumo-negativo", "preco-negativo", "pedagio-negativo", "sem-passageiros"],
)
async def test_entradas_fora_do_dominio_levantam_value_error(kwargs: dict[str, Any]) -> None:
    base: dict[str, Any] = {
        "distancia_km": 100.0,
        "tipo_veiculo": "gasolina",
        "consumo": 10.0,
        "preco": 6.0,
        "passageiros": 1,
        "pedagios": 0.0,
    }
    with pytest.raises(ValueError):
        await calcular_custos_async(**{**base, **kwargs})
