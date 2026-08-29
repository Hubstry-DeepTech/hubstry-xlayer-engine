"""
Gate 3.1 — Persistencia dos episodios de curtailment
====================================================
PERGUNTA QUE ESTE SCRIPT RESPONDE
---------------------------------
Um evento de curtailment constitui uma janela continua de energia
aproveitavel, ou e um pulso isolado de 30 minutos?

A resposta decide a viabilidade do Allocation Engine. Se os cortes
forem pontuais, nao ha energia sustentada para armazenamento
eletroquimico nem para processo industrial continuo, e os unicos
destinos viaveis sao cargas interrompiveis de resposta rapida. Se
houver janelas de horas, bateria e carga industrial entram.

POR QUE REFAZER O GATE 2.9
--------------------------
O Gate 2.9 concluiu que todo episodio COFF tem 1 intervalo, sem
nenhum caso de 4 ou mais. Isso contradiz a serie observada: em
2025-01-04 ha cortes por razao energetica as 16:30, 17:00 e 17:30,
com 111 conjuntos em cada intervalo — uma janela de 1h30.

A causa provavel e a amostra. O Gate 2.9 rodou sobre os 11 ativos da
intersecao COFF x DETAIL, que sao Tipo I e Tipo II-B. Os grandes
eventos energeticos ocorrem em conjuntos Tipo II-C (prefixo CJU_ no
id_ons), estruturalmente ausentes daquela intersecao. A amostra
excluia o fenomeno que se queria medir.

Este script roda sobre o COFF COMPLETO.

DEFINICAO DE EPISODIO
---------------------
Sequencia de intervalos semi-horarios CONSECUTIVOS em que o mesmo
ativo teve corte positivo pela mesma razao. Um intervalo faltante
encerra o episodio.

Corte = val_geracaolimitada - val_geracao   (formula validada:
zero negativas em 142 usinas no instante testado; as alternativas
produziram negativas ou violacoes fisicas).

O QUE NAO E RESPONDIDO AQUI
---------------------------
Persistencia observada nao e persistencia previsivel. Saber que
episodios duram em media X intervalos nao permite afirmar, no inicio
de um evento, que ele durara X. Isso e problema do Heuristic Engine
e exige validacao fora da amostra.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    from . import ons_client as ons
except ImportError:
    import ons_client as ons

PREFIXO_EOLICA = "dataset/restricao_coff_eolica_tm/"
PASSO_HORAS = 0.5
PASSO = pd.Timedelta(minutes=30)

VAL_COLS = [
    "val_geracao", "val_geracaolimitada", "val_disponibilidade",
    "val_geracaoreferencia", "val_geracaoreferenciafinal",
]
COD_COLS = ["cod_razaorestricao", "cod_origemrestricao", "dsc_restricao"]


# ----------------------------------------------------------------------

def para_numero(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip()
    t = t.mask(t.isin(["", "-", "nan", "None"]))
    if t.str.contains(r"\d\.\d{3},", na=False).any():
        t = t.str.replace(".", "", regex=False)
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")


def carregar(ano: int, mes: int) -> pd.DataFrame:
    objs = ons.listar(PREFIXO_EOLICA, contendo=f"_{ano}_{mes:02d}.parquet")
    if not objs:
        raise FileNotFoundError(f"parquet de {ano}-{mes:02d} nao encontrado")
    df = pd.read_parquet(ons.baixar(objs[0].key))
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    for c in VAL_COLS:
        if c in df.columns:
            df[c] = para_numero(df[c])
    for c in COD_COLS:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    return df


def calcular_corte(df: pd.DataFrame) -> pd.DataFrame:
    """
    Corte = limitada - geracao, apenas nas linhas com restricao.
    Negativas sao postas em quarentena, nao abortam a execucao: com
    41 mil linhas, um punhado de anomalias e esperado e deve ser
    reportado, nao fatal.
    """
    out = df[df["cod_razaorestricao"].notna()].copy()
    out = out.dropna(subset=["val_geracaolimitada", "val_geracao"])
    out["corte_mw"] = out["val_geracaolimitada"] - out["val_geracao"]

    quarentena = out[out["corte_mw"] < -1e-6]
    out = out[out["corte_mw"] >= -1e-6].copy()
    out["corte_mw"] = out["corte_mw"].clip(lower=0.0)
    out["corte_mwh"] = out["corte_mw"] * PASSO_HORAS

    out.attrs["quarentena_linhas"] = len(quarentena)
    out.attrs["quarentena_pct"] = round(
        len(quarentena) / max(len(quarentena) + len(out), 1) * 100, 2
    )
    return out


# ----------------------------------------------------------------------

def episodios(df: pd.DataFrame, chave: List[str] | None = None) -> pd.DataFrame:
    """
    Agrupa intervalos consecutivos com corte > 0 em episodios.

    chave define a unidade de analise. Padrao: ativo + razao.
    """
    chave = chave or ["id_ons", "cod_razaorestricao"]
    base = df[df["corte_mw"] > 0].sort_values(chave + ["din_instante"]).copy()
    if base.empty:
        return pd.DataFrame()

    g = base.groupby(chave, observed=True)["din_instante"]
    salto = g.diff().ne(PASSO)          # True quando quebra a sequencia
    base["episodio"] = salto.groupby([base[c] for c in chave],
                                     observed=True).cumsum()

    agg = (
        base.groupby(chave + ["episodio"], observed=True)
        .agg(
            inicio=("din_instante", "min"),
            fim=("din_instante", "max"),
            intervalos=("din_instante", "size"),
            mwh=("corte_mwh", "sum"),
            mw_medio=("corte_mw", "mean"),
            mw_pico=("corte_mw", "max"),
        )
        .reset_index()
    )
    agg["horas"] = agg["intervalos"] * PASSO_HORAS
    return agg


def distribuicao(ep: pd.DataFrame, rotulo: str) -> None:
    if ep.empty:
        print(f"{rotulo}: nenhum episodio")
        return
    n = len(ep)
    print(f"\n=== {rotulo} ===")
    print(f"  episodios ................. {n:,}")
    print(f"  intervalos: mediana {ep['intervalos'].median():.0f}  "
          f"media {ep['intervalos'].mean():.2f}  max {ep['intervalos'].max()}")
    print(f"  duracao:    mediana {ep['horas'].median():.1f}h  "
          f"max {ep['horas'].max():.1f}h")
    print(f"  energia:    total {ep['mwh'].sum()/1000:,.1f} GWh  "
          f"mediana por episodio {ep['mwh'].median():.1f} MWh")

    print("  distribuicao de duracao:")
    faixas = [(1, 1), (2, 3), (4, 7), (8, 15), (16, 47), (48, 10**9)]
    rotulos = ["   30 min", " 1h - 1h30", "  2h - 3h30", "  4h - 7h30",
               "  8h - 23h30", "   >= 24h"]
    for (lo, hi), r in zip(faixas, rotulos):
        sel = ep[(ep["intervalos"] >= lo) & (ep["intervalos"] <= hi)]
        if len(sel):
            print(f"    {r:<14} {len(sel):>6,} episodios  "
                  f"({len(sel)/n*100:5.1f}%)   "
                  f"{sel['mwh'].sum()/1000:8.1f} GWh  "
                  f"({sel['mwh'].sum()/ep['mwh'].sum()*100:5.1f}% da energia)")


def janelas_aproveitaveis(ep: pd.DataFrame, min_intervalos: int = 4,
                          min_mwh: float = 50.0) -> pd.DataFrame:
    """
    Episodios longos e volumosos o bastante para justificar um destino
    com inercia (bateria, processo industrial).
    """
    return ep[(ep["intervalos"] >= min_intervalos) & (ep["mwh"] >= min_mwh)]


# ----------------------------------------------------------------------

if __name__ == "__main__":
    ANO, MES = 2025, 1

    print(f"Carregando COFF eolica {ANO}-{MES:02d} (dataset completo)...")
    df = calcular_corte(carregar(ANO, MES))
    print(f"  linhas com restricao e corte valido: {len(df):,}")
    print(f"  quarentena (corte negativo): {df.attrs['quarentena_linhas']:,} "
          f"({df.attrs['quarentena_pct']}%)")
    print(f"  ativos distintos: {df['id_ons'].nunique()}")

    conj = df[df["id_ons"].astype(str).str.startswith("CJU_")]["id_ons"].nunique()
    print(f"  destes, conjuntos Tipo II-C (CJU_): {conj}")
    print("  NOTA: o Gate 2.9 rodou sobre 11 ativos Tipo I e II-B, que")
    print("        excluem estes conjuntos. Dai a divergencia.")

    ep = episodios(df)
    distribuicao(ep, "TODAS AS RAZOES")

    for razao in ["ENE", "CNF", "REL"]:
        sub = df[df["cod_razaorestricao"] == razao]
        distribuicao(episodios(sub), f"RAZAO {razao}")

    print("\n\n=== JANELAS APROVEITAVEIS (>= 2h e >= 50 MWh, razao ENE) ===")
    ene = episodios(df[df["cod_razaorestricao"] == "ENE"])
    jan = janelas_aproveitaveis(ene, min_intervalos=4, min_mwh=50.0)
    if jan.empty:
        print("  Nenhuma. Destinos com inercia ficam inviaveis; so cargas")
        print("  interrompiveis de resposta rapida fazem sentido.")
    else:
        print(f"  {len(jan):,} janelas  |  {jan['mwh'].sum()/1000:,.1f} GWh  "
              f"({jan['mwh'].sum()/ene['mwh'].sum()*100:.1f}% do corte ENE)")
        print(f"  duracao mediana: {jan['horas'].median():.1f}h  "
              f"maxima: {jan['horas'].max():.1f}h")
        print("\n  Dez maiores:")
        cols = ["id_ons", "inicio", "fim", "intervalos", "horas", "mwh", "mw_pico"]
        print(jan.nlargest(10, "mwh")[cols].to_string(index=False))

    print("\n\n=== EVENTO SISTEMICO: cortes simultaneos por instante (ENE) ===")
    sist = (
        df[(df["cod_razaorestricao"] == "ENE") & (df["corte_mw"] > 0)]
        .groupby("din_instante")
        .agg(mwh=("corte_mwh", "sum"), ativos=("id_ons", "nunique"))
        .sort_index()
    )
    if len(sist):
        marca = sist.index.to_series().diff().ne(PASSO).cumsum()
        blocos = (
            sist.groupby(marca)
            .agg(inicio=("mwh", lambda s: s.index.min()),
                 fim=("mwh", lambda s: s.index.max()),
                 intervalos=("mwh", "size"),
                 mwh=("mwh", "sum"),
                 ativos_max=("ativos", "max"))
        )
        blocos["horas"] = blocos["intervalos"] * PASSO_HORAS
        print(f"  blocos sistemicos: {len(blocos):,}")
        print(f"  duracao mediana: {blocos['horas'].median():.1f}h  "
              f"maxima: {blocos['horas'].max():.1f}h")
        print("\n  Dez maiores:")
        print(blocos.nlargest(10, "mwh").to_string(index=False))

    print("\n\n--- Leitura ---")
    print("  Janela sistemica e o que importa para o Allocation Engine:")
    print("  um destino co-localizado absorve o excedente do parque a que")
    print("  esta ligado, mas a duracao do evento e sistemica.")
    print("  Persistencia observada nao e persistencia previsivel — para")
    print("  isso, validar fora da amostra em outro mes.")
