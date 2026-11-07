"""
Analise Gate 3.1A e Persistencia por Razao de Restricao (Janeiro de 2025)
=========================================================================
Script reprodutivel para sustentar o relatorio `docs/analises/gate31a-razao-01.md`.

Escopo da analise (sem alterar arquivos de `src/` nem `docs/`):
  1. Reproduzir o instante do Gate 3.1A (`escolher_instante` em
     `src/digital_twin/gate31a_analitico.py`) e verificar se
     `usinas_do_instante()` mistura conjuntos com `cod_razaorestricao`
     diferente de `ENE`. Reportar quantos conjuntos de cada razao entram e
     o impacto no total de MWh e no rateio da secao 6.1 se o filtro `ENE`
     for aplicado (no instante do Gate 3.1A e nos demais patamares com `ENE`
     do mes).
  2. Recalcular a duracao dos episodios de janeiro de 2025 a partir so da
     ocorrencia de restricao declarada por razao (`cod_razaorestricao`
     preenchido), sem usar `corte_mw > 0`. Comparar com os "9 a 11,5 horas"
     e os "mais de 130 conjuntos simultaneos" do `README.md`.
  3. Separar sempre `ENE`, `REL`, `CNF` e `PAR`, informando os denominadores
     com e sem quarentena.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from baseline_ons import Usina, rateio_proporcional
from digital_twin import gate31_persistencia as g31
from digital_twin import gate31a_analitico as g31a
from digital_twin import gate31a2_decomposicao as g31a2

PASSO = pd.Timedelta(minutes=30)
PASSO_HORAS = 0.5
RAZOES_ORDEM = ["ENE", "REL", "CNF", "PAR"]


def preparar_base_completa(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara o DataFrame mantendo todas as linhas com `cod_razaorestricao`
    preenchido e marcando quarentena (`corte_mw_bruto < -1e-6`), corte zero
    (`-1e-6 <= corte_mw_bruto <= 0`) e corte estritamente positivo (`> 0`).
    """
    df = df_raw[df_raw["cod_razaorestricao"].notna()].copy()
    df = df.dropna(subset=["val_geracaolimitada", "val_geracao"]).copy()
    df["corte_mw_bruto"] = df["val_geracaolimitada"] - df["val_geracao"]
    df["em_quarentena"] = df["corte_mw_bruto"] < -1e-6
    df["corte_zero"] = (~df["em_quarentena"]) & (df["corte_mw_bruto"] <= 0.0)
    df["corte_pos"] = df["corte_mw_bruto"] > 0.0
    df["corte_mw_pos"] = df["corte_mw_bruto"].clip(lower=0.0)
    df["corte_mwh_pos"] = df["corte_mw_pos"] * PASSO_HORAS
    df["corte_mwh_bruto"] = df["corte_mw_bruto"] * PASSO_HORAS
    return df


