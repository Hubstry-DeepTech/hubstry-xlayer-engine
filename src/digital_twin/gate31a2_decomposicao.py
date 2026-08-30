"""
Gate 3.1A.2 — Decomposicao da divergencia entre os baselines
============================================================
O QUE ESTE GATE PRECISA ELIMINAR ANTES DE QUALQUER CONCLUSAO
------------------------------------------------------------
O Gate 3.1A.1 mostrou que 60,15% das observacoes de janeiro/2025
produzem divergencia entre os dois baselines normativos, e que a
inconsistencia de disponibilidade explica apenas 19,3% do total.

Antes de tratar os 80,7% restantes como fenomeno normativo, e preciso
descartar uma explicacao trivial: A IMPLEMENTACAO.

O rateio_proporcional e ITERATIVO. Quando uma usina satura o
cabimento (nao pode ser cortada alem da propria geracao), o excedente
e redistribuido entre as demais. Como os dois baselines usam pesos
diferentes, saturam usinas diferentes — e a redistribuicao PROPAGA
divergencia para usinas cujos pesos eram identicos.

Se for isso, os 80,7% sao artefato do algoritmo, nao achado sobre a
norma.

ORDEM DOS TESTES
----------------
TESTE 1 — efeito da redistribuicao
  Rodar os dois baselines em duas versoes:
    (a) sem redistribuicao: corte_i = peso_i / soma(pesos) * total,
        sem tratar saturacao
    (b) com redistribuicao: implementacao atual
  Medir quanto da divergencia desaparece na versao (a).

TESTE 2 — efeito do ponto de partida
  Sobre a versao SEM redistribuicao, isolar a diferenca conceitual
  legitima entre os criterios: o baseline A pesa por
  min(geracao, limite) e o B pesa por disponibilidade. Onde os pesos
  ja diferem, a divergencia e estrutural da norma.

TESTE 3 — perfil cadastral dos ativos inconsistentes
  Os 26 ativos com disponibilidade nula e geracao positiva tem
  modalidade, submercado ou estado em comum? Concentracao cadastral
  explicaria recorrencia sem pressupor erro de preenchimento.

SO DEPOIS
---------
Se os tres testes nao explicarem o total, abrir as demais categorias.
A decomposicao pretendida e:

  divergencia observada
    -> efeito da implementacao
    -> efeito da regra matematica
    -> efeito da qualidade dos dados
    -> residual ainda nao explicado

O QUE ESTE GATE NAO AFIRMA
--------------------------
Que disponibilidade nula com geracao positiva e erro. E inconsistencia
entre campos publicados. A causa permanece aberta.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from . import gate31_persistencia as g31
except ImportError:
    import gate31_persistencia as g31

PASSO_HORAS = 0.5


# ----------------------------------------------------------------------
# Rateio sem redistribuicao — proporcional puro
# ----------------------------------------------------------------------

def rateio_puro(pesos: np.ndarray, total: float) -> np.ndarray:
    """
    corte_i = peso_i / soma(pesos) * total

    Sem tratar saturacao. Pode atribuir a uma usina corte maior que a
    propria geracao — o que e fisicamente impossivel, e exatamente por
    isso a implementacao real redistribui. Aqui o objetivo e ISOLAR o
    efeito dessa redistribuicao, nao produzir alocacao valida.
    """
    s = pesos.sum()
    if s <= 1e-9:
        return np.zeros_like(pesos)
    return pesos / s * total


def rateio_com_redistribuicao(pesos: np.ndarray, cabimento: np.ndarray,
                              total: float) -> np.ndarray:
    """Mesma logica de baseline_ons.rateio_proporcional, vetorizada."""
    cortes = np.zeros_like(pesos, dtype=float)
    ativos = (cabimento > 1e-9) & (pesos > 1e-9)
    restante = total
    for _ in range(len(pesos) + 5):
        if restante <= 1e-6 or not ativos.any():
            break
        s = pesos[ativos].sum()
        if s <= 1e-9:
            break
        parcela = np.zeros_like(cortes)
        parcela[ativos] = restante * pesos[ativos] / s
        livre = cabimento - cortes
        satura = ativos & (parcela >= livre - 1e-9)
        cortes[satura] = cabimento[satura]
        nao = ativos & ~satura
        cortes[nao] += parcela[nao]
        restante = total - cortes.sum()
        ativos = ativos & ~satura
    return cortes


def divergencias_do_patamar(g: pd.DataFrame) -> Dict[str, float]:
    """Calcula a divergencia A-B nas duas versoes, para um patamar."""
    ger = g["val_geracao"].to_numpy(float)
    disp = np.nan_to_num(g["val_disponibilidade"].to_numpy(float))
    lim = np.nan_to_num(g["val_geracaolimitada"].to_numpy(float))
    total = float(g["corte_mw"].sum())

    peso_a = np.minimum(ger, lim)          # ponto de partida (NT 6.1)
    peso_b = disp                           # disponibilidade (NT 5.1.2-IV)

    a_puro = rateio_puro(peso_a, total)
    b_puro = rateio_puro(peso_b, total)
    a_red = rateio_com_redistribuicao(peso_a, ger, total)
    b_red = rateio_com_redistribuicao(peso_b, ger, total)

    # pesos identicos: nenhuma divergencia estrutural esperada
    pesos_iguais = np.isclose(peso_a, peso_b, rtol=1e-6, atol=1e-6)

    return {
        "n": len(g),
        "div_puro": float(np.abs(a_puro - b_puro).sum()),
        "div_red": float(np.abs(a_red - b_red).sum()),
        "n_div_puro": int((np.abs(a_puro - b_puro) > 0.01).sum()),
        "n_div_red": int((np.abs(a_red - b_red) > 0.01).sum()),
        "n_pesos_iguais": int(pesos_iguais.sum()),
        # divergencia em usinas cujos pesos sao IDENTICOS: so pode vir
        # da redistribuicao
        "div_red_pesos_iguais": float(
            np.abs(a_red - b_red)[pesos_iguais].sum()),
        "div_puro_pesos_iguais": float(
            np.abs(a_puro - b_puro)[pesos_iguais].sum()),
    }


# ----------------------------------------------------------------------

if __name__ == "__main__":
    ANO, MES = 2025, 1
    print(f"Carregando COFF eolica {ANO}-{MES:02d}...")
    df = g31.calcular_corte(g31.carregar(ANO, MES))
    df["disp_zero_ger_positiva"] = (
        (df["val_disponibilidade"].fillna(-1) == 0) & (df["val_geracao"] > 0))

    print("\n" + "=" * 72)
    print("TESTE 1 — EFEITO DA REDISTRIBUICAO")
    print("=" * 72)
    print("  Rodando os dois baselines com e sem redistribuicao...")

    linhas = []
    for t, g in df.groupby("din_instante", sort=True):
        if len(g) < 2:
            continue
        linhas.append(divergencias_do_patamar(g))
    r = pd.DataFrame(linhas)

    dp, dr = r["div_puro"].sum(), r["div_red"].sum()
    print(f"\n  patamares avaliados .............. {len(r):,}")
    print(f"  observacoes ...................... {int(r['n'].sum()):,}")
    print()
    print(f"  divergencia SEM redistribuicao ... {dp:12,.1f} MW")
    print(f"  divergencia COM redistribuicao ... {dr:12,.1f} MW")
    if dr > 0:
        print(f"  atribuivel a redistribuicao ...... {(dr - dp)/dr*100:11.1f}%")
    print()
    print(f"  obs. divergentes SEM ............. {int(r['n_div_puro'].sum()):,}")
    print(f"  obs. divergentes COM ............. {int(r['n_div_red'].sum()):,}")

    print("\n  --- Prova direta: usinas com PESOS IDENTICOS ---")
    print("  Se os pesos de A e B sao iguais, qualquer divergencia so pode")
    print("  vir da redistribuicao.")
    print(f"    observacoes com pesos identicos . {int(r['n_pesos_iguais'].sum()):,}")
    print(f"    divergencia delas, SEM redistrib. {r['div_puro_pesos_iguais'].sum():10,.1f} MW")
    print(f"    divergencia delas, COM redistrib. {r['div_red_pesos_iguais'].sum():10,.1f} MW")
    if dr > 0:
        print(f"    -> {r['div_red_pesos_iguais'].sum()/dr*100:.1f}% da divergencia total")

    print("\n  --- Leitura do Teste 1 ---")
    if dr > 0 and (dr - dp) / dr > 0.5:
        print("  A REDISTRIBUICAO EXPLICA A MAIOR PARTE. Os 80,7% do Gate")
        print("  3.1A.1 sao, em boa medida, artefato da implementacao")
        print("  iterativa — nao achado sobre a norma. O resultado do A.1")
        print("  precisa ser reformulado.")
    else:
        print("  A REDISTRIBUICAO NAO EXPLICA A MAIOR PARTE. A divergencia")
        print("  persiste sem ela, o que aponta para diferenca estrutural")
        print("  entre os criterios normativos.")

    print("\n" + "=" * 72)
    print("TESTE 2 — EFEITO DO PONTO DE PARTIDA (sobre rateio puro)")
    print("=" * 72)
    print("  Baseline A pesa por min(geracao, limite); B pesa por")
    print("  disponibilidade. Onde os pesos ja diferem, a divergencia e")
    print("  estrutural da norma, nao da implementacao.\n")

    d = df.copy()
    d["peso_a"] = np.minimum(d["val_geracao"].fillna(0),
                             d["val_geracaolimitada"].fillna(0))
    d["peso_b"] = d["val_disponibilidade"].fillna(0)
    d["pesos_diferem"] = ~np.isclose(d["peso_a"], d["peso_b"],
                                     rtol=1e-6, atol=1e-6)

    print(f"  observacoes ...................... {len(d):,}")
    print(f"  com pesos diferentes ............. {int(d['pesos_diferem'].sum()):,} "
          f"({d['pesos_diferem'].mean()*100:.1f}%)")

    cat = pd.cut(
        (d["peso_a"] - d["peso_b"]).abs(),
        bins=[-0.001, 0.01, 1, 10, 100, 1e9],
        labels=["identicos", "< 1 MW", "1-10 MW", "10-100 MW", "> 100 MW"],
    )
    tab = pd.DataFrame({"observacoes": cat.value_counts().sort_index()})
    tab["pct"] = (tab["observacoes"] / len(d) * 100).round(1)
    print("\n  distribuicao da diferenca entre pesos:")
    print(tab.to_string())

    print("\n  por condicao de disponibilidade:")
    t2 = d.groupby("disp_zero_ger_positiva").agg(
        obs=("pesos_diferem", "size"),
        pesos_diferem=("pesos_diferem", "sum"),
    )
    t2["pct"] = (t2["pesos_diferem"] / t2["obs"] * 100).round(1)
    print(t2.to_string())

    print("\n" + "=" * 72)
    print("TESTE 3 — PERFIL CADASTRAL DOS ATIVOS INCONSISTENTES")
    print("=" * 72)
    afetados = set(d[d["disp_zero_ger_positiva"]]["id_ons"])
    d["ativo_afetado"] = d["id_ons"].isin(afetados)
    print(f"  ativos com ao menos uma inconsistencia: {len(afetados)} "
          f"de {d['id_ons'].nunique()}\n")

    for col in ("id_subsistema", "id_estado", "nom_modalidadeoperacao"):
        if col not in d.columns:
            continue
        base = d.drop_duplicates("id_ons")
        t = pd.crosstab(base[col], base["ativo_afetado"])
        if True in t.columns and False in t.columns:
            t["pct_afetados"] = (t[True] / (t[True] + t[False]) * 100).round(1)
        print(f"  --- {col} ---")
        print(t.to_string())
        print()

    print("  Concentracao em uma modalidade ou submercado explicaria a")
    print("  recorrencia sem pressupor erro de preenchimento. Distribuicao")
    print("  uniforme afastaria a hipotese cadastral.")

    print("\n" + "=" * 72)
    print("SINTESE")
    print("=" * 72)
    print(f"  divergencia total (com redistribuicao) ... {dr:12,.1f} MW")
    print(f"  atribuivel a redistribuicao ............. {max(dr-dp,0):12,.1f} MW")
    print(f"  remanescente (estrutural + dados) ....... {min(dp,dr):12,.1f} MW")
    print()
    print("  Este gate NAO estabelece a causa da disponibilidade nula.")
    print("  Inconsistencia entre campos publicados esta demonstrada; a")
    print("  origem — semantica, defasagem, apuracao ou preenchimento —")
    print("  permanece aberta.")
