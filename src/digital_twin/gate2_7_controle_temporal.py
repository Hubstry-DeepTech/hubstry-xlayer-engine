import pandas as pd
import numpy as np

p1 = r".\data\ons\RESTRICAO_COFF_EOLICA_2025_01.parquet"
p2 = r".\data\ons\RESTRICAO_COFF_EOLICA_DETAIL_2025_01.parquet"

a = pd.read_parquet(p1)
b = pd.read_parquet(p2)

ids = sorted(
    set(a["id_ons"].dropna()) &
    set(b["id_ons"].dropna())
)

a = a[a["id_ons"].isin(ids)].copy()
b = b[b["id_ons"].isin(ids)].copy()

a["COFF"] = a["cod_razaorestricao"].isin(
    ["ENE", "CNF", "REL"]
)

cols = [
    "val_ventoverificado",
    "val_geracaoestimada",
    "val_geracaoverificada",
]

b[cols] = b[cols].apply(
    pd.to_numeric,
    errors="coerce"
)

m = b.merge(
    a[
        [
            "id_ons",
            "din_instante",
            "COFF",
            "cod_razaorestricao",
        ]
    ],
    on=["id_ons", "din_instante"],
    how="left"
)

m["COFF"] = m["COFF"].fillna(False)

m["GE"] = m["val_geracaoestimada"]
m["GV"] = m["val_geracaoverificada"]

m = m[m["GE"] >= 5].copy()

m["taxa_realizacao"] = m["GV"] / m["GE"]

m["hora"] = (
    m["din_instante"].dt.hour
    + m["din_instante"].dt.minute / 60
)

# meia-hora como unidade temporal
m["slot"] = (
    m["din_instante"].dt.hour * 2
    + (m["din_instante"].dt.minute // 30)
)

m["vento_bin"] = pd.cut(
    m["val_ventoverificado"],
    bins=[-0.001, 4, 6, 8, 10, 12, 15, 100],
    include_lowest=True
)

print("=== GATE 2.7: CONTROLE ATIVO + VENTO + HORA ===")
print()

# agregacao dentro de cada ativo + slot + faixa de vento
g = (
    m.groupby(
        [
            "id_ons",
            "slot",
            "vento_bin",
            "COFF"
        ],
        observed=True
    )
    .agg(
        n=("taxa_realizacao", "size"),
        taxa=("taxa_realizacao", "median")
    )
    .reset_index()
)

p = g.pivot_table(
    index=["id_ons", "slot", "vento_bin"],
    columns="COFF",
    values=["n", "taxa"]
)

p.columns = [
    "_".join(
        str(x) for x in c
    )
    for c in p.columns
]

p = p.reset_index()

p = p[
    p["taxa_False"].notna() &
    p["taxa_True"].notna()
].copy()

p["delta"] = (
    p["taxa_True"] -
    p["taxa_False"]
)

print("pares comparáveis:", len(p))
print()

print("=== DISTRIBUICAO DAS DIFERENCAS ===")

print(
    p["delta"]
    .describe(
        percentiles=[
            .05,
            .25,
            .50,
            .75,
            .95
        ]
    )
    .round(4)
    .to_string()
)

print()

print("=== MEDIANA POR ATIVO ===")

print(
    p.groupby("id_ons")["delta"]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        pct_negativa=lambda s: 100 * (s < 0).mean()
    )
    .round(4)
    .to_string()
)

print()

print("=== MEDIANA POR FAIXA DE VENTO ===")

print(
    p.groupby("vento_bin", observed=True)["delta"]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        pct_negativa=lambda s: 100 * (s < 0).mean()
    )
    .round(4)
    .to_string()
)

print()

print("=== RESULTADO GLOBAL ===")

print(
    "delta mediano:",
    round(p["delta"].median(), 4)
)

print(
    "delta medio:",
    round(p["delta"].mean(), 4)
)

print(
    "pares com delta < 0:",
    int((p["delta"] < 0).sum()),
    "/",
    len(p)
)

print(
    "percentual negativo:",
    round(100 * (p["delta"] < 0).mean(), 2),
    "%"
)