def tabela_denominadores(df_restr: pd.DataFrame, total_linhas_raw: int) -> pd.DataFrame:
    """Constroi tabela de denominadores por razao (ENE, REL, CNF, PAR e TODAS)."""
    linhas = []
    for r in RAZOES_ORDEM + ["TODAS"]:
        sub = df_restr if r == "TODAS" else df_restr[df_restr["cod_razaorestricao"] == r]
        n_sem_q = len(sub)
        n_quar = int(sub["em_quarentena"].sum())
        n_com_q = int((~sub["em_quarentena"]).sum())
        n_zero = int(sub["corte_zero"].sum())
        n_pos = int(sub["corte_pos"].sum())

        sis_sem_q = int((sub["cod_origemrestricao"] == "SIS").sum())
        loc_sem_q = int((sub["cod_origemrestricao"] == "LOC").sum())
        sub_com_q = sub[~sub["em_quarentena"]]
        sis_com_q = int((sub_com_q["cod_origemrestricao"] == "SIS").sum())
        loc_com_q = int((sub_com_q["cod_origemrestricao"] == "LOC").sum())
        sub_pos = sub[sub["corte_pos"]]
        sis_pos = int((sub_pos["cod_origemrestricao"] == "SIS").sum())
        loc_pos = int((sub_pos["cod_origemrestricao"] == "LOC").sum())

        linhas.append(
            {
                "razao": r,
                "sem_quarentena_n": n_sem_q,
                "sem_quarentena_pct_restr": round(n_sem_q / len(df_restr) * 100, 2) if len(df_restr) else 0.0,
                "sem_quarentena_pct_raw": round(n_sem_q / total_linhas_raw * 100, 2) if total_linhas_raw else 0.0,
                "quarentena_n": n_quar,
                "quarentena_pct_da_razao": round(n_quar / n_sem_q * 100, 2) if n_sem_q else 0.0,
                "com_quarentena_n": n_com_q,
                "com_quarentena_pct_pos_q": round(n_com_q / int((~df_restr["em_quarentena"]).sum()) * 100, 2),
                "corte_zero_n": n_zero,
                "corte_zero_pct_da_razao": round(n_zero / n_sem_q * 100, 2) if n_sem_q else 0.0,
                "corte_pos_n": n_pos,
                "corte_pos_pct_pos": round(n_pos / int(df_restr["corte_pos"].sum()) * 100, 2),
                "ativos_sem_q": int(sub["id_ons"].nunique()),
                "ativos_com_q": int(sub_com_q["id_ons"].nunique()),
                "ativos_corte_pos": int(sub_pos["id_ons"].nunique()),
                "patamares_sem_q": int(sub["din_instante"].nunique()),
                "patamares_com_q": int(sub_com_q["din_instante"].nunique()),
                "patamares_corte_pos": int(sub_pos["din_instante"].nunique()),
                "sis_sem_q": sis_sem_q,
                "loc_sem_q": loc_sem_q,
                "sis_com_q": sis_com_q,
                "loc_com_q": loc_com_q,
                "sis_pos": sis_pos,
                "loc_pos": loc_pos,
                "gwh_pos": round(float(sub["corte_mwh_pos"].sum() / 1000.0), 3),
                "gwh_bruto": round(float(sub["corte_mwh_bruto"].sum() / 1000.0), 3),
            }
        )
    return pd.DataFrame(linhas)


