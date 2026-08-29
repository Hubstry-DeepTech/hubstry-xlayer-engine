import pandas as pd
import numpy as np

p1 = r".\data\ons\RESTRICAO_COFF_EOLICA_2025_01.parquet"
p2 = r".\data\ons\RESTRICAO_COFF_EOLICA_DETAIL_2025_01.parquet"

a = pd.read_parquet(p1)
b = pd.read_parquet(p2)

ids = sorted(set(a["id_ons"].dropna()) & set(b["id_ons"].dropna()))

a = a[a["id_ons"].isin(ids)].copy()
b = b[b["id_ons"].isin(ids)].copy()

for c in [
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia"
]:
    a[c] = pd.to_numeric(a[c], errors="coerce")

for c in [
    "val_ventoverificado",
    "val_geracaoestimada",
    "val_geracaoverificada"
]:
    b[c] = pd.to_numeric(b[c], errors="coerce")

m = b.merge(
    a[
        [
            "id_ons",
            "din_instante",
            "cod_razaorestricao",
            "val_geracao",
            "val_geracaolimitada",
            "val_disponibilidade",
            "val_geracaoreferencia"
        ]
    ],
    on=["id_ons", "din_instante"],
    how="inner"
)

m = m[
    m["cod_razaorestricao"].isin(["CNF","ENE","REL"])
].copy()

m["GE"] = m["val_geracaoestimada"]
m["GV"] = m["val_geracaoverificada"]

m = m[m["GE"] > 0].copy()

m["R"] = m["GV"] / m["GE"]

m["vento_bin"] = pd.cut(
    m["val_ventoverificado"],
    bins=[-0.001, 4, 6, 8, 10, 12, 15, 100],
    include_lowest=True
)

m["hora"] = m["din_instante"].dt.hour

print("=== GATE 2.11: RAZAO CONTROLADA ===")
print()

print("=== AMOSTRA ===")
print(
    m.groupby("cod_razaorestricao")
    .size()
    .to_string()
)

print()

print("=== R BRUTO ===")
print(
    m.groupby("cod_razaorestricao")["R"]
    .agg(
        n="count",
        mediana="median",
        media="mean"
    )
    .round(4)
    .to_string()
)

print()

print("=== R POR ATIVO + FAIXA DE VENTO ===")

q = (
    m.groupby(
        ["id_ons","vento_bin","cod_razaorestricao"],
        observed=True
    )["R"]
    .agg(
        n="count",
        mediana="median",
        media="mean"
    )
    .reset_index()
)

print(
    q[q["n"] >= 5]
    .sort_values(["id_ons","vento_bin","cod_razaorestricao"])
    .round(4)
    .to_string(index=False)
)

print()

print("=== MEDIANA POR ATIVO/RAZAO ===")

x = (
    m.groupby(
        ["id_ons","cod_razaorestricao"]
    )["R"]
    .agg(
        n="count",
        mediana="median",
        media="mean"
    )
    .reset_index()
)

print(
    x.round(4)
    .to_string(index=False)
)

print()

print("=== COMPARACAO REL - ENE ===")

p = m.pivot_table(
    index=["id_ons","vento_bin"],
    columns="cod_razaorestricao",
    values="R",
    aggfunc="median"
)

if "REL" in p.columns and "ENE" in p.columns:
    p["REL_menos_ENE"] = p["REL"] - p["ENE"]

if "REL" in p.columns and "CNF" in p.columns:
    p["REL_menos_CNF"] = p["REL"] - p["CNF"]

print(
    p.dropna(how="all")
    .round(4)
    .to_string()
)

print()

print("=== HORA ===")

h = (
    m.groupby(
        ["hora","cod_razaorestricao"]
    )["R"]
    .median()
    .unstack()
)

print(h.round(4).to_string())

print()

print("=== VENTO MEDIANO POR RAZAO ===")

print(
    m.groupby("cod_razaorestricao")["val_ventoverificado"]
    .agg(
        median="median",
        mean="mean"
    )
    .round(4)
    .to_string()
)
