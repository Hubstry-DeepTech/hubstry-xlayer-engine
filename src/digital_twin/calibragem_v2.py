"""
Calibracao do dataset agregado de restricao de operacao
=======================================================
Objetivo unico: descobrir empiricamente o que significa
val_geracaolimitada, antes de escrever qualquer valoracao em cima
dela.

A descricao oficial e ambigua: "Valor da Geracao Limitada por alguma
Restricao, em MWmed" pode ser (a) o montante cortado ou (b) o nivel
de geracao durante a restricao. As duas leituras produzem numeros
completamente diferentes.

Hipoteses testadas:
  H1  val_geracaolimitada == corte
      => val_geracao + val_geracaolimitada ~ val_geracaoreferenciafinal
  H2  val_geracaolimitada == geracao sob restricao
      => val_geracaolimitada ~ val_geracao nas linhas com restricao
  H3  corte = val_geracaoreferenciafinal - val_geracao

Rodar antes de usar qualquer numero deste dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from . import ons_client as ons
except ImportError:
    import ons_client as ons

PREFIXO_AGG = "dataset/restricao_coff_eolica_tm/"
ANO, MES = 2025, 1

VAL_COLS = [
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
]


def para_numero(s: pd.Series) -> pd.Series:
    """
    As colunas de valor chegam como texto, com campo VAZIO no lugar de
    zero/ausente e possivel virgula decimal. Converter antes de
    qualquer aritmetica.
    """
    t = s.astype("string").str.strip()
    t = t.mask(t.isin(["", "-", "nan", "None"]))
    t = t.str.replace(".", "", regex=False) if t.str.contains(
        r"\d\.\d{3},", na=False).any() else t
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")


def carregar() -> pd.DataFrame:
    objs = ons.listar(PREFIXO_AGG, contendo=f"_{ANO}_{MES:02d}.parquet")
    if not objs:
        raise FileNotFoundError("parquet agregado nao encontrado")
    df = pd.read_parquet(ons.baixar(objs[0].key))
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    for c in VAL_COLS:
        if c in df.columns:
            df[c] = para_numero(df[c])
    for c in ("cod_razaorestricao", "cod_origemrestricao", "dsc_restricao"):
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    return df


def erro_relativo(a: pd.Series, b: pd.Series) -> dict:
    mask = b.abs() > 1e-6
    if not mask.any():
        return {"n": 0}
    dif = (a[mask] - b[mask]).abs()
    return {
        "n": int(mask.sum()),
        "erro_medio_mw": round(float(dif.mean()), 4),
        "erro_mediano_mw": round(float(dif.median()), 4),
        "pct_linhas_erro_menor_0.01": round(float((dif < 0.01).mean() * 100), 1),
    }


if __name__ == "__main__":
    df = carregar()
    print(f"Linhas: {len(df):,}   Colunas: {len(df.columns)}")
    print(f"Colunas: {list(df.columns)}\n")

    print("--- Estatisticas das colunas de valor (ja numericas) ---")
    presentes = [c for c in VAL_COLS if c in df.columns]
    print(df[presentes].describe().T.to_string())
    print("\nNulos por coluna:")
    print(df[presentes].isna().sum().to_string())

    com_restricao = df[df["cod_razaorestricao"].notna()]
    print(f"\nLinhas com restricao declarada: {len(com_restricao):,} "
          f"de {len(df):,} ({len(com_restricao)/len(df)*100:.1f}%)")

    print("\n--- Razao da restricao ---")
    if "cod_razaorestricao" in df.columns:
        print(df["cod_razaorestricao"].value_counts(dropna=False).to_string())
    print("\n--- Origem da restricao ---")
    if "cod_origemrestricao" in df.columns:
        print(df["cod_origemrestricao"].value_counts(dropna=False).to_string())

    print("\n--- Motivos mais frequentes (dsc_restricao) ---")
    if "dsc_restricao" in df.columns:
        print(df["dsc_restricao"].value_counts(dropna=False).head(12).to_string())

    print("\n--- Teste das hipoteses (apenas linhas com restricao) ---")
    df = com_restricao if len(com_restricao) else df
    if {"val_geracao", "val_geracaolimitada", "val_geracaoreferenciafinal"} <= set(df.columns):
        soma = df["val_geracao"] + df["val_geracaolimitada"]
        print("H1  geracao + limitada == referenciafinal")
        print("   ", erro_relativo(soma, df["val_geracaoreferenciafinal"]))

        print("H2  limitada == geracao")
        print("   ", erro_relativo(df["val_geracaolimitada"], df["val_geracao"]))

        h3 = df["val_geracaoreferenciafinal"] - df["val_geracao"]
        print("H3  corte = referenciafinal - geracao")
        print(f"    soma H3 ....... {h3.clip(lower=0).sum():,.1f} MWmed")
        print(f"    negativas ..... {int((h3 < -1e-6).sum()):,} linhas "
              f"({(h3 < -1e-6).mean()*100:.1f}%)")
        print(f"    soma limitada . {df['val_geracaolimitada'].sum():,.1f} MWmed")
        print(f"    negativas ..... {int((df['val_geracaolimitada'] < -1e-6).sum()):,} linhas")

    print("\n--- Corte por razao, em MWmed (usando val_geracaolimitada) ---")
    if {"cod_razaorestricao", "val_geracaolimitada"} <= set(df.columns):
        por_razao = (
            df.groupby("cod_razaorestricao")["val_geracaolimitada"]
            .agg(["sum", "count"])
            .sort_values("sum", ascending=False)
        )
        por_razao["pct"] = (por_razao["sum"] / por_razao["sum"].sum() * 100).round(1)
        print(por_razao.to_string())

    print("\n--- Amostra ---")
    cols = [c for c in ["din_instante", "id_subsistema", "nom_usina",
                        "val_geracao", "val_geracaolimitada",
                        "val_geracaoreferenciafinal", "cod_razaorestricao",
                        "cod_origemrestricao", "dsc_restricao"] if c in df.columns]
    amostra = df[df.get("val_geracaolimitada", pd.Series(dtype=float)) > 0]
    print((amostra if len(amostra) else df)[cols].head(8).to_string(index=False))
