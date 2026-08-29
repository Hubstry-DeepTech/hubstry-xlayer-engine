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

b["GF"] = (
    b["val_geracaoestimada"]
    - b["val_geracaoverificada"]
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
    how="left",
)

m["COFF"] = m["COFF"].fillna(False)

# Evita razoes instaveis para GE proximo de zero.
m["taxa_realizacao"] = np.where(
    m["val_geracaoestimada"] >= 5,
    m["val_geracaoverificada"]
    / m["val_geracaoestimada"],
    np.nan,
)

print("=== TAXA DE REALIZACAO GV / GE ===")
print()

print(
    m.groupby("COFF")["taxa_realizacao"]
    .agg([
        "count",
        "mean",
        "median",
        "std",
        "min",
        "max",
    ])
    .round(4)
    .to_string()
)

print()
print("=== PERCENTIS ===")
print()

print(
    m.groupby("COFF")["taxa_realizacao"]
    .quantile([
        0.05,
        0.25,
        0.50,
        0.75,
        0.95,
    ])
    .unstack()
    .round(4)
    .to_string()
)

print()
print("=== TAXA POR FAIXA DE VENTO ===")
print()

m["vento_bin"] = pd.cut(
    m["val_ventoverificado"],
    bins=[-0.001, 4, 6, 8, 10, 12, 15, 100],
    include_lowest=True,
)

r = (
    m[m["val_geracaoestimada"] >= 5]
    .groupby(
        ["vento_bin", "COFF"],
        observed=True
    )["taxa_realizacao"]
    .agg(
        n="count",
        mediana="median",
        media="mean"
    )
    .reset_index()
)

print(
    r.round(4).to_string(index=False)
)

print()
print("=== DIFERENCA DA MEDIANA COFF - NAO COFF ===")
print()

q = r.pivot_table(
    index="vento_bin",
    columns="COFF",
    values="mediana"
)

q["delta_mediana"] = q[True] - q[False]

print(
    q.round(4).to_string()
)