def analisar_instante_gate31a(df_raw: pd.DataFrame, df_restr: pd.DataFrame) -> None:
    """Executa a verificacao completa do Item 1."""
    df_corte = g31.calcular_corte(df_raw)
    instante = g31a.escolher_instante(df_corte)
    recorte_sem_filtro = g31a.usinas_do_instante(df_corte, instante)
    recorte_com_filtro = recorte_sem_filtro[recorte_sem_filtro["cod_razaorestricao"] == "ENE"].reset_index(drop=True)

    print("=" * 88)
    print(f"ITEM 1 — REPRODUCAO DO INSTANTE DO GATE 3.1A: {instante}")
    print("=" * 88)

    inst_raw = df_raw[df_raw["din_instante"] == instante]
    inst_restr = df_restr[df_restr["din_instante"] == instante]
    inst_com_q = df_corte[df_corte["din_instante"] == instante]

    print(f"Universo no instante {instante}:")
    print(f"  Conjuntos totais no dataset ......................... {len(inst_raw)}")
    print(f"  Sem restricao declarada (cod_razaorestricao <NA>) ... {int(inst_raw['cod_razaorestricao'].isna().sum())}")
    print(f"  Com restricao declarada (sem quarentena) ............ {len(inst_restr)}")
    print(f"  Em quarentena (corte_mw < -1e-6) .................... {int(inst_restr['em_quarentena'].sum())}")
    print(f"  Pos-quarentena (corte_mw >= 0) ...................... {len(inst_com_q)}")
    print(f"  Pos-quarentena com corte_mw == 0 .................... {int(inst_restr['corte_zero'].sum())}")
    print(f"  usinas_do_instante() [corte_mw > 0, sem filtro ENE] . {len(recorte_sem_filtro)}")
    print(f"  usinas_do_instante() [corte_mw > 0, com filtro ENE] . {len(recorte_com_filtro)}")

    rows_inst = []
    for r in RAZOES_ORDEM + ["TODAS"]:
        s_sem_q = inst_restr if r == "TODAS" else inst_restr[inst_restr["cod_razaorestricao"] == r]
        s_com_q = inst_com_q if r == "TODAS" else inst_com_q[inst_com_q["cod_razaorestricao"] == r]
        s_pos = recorte_sem_filtro if r == "TODAS" else recorte_sem_filtro[recorte_sem_filtro["cod_razaorestricao"] == r]
        rows_inst.append(
            {
                "razao": r,
                "sem_quarentena": len(s_sem_q),
                "em_quarentena": int(s_sem_q["em_quarentena"].sum()),
                "com_quarentena": len(s_com_q),
                "corte_zero": int(s_sem_q["corte_zero"].sum()),
                "usinas_do_instante_corte_pos": len(s_pos),
                "corte_mw_total": round(float(s_pos["corte_mw"].sum()), 4),
                "corte_mwh_total": round(float(s_pos["corte_mwh"].sum()), 4),
                "geracao_mw_total": round(float(s_pos["val_geracao"].sum()), 4),
                "limitada_mw_total": round(float(s_pos["val_geracaolimitada"].sum()), 4),
                "disp_mw_total": round(float(s_pos["val_disponibilidade"].sum()), 4),
            }
        )
    print("\nContagem por razao no instante 2025-01-13 15:00:00:")
    print(pd.DataFrame(rows_inst).to_string(index=False))

    # Comparar rateio 6.1 sem filtro ENE vs com filtro ENE no instante 2025-01-13 15:00:00
    dist_sem = g31a.distribuicao_do_corte(recorte_sem_filtro)
    dist_com = g31a.distribuicao_do_corte(recorte_com_filtro)
    comp = dist_sem.merge(dist_com, on=["id_ons", "nome"], suffixes=("_sem_filtro", "_com_filtro"))
    comp["delta_A_mw"] = comp["baseline_A_mw_com_filtro"] - comp["baseline_A_mw_sem_filtro"]
    comp["delta_B_mw"] = comp["baseline_B_mw_com_filtro"] - comp["baseline_B_mw_sem_filtro"]

    print("\nImpacto da aplicacao do filtro ENE em 2025-01-13 15:00:00:")
    print(f"  Conjuntos removidos ............... {len(recorte_sem_filtro) - len(recorte_com_filtro)}")
    print(f"  Impacto no excedente (MWh) ........ {recorte_com_filtro['corte_mwh'].sum() - recorte_sem_filtro['corte_mwh'].sum():.4f} MWh")
    print(f"  Impacto maximo no rateio 6.1 (MW) . {comp['delta_A_mw'].abs().max():.4f} MW")
    print(f"  Impacto acumulado rateio 6.1 (MW) . {comp['delta_A_mw'].abs().sum():.4f} MW")

    # Varredura de todos os patamares do mes onde ENE ocorre junto com outra razao
    print("\n--- Varredura nos 164 patamares com ENE em Janeiro de 2025 ---")
    # Base pos-quarentena com corte > 0 (comportamento de usinas_do_instante)
    patamares_ene = sorted(df_corte[(df_corte["cod_razaorestricao"] == "ENE") & (df_corte["corte_mw"] > 0)]["din_instante"].unique())
    mistos_corte_pos = []
    for t in patamares_ene:
        rec_all = g31a.usinas_do_instante(df_corte, t)
        vc = rec_all["cod_razaorestricao"].value_counts()
        n_ene = int(vc.get("ENE", 0))
        n_rel = int(vc.get("REL", 0))
        n_cnf = int(vc.get("CNF", 0))
        n_par = int(vc.get("PAR", 0))
        if n_rel + n_cnf + n_par > 0:
            rec_ene = rec_all[rec_all["cod_razaorestricao"] == "ENE"].copy()
            # Rateio iterativo (baseline_ons.py)
            d_all = g31a.distribuicao_do_corte(rec_all)
            d_ene = g31a.distribuicao_do_corte(rec_ene)
            m = d_ene.merge(d_all[["id_ons", "baseline_A_mw"]], on="id_ons", suffixes=("_ene", "_all"))
            delta_iter = (m["baseline_A_mw_all"] - m["baseline_A_mw_ene"]).abs()

            # Rateio puro sem saturacao (gate31a2_decomposicao.py)
            peso_all = np.minimum(rec_all["val_geracao"].to_numpy(float), rec_all["val_geracaolimitada"].to_numpy(float))
            puro_all = pd.Series(g31a2.rateio_puro(peso_all, float(rec_all["corte_mw"].sum())), index=rec_all["id_ons"])
            peso_ene = np.minimum(rec_ene["val_geracao"].to_numpy(float), rec_ene["val_geracaolimitada"].to_numpy(float))
            puro_ene = pd.Series(g31a2.rateio_puro(peso_ene, float(rec_ene["corte_mw"].sum())), index=rec_ene["id_ons"])
            delta_puro = (puro_all.loc[puro_ene.index] - puro_ene).abs()

            # Parcela erroneamente atribuida a usinas nao-ENE no rateio 6.1
            d_nao_ene = d_all[~d_all["id_ons"].isin(set(rec_ene["id_ons"]))]
            puro_nao_ene = puro_all.loc[d_nao_ene["id_ons"]]

            mistos_corte_pos.append(
                {
                    "din_instante": t,
                    "n_total": len(rec_all),
                    "n_ene": n_ene,
                    "n_rel": n_rel,
                    "n_cnf": n_cnf,
                    "n_par": n_par,
                    "mwh_total": round(float(rec_all["corte_mwh"].sum()), 2),
                    "mwh_ene": round(float(rec_ene["corte_mwh"].sum()), 2),
                    "mwh_nao_ene": round(float(rec_all["corte_mwh"].sum() - rec_ene["corte_mwh"].sum()), 2),
                    "saturado": bool(rec_ene["corte_mw"].sum() >= rec_ene["val_geracao"].sum() - 1e-6),
                    "rateio61_iter_nao_ene_mw": round(float(d_nao_ene["baseline_A_mw"].sum()), 2),
                    "rateio61_iter_delta_ene_soma_mw": round(float(delta_iter.sum()), 2),
                    "rateio61_iter_delta_ene_max_mw": round(float(delta_iter.max()), 2),
                    "rateio61_puro_nao_ene_mw": round(float(puro_nao_ene.sum()), 2),
                    "rateio61_puro_delta_ene_soma_mw": round(float(delta_puro.sum()), 2),
                    "rateio61_puro_delta_ene_max_mw": round(float(delta_puro.max()), 2),
                }
            )
    df_mistos_pos = pd.DataFrame(mistos_corte_pos)
    print(f"Patamares com ENE + outra razao em usinas_do_instante() (pos-quarentena, corte>0): {len(df_mistos_pos)} de {len(patamares_ene)}")
    print(df_mistos_pos.to_string(index=False))

    # Tambem verificar sem quarentena e sem corte>0 quantos patamares tem ENE + outra razao
    pat_ene_raw = sorted(df_restr[df_restr["cod_razaorestricao"] == "ENE"]["din_instante"].unique())
    mistos_raw = []
    for t in pat_ene_raw:
        sub_t = df_restr[df_restr["din_instante"] == t]
        vc = sub_t["cod_razaorestricao"].value_counts()
        if int(vc.get("REL", 0)) + int(vc.get("CNF", 0)) + int(vc.get("PAR", 0)) > 0:
            mistos_raw.append(
                {
                    "din_instante": t,
                    "n_total_sem_q": len(sub_t),
                    "n_ene_sem_q": int(vc.get("ENE", 0)),
                    "n_rel_sem_q": int(vc.get("REL", 0)),
                    "n_cnf_sem_q": int(vc.get("CNF", 0)),
                    "n_par_sem_q": int(vc.get("PAR", 0)),
                }
            )
    df_mistos_raw = pd.DataFrame(mistos_raw)
    print(f"\nPatamares com ENE + outra razao na base declarada (sem quarentena, sem corte>0): {len(df_mistos_raw)} de {len(pat_ene_raw)}")
    print(df_mistos_raw.to_string(index=False))


