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

m = m[m["cod_razaorestricao"].isin(["CNF","ENE","REL"])].copy()

m["GE"] = m["val_geracaoestimada"]
m["GV"] = m["val_geracaoverificada"]
m["GF"] = m["GE"] - m["GV"]

m["GE_pos"] = m["GE"] > 0
m["GV_pos"] = m["GV"] > 0

print("=== GATE 2.12: ESTRUTURA DE ZERO ===")
print()

print("=== UNIVERSO ===")
print(
    m.groupby("cod_razaorestricao")
    .size()
    .to_string()
)

print()

print("=== GE > 0 ===")

g = (
    m.groupby("cod_razaorestricao")["GE_pos"]
    .agg(
        n="count",
        positivos="sum",
        pct="mean"
    )
)

g["pct"] *= 100

print(g.round(2).to_string())

print()

print("=== GV > 0 | GE > 0 ===")

x = m[m["GE_pos"]].copy()

v = (
    x.groupby("cod_razaorestricao")["GV_pos"]
    .agg(
        n="count",
        positivos="sum",
        pct="mean"
    )
)

v["pct"] *= 100

print(v.round(2).to_string())

print()

print("=== GV = 0 | GE > 0 ===")

z = (
    x.groupby("cod_razaorestricao")["GV_pos"]
    .agg(
        n="count",
        zeros=lambda s: (~s).sum(),
        pct_zero=lambda s: 100*(~s).mean()
    )
)

print(z.round(2).to_string())

print()

print("=== R = GV / GE | GE > 0 ===")

x["R"] = x["GV"] / x["GE"]

r = (
    x.groupby("cod_razaorestricao")["R"]
    .agg(
        n="count",
        median="median",
        mean="mean",
        p25=lambda s: s.quantile(.25),
        p75=lambda s: s.quantile(.75)
    )
)

print(r.round(4).to_string())

print()

print("=== GV = 0 POR ATIVO ===")

z2 = (
    x.groupby(["id_ons","cod_razaorestricao"])
    .agg(
        n=("GV","size"),
        gv_zero=("GV",lambda s:(s==0).sum()),
        pct_gv_zero=("GV",lambda s:100*(s==0).mean()),
        R_mediana=("R","median")
    )
    .reset_index()
)

print(
    z2[z2["n"] >= 5]
    .sort_values(["id_ons","cod_razaorestricao"])
    .round(3)
    .to_string(index=False)
)

print()

print("=== GF POSITIVO ===")

gf = (
    x.groupby("cod_razaorestricao")["GF"]
    .agg(
        n="count",
        gf_positivo=lambda s:(s>0).sum(),
        pct_gf_positivo=lambda s:100*(s>0).mean(),
        mediana="median",
        media="mean"
    )
)

print(gf.round(3).to_string())

print()

print("=== TESTE REL x ENE: ZERO GV ===")

rel = x[x["cod_razaorestricao"]=="REL"]
ene = x[x["cod_razaorestricao"]=="ENE"]

print(
    "REL GV=0:",
    round(100*(rel["GV"]==0).mean(),2),
    "%"
)

print(
    "ENE GV=0:",
    round(100*(ene["GV"]==0).mean(),2),
    "%"
)

print()

print("=== TESTE REL x ENE: R < 0.10 ===")

print(
    "REL:",
    round(100*(rel["R"]<0.10).mean(),2),
    "%"
)

print(
    "ENE:",
    round(100*(ene["R"]<0.10).mean(),2),
    "%"
)
