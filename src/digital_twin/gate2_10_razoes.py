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

num = [
    "val_ventoverificado",
    "val_geracaoestimada",
    "val_geracaoverificada"
]

b[num] = b[num].apply(
    pd.to_numeric,
    errors="coerce"
)

m = b.merge(
    a[
        [
            "id_ons",
            "din_instante",
            "cod_razaorestricao",
            "COFF",
            "val_geracao",
            "val_geracaoreferencia",
            "val_geracaolimitada",
            "val_disponibilidade"
        ]
    ],
    on=["id_ons", "din_instante"],
    how="left"
)

m["GE"] = m["val_geracaoestimada"]
m["GV"] = m["val_geracaoverificada"]

m["R"] = (
    m["GV"] /
    m["GE"].replace(0, np.nan)
)

m["GF"] = (
    m["GE"] -
    m["GV"]
)

m["L_G"] = (
    pd.to_numeric(
        m["val_geracaolimitada"],
        errors="coerce"
    )
    -
    pd.to_numeric(
        m["val_geracao"],
        errors="coerce"
    )
)

m["R_G"] = (
    pd.to_numeric(
        m["val_geracaoreferencia"],
        errors="coerce"
    )
    -
    pd.to_numeric(
        m["val_geracao"],
        errors="coerce"
    )
)

m = m[
    m["cod_razaorestricao"].isin(
        ["ENE", "CNF", "REL"]
    )
].copy()

print("=== GATE 2.10: ENE x CNF x REL ===")
print()

print("=== CONTAGEM ===")
print(
    m["cod_razaorestricao"]
    .value_counts()
    .to_string()
)

print()

print("=== REALIZACAO GV / GE ===")

print(
    m[m["GE"] >= 5]
    .groupby("cod_razaorestricao")["R"]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75)
    )
    .round(4)
    .to_string()
)

print()

print("=== GF = GE - GV ===")

print(
    m.groupby("cod_razaorestricao")["GF"]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75),
        max="max"
    )
    .round(4)
    .to_string()
)

print()

print("=== DESVIO DA LIMITADA L-G ===")

print(
    m.groupby("cod_razaorestricao")["L_G"]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75)
    )
    .round(4)
    .to_string()
)

print()

print("=== DESVIO DA REFERENCIA R-G ===")

print(
    m.groupby("cod_razaorestricao")["R_G"]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75)
    )
    .round(4)
    .to_string()
)

print()

print("=== VENTO ===")

print(
    m.groupby("cod_razaorestricao")[
        "val_ventoverificado"
    ]
    .agg(
        n="count",
        mediana="median",
        media="mean",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75)
    )
    .round(4)
    .to_string()
)

print()

print("=== CORRELACOES COM GF ===")

for razao, g in m.groupby(
    "cod_razaorestricao"
):

    cols = [
        "val_ventoverificado",
        "GE",
        "GV",
        "L_G",
        "R_G"
    ]

    print()
    print("---", razao, "---")

    print(
        g[cols + ["GF"]]
        .corr()["GF"]
        .drop("GF")
        .round(4)
        .to_string()
    )