def episodios_ativo(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa intervalos consecutivos por (id_ons, cod_razaorestricao)."""
    chave = ["id_ons", "cod_razaorestricao"]
    if df.empty:
        return pd.DataFrame()
    base = df.sort_values(chave + ["din_instante"]).copy()
    g = base.groupby(chave, observed=True)["din_instante"]
    salto = g.diff().ne(PASSO)
    base["episodio"] = salto.groupby([base[c] for c in chave], observed=True).cumsum()

    agg = (
        base.groupby(chave + ["episodio"], observed=True)
        .agg(
            inicio=("din_instante", "min"),
            fim=("din_instante", "max"),
            intervalos=("din_instante", "size"),
            mwh_pos=("corte_mwh_pos", "sum"),
            mwh_bruto=("corte_mwh_bruto", "sum"),
            n_quarentena=("em_quarentena", "sum"),
            n_corte_zero=("corte_zero", "sum"),
            n_corte_pos=("corte_pos", "sum"),
        )
        .reset_index()
    )
    agg["horas"] = agg["intervalos"] * PASSO_HORAS
    return agg


def blocos_sistemicos_razao(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa instantes consecutivos no SIN em blocos sistemicos."""
    if df.empty:
        return pd.DataFrame()
    sist = (
        df.groupby("din_instante")
        .agg(
            mwh_pos=("corte_mwh_pos", "sum"),
            mwh_bruto=("corte_mwh_bruto", "sum"),
            ativos=("id_ons", "nunique"),
            ativos_corte_pos=("corte_pos", "sum"),
            ativos_quarentena=("em_quarentena", "sum"),
            ativos_corte_zero=("corte_zero", "sum"),
        )
        .sort_index()
    )
    marca = sist.index.to_series().diff().ne(PASSO).cumsum()
    blocos = (
        sist.groupby(marca)
        .agg(
            inicio=("mwh_pos", lambda s: s.index.min()),
            fim=("mwh_pos", lambda s: s.index.max()),
            intervalos=("mwh_pos", "size"),
            mwh_pos=("mwh_pos", "sum"),
            mwh_bruto=("mwh_bruto", "sum"),
            ativos_min=("ativos", "min"),
            ativos_mediano=("ativos", "median"),
            ativos_media=("ativos", "mean"),
            ativos_max=("ativos", "max"),
            patamares_gt_130=("ativos", lambda s: int((s > 130).sum())),
            patamares_ge_130=("ativos", lambda s: int((s >= 130).sum())),
        )
        .reset_index(drop=True)
    )
    blocos["horas"] = blocos["intervalos"] * PASSO_HORAS
    return blocos


def analisar_episodios_e_blocos(df_restr: pd.DataFrame) -> None:
    """Executa a analise completa dos Itens 2 e 3."""
    print("\n" + "=" * 88)
    print("ITENS 2 E 3 — DURACAO DOS EPISODIOS E CONJUNTOS SIMULTANEOS POR RAZAO E DENOMINADOR")
    print("=" * 88)

    recortes = [
        ("Sem Quarentena, Sem corte>0 (Ocorrencia Declarada)", df_restr),
        ("Com Quarentena (corte>=0), Sem corte>0", df_restr[~df_restr["em_quarentena"]]),
        ("Com Quarentena, Com corte>0 (Original Gate 3.1)", df_restr[df_restr["corte_pos"]]),
    ]

    # Resumo comparativo de episodios por ativo
    linhas_ep = []
    for rotulo_base, dbase in recortes:
        for r in RAZOES_ORDEM + ["TODAS"]:
            sub = dbase if r == "TODAS" else dbase[dbase["cod_razaorestricao"] == r]
            ep = episodios_ativo(sub)
            if ep.empty:
                linhas_ep.append(
                    {
                        "base": rotulo_base,
                        "razao": r,
                        "ocorrencias": 0,
                        "ativos": 0,
                        "episodios": 0,
                        "horas_p25": 0.0,
                        "horas_mediana": 0.0,
                        "horas_media": 0.0,
                        "horas_p75": 0.0,
                        "horas_p90": 0.0,
                        "horas_max": 0.0,
                        "ep_30min_n": 0,
                        "ep_30min_pct": 0.0,
                        "mwh_30min_pct": 0.0,
                        "ep_ge_4h_n": 0,
                        "ep_ge_4h_pct": 0.0,
                        "ocorr_ge_4h_pct": 0.0,
                        "mwh_ge_4h_pct": 0.0,
                        "ep_8h_11h5_n": 0,
                        "ep_8h_11h5_pct": 0.0,
                        "ep_9h_11h5_n": 0,
                        "ep_9h_11h5_pct": 0.0,
                    }
                )
                continue
            tot_mwh = float(ep["mwh_pos"].sum())
            tot_int = int(ep["intervalos"].sum())
            e30 = ep[ep["intervalos"] == 1]
            e4h = ep[ep["intervalos"] >= 8]
            e8_115 = ep[(ep["horas"] >= 8.0) & (ep["horas"] <= 11.5)]
            e9_115 = ep[(ep["horas"] >= 9.0) & (ep["horas"] <= 11.5)]
            linhas_ep.append(
                {
                    "base": rotulo_base,
                    "razao": r,
                    "ocorrencias": len(sub),
                    "ativos": int(ep["id_ons"].nunique()),
                    "episodios": len(ep),
                    "horas_p25": round(float(ep["horas"].quantile(0.25)), 2),
                    "horas_mediana": round(float(ep["horas"].median()), 2),
                    "horas_media": round(float(ep["horas"].mean()), 2),
                    "horas_p75": round(float(ep["horas"].quantile(0.75)), 2),
                    "horas_p90": round(float(ep["horas"].quantile(0.90)), 2),
                    "horas_max": round(float(ep["horas"].max()), 2),
                    "ep_30min_n": len(e30),
                    "ep_30min_pct": round(len(e30) / len(ep) * 100, 1),
                    "mwh_30min_pct": round(float(e30["mwh_pos"].sum()) / tot_mwh * 100, 2) if tot_mwh else 0.0,
                    "ep_ge_4h_n": len(e4h),
                    "ep_ge_4h_pct": round(len(e4h) / len(ep) * 100, 1),
                    "ocorr_ge_4h_pct": round(int(e4h["intervalos"].sum()) / tot_int * 100, 1) if tot_int else 0.0,
                    "mwh_ge_4h_pct": round(float(e4h["mwh_pos"].sum()) / tot_mwh * 100, 1) if tot_mwh else 0.0,
                    "ep_8h_11h5_n": len(e8_115),
                    "ep_8h_11h5_pct": round(len(e8_115) / len(ep) * 100, 1),
                    "ep_9h_11h5_n": len(e9_115),
                    "ep_9h_11h5_pct": round(len(e9_115) / len(ep) * 100, 1),
                }
            )
    df_res_ep = pd.DataFrame(linhas_ep)
    print("\n--- Resumo de Episodios por Ativo (id_ons + cod_razaorestricao) ---")
    print(df_res_ep.to_string(index=False))

    # Resumo comparativo de blocos sistemicos
    linhas_bl = []
    for rotulo_base, dbase in recortes:
        for r in RAZOES_ORDEM + ["TODAS"]:
            sub = dbase if r == "TODAS" else dbase[dbase["cod_razaorestricao"] == r]
            bl = blocos_sistemicos_razao(sub)
            if bl.empty:
                linhas_bl.append(
                    {
                        "base": rotulo_base,
                        "razao": r,
                        "ocorrencias": 0,
                        "patamares": 0,
                        "blocos": 0,
                        "horas_min": 0.0,
                        "horas_mediana": 0.0,
                        "horas_media": 0.0,
                        "horas_max": 0.0,
                        "blocos_9h_11h5": 0,
                        "blocos_7h5_11h5": 0,
                        "ativos_simult_max": 0,
                        "ativos_simult_mediana_patamar": 0.0,
                        "blocos_max_gt_130": 0,
                        "patamares_gt_130": 0,
                        "patamares_ge_130": 0,
                    }
                )
                continue
            pat_ativos = sub.groupby("din_instante")["id_ons"].nunique()
            linhas_bl.append(
                {
                    "base": rotulo_base,
                    "razao": r,
                    "ocorrencias": len(sub),
                    "patamares": int(bl["intervalos"].sum()),
                    "blocos": len(bl),
                    "horas_min": round(float(bl["horas"].min()), 2),
                    "horas_mediana": round(float(bl["horas"].median()), 2),
                    "horas_media": round(float(bl["horas"].mean()), 2),
                    "horas_max": round(float(bl["horas"].max()), 2),
                    "blocos_9h_11h5": int(((bl["horas"] >= 9.0) & (bl["horas"] <= 11.5)).sum()),
                    "blocos_7h5_11h5": int(((bl["horas"] >= 7.5) & (bl["horas"] <= 11.5)).sum()),
                    "ativos_simult_max": int(bl["ativos_max"].max()),
                    "ativos_simult_mediana_patamar": round(float(pat_ativos.median()), 1),
                    "blocos_max_gt_130": int((bl["ativos_max"] > 130).sum()),
                    "patamares_gt_130": int(bl["patamares_gt_130"].sum()),
                    "patamares_ge_130": int(bl["patamares_ge_130"].sum()),
                }
            )
    df_res_bl = pd.DataFrame(linhas_bl)
    print("\n--- Resumo de Blocos Sistemicos (Simultaneos no SIN por din_instante) ---")
    print(df_res_bl.to_string(index=False))

    # Imprimir todos os blocos sistemicos de ENE, REL e CNF lado a lado nas 3 bases
    for r in ["ENE", "REL", "CNF"]:
        print(f"\n=== Detalhamento dos Blocos Sistemicos — Razao {r} ===")
        for rotulo_base, dbase in recortes:
            sub = dbase[dbase["cod_razaorestricao"] == r]
            bl = blocos_sistemicos_razao(sub)
            print(f"\n[{r}] {rotulo_base} (blocos={len(bl)}, patamares={int(bl['intervalos'].sum())}):")
            print(bl.to_string(index=False))


if __name__ == "__main__":
    ano, mes = 2025, 1
    df_raw = g31.carregar(ano, mes)
    df_restr = preparar_base_completa(df_raw)

    print("=" * 88)
    print("DENOMINADORES GLOBAIS — JANEIRO DE 2025 (EOLICA)")
    print("=" * 88)
    print(f"Total de linhas no Parquet ({ano}-{mes:02d}): {len(df_raw):,}")
    print(f"Linhas sem restricao declarada (<NA>): {int(df_raw['cod_razaorestricao'].isna().sum()):,}")
    print(f"Linhas com restricao declarada (cod_razaorestricao preenchido): {len(df_restr):,}")
    tab_den = tabela_denominadores(df_restr, len(df_raw))
    print(tab_den.to_string(index=False))

    analisar_instante_gate31a(df_raw, df_restr)
    analisar_episodios_e_blocos(df_restr)
