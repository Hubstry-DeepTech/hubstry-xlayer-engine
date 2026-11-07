"""
Testes para os endpoints FastAPI em main.py (/, /gates e GET /baseline).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_endpoint_root_health_check():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "online", "engine": "X-Layer Core Active"}


def test_endpoint_gates():
    resp = client.get("/gates")
    assert resp.status_code == 200
    dados = resp.json()
    assert "available_modules" in dados
    assert "ons_client" in dados["available_modules"]
    assert "replay_v2" in dados["available_modules"]
    assert "gate31a_analitico" in dados["available_modules"]


def test_endpoint_get_baseline_secao_6_1():
    payload = {
        "usinas": [
            {"id_ons": "CJU_A", "nome": "Conjunto A", "disponibilidade_mw": 500.0, "geracao_mw": 420.0},
            {"id_ons": "CJU_B", "nome": "Conjunto B", "disponibilidade_mw": 300.0, "geracao_mw": 280.0},
            {"id_ons": "CJU_C", "nome": "Conjunto C", "disponibilidade_mw": 200.0, "geracao_mw": 60.0},
            {"id_ons": "CJU_D", "nome": "Conjunto D", "disponibilidade_mw": 150.0, "geracao_mw": 140.0},
        ],
        "corte_necessario_mw": 600.0,
    }
    resp = client.request("GET", "/baseline", json=payload)
    assert resp.status_code == 200

    dados = resp.json()
    assert "6.1" in dados["criterio"]
    assert "ponto de partida" in dados["criterio"]
    assert dados["corte_total_mw"] == pytest.approx(600.0, abs=1e-4)
    assert dados["residual_mw"] == pytest.approx(0.0, abs=1e-4)
    assert dados["observacoes"] == []
    assert dados["corte_por_usina"]["CJU_A"] == pytest.approx(280.0, abs=1e-3)
    assert dados["corte_por_usina"]["CJU_B"] == pytest.approx(186.6667, abs=1e-3)
    assert dados["corte_por_usina"]["CJU_C"] == pytest.approx(40.0, abs=1e-3)
    assert dados["corte_por_usina"]["CJU_D"] == pytest.approx(93.3333, abs=1e-3)


def test_endpoint_get_baseline_validacao_pydantic():
    resp = client.request("GET", "/baseline", json={"usinas": "invalido"})
    assert resp.status_code == 422
