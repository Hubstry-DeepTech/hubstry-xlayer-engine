"""
Testes unitarios para rateio_proporcional nas duas bases e comparar()
em src/baseline_ons.py.
"""

from __future__ import annotations

import pytest

from src.baseline_ons import Usina, comparar, rateio_proporcional


@pytest.fixture
def usinas_exemplo():
    return [
        Usina("CJU_A", "Conjunto A", disponibilidade_mw=500.0, geracao_mw=420.0),
        Usina("CJU_B", "Conjunto B", disponibilidade_mw=300.0, geracao_mw=280.0),
        Usina("CJU_C", "Conjunto C", disponibilidade_mw=200.0, geracao_mw=60.0),
        Usina("CJU_D", "Conjunto D", disponibilidade_mw=150.0, geracao_mw=140.0),
    ]


def test_rateio_proporcional_base_ponto_de_partida(usinas_exemplo):
    res = rateio_proporcional(usinas_exemplo, 600.0, base="ponto_de_partida")

    assert "6.1" in res.criterio
    assert "ponto de partida" in res.criterio
    assert res.corte_total_mw == pytest.approx(600.0, abs=1e-4)
    assert res.residual_mw == pytest.approx(0.0, abs=1e-4)
    assert res.observacoes == []

    # Soma dos pontos de partida = 420 + 280 + 60 + 140 = 900 MW (fator 2/3)
    assert res.corte_por_usina["CJU_A"] == pytest.approx(280.0, abs=1e-3)
    assert res.corte_por_usina["CJU_B"] == pytest.approx(186.6667, abs=1e-3)
    assert res.corte_por_usina["CJU_C"] == pytest.approx(40.0, abs=1e-3)
    assert res.corte_por_usina["CJU_D"] == pytest.approx(93.3333, abs=1e-3)


def test_rateio_proporcional_ponto_de_partida_respeita_limite_atual():
    usinas = [
        Usina("U1", "Usina 1", disponibilidade_mw=200.0, geracao_mw=150.0, limite_atual_mw=100.0),
        Usina("U2", "Usina 2", disponibilidade_mw=200.0, geracao_mw=100.0, limite_atual_mw=None),
    ]
    # Ponto de partida de U1 = min(150, 100) = 100; U2 = 100 -> pesos iguais
    res = rateio_proporcional(usinas, 80.0, base="ponto_de_partida")
    assert res.corte_por_usina["U1"] == pytest.approx(40.0, abs=1e-4)
    assert res.corte_por_usina["U2"] == pytest.approx(40.0, abs=1e-4)


def test_rateio_proporcional_base_disponibilidade_com_saturacao(usinas_exemplo):
    res = rateio_proporcional(usinas_exemplo, 600.0, base="disponibilidade")

    assert "5.1.2-IV" in res.criterio
    assert "disponibilidade" in res.criterio
    assert res.corte_total_mw == pytest.approx(600.0, abs=1e-4)
    assert res.residual_mw == pytest.approx(0.0, abs=1e-4)

    # CJU_C tem disponibilidade 200 MW mas geracao de apenas 60 MW: satura em 60 MW
    assert res.corte_por_usina["CJU_C"] == pytest.approx(60.0, abs=1e-4)
    # Os 540 MW restantes sao redistribuidos proporcionalmente a 500:300:150 (soma 950)
    assert res.corte_por_usina["CJU_A"] == pytest.approx(540.0 * 500.0 / 950.0, abs=1e-3)
    assert res.corte_por_usina["CJU_B"] == pytest.approx(540.0 * 300.0 / 950.0, abs=1e-3)
    assert res.corte_por_usina["CJU_D"] == pytest.approx(540.0 * 150.0 / 950.0, abs=1e-3)
    assert len(res.observacoes) == 1
    assert "saturaram" in res.observacoes[0]


def test_comparar_usa_ponto_de_partida(usinas_exemplo):
    corte_qubo = {"CJU_A": 250.0, "CJU_B": 200.0, "CJU_C": 50.0, "CJU_D": 100.0}
    precos = {"CJU_A": 300.0, "CJU_B": 300.0, "CJU_C": 300.0, "CJU_D": 300.0}

    df = comparar(usinas_exemplo, 600.0, corte_qubo, precos)
    linha_c = df.loc[df["id_ons"] == "CJU_C"].iloc[0]

    # Pelo ponto de partida (secao 6.1), o baseline de CJU_C e 40.0 MW (e nao 60.0 MW da disponibilidade)
    assert linha_c["corte_baseline_mw"] == pytest.approx(40.0, abs=1e-3)
    assert linha_c["delta_mw"] == pytest.approx(10.0, abs=1e-3)
