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

b[
    [
        "val_geracaoestimada",
        "val_geracaoverificada",
        "val_ventoverificado"
    ]
] = b[
    [
        "val_geracaoestimada",
        "val_geracaoverificada",
        "val_ventoverificado"
    ]
].apply(pd.to_numeric, errors="coerce")

# Junta COFF à série temporal completa
m = b.merge(
    a[
        [
            "id_ons",
            "din_instante",
            "COFF",
            "cod_razaorestricao"
        ]
    ],
    on=["id_ons", "din_instante"],
    how="left"
)

m["COFF"] = m["COFF"].fillna(False)

m = m.sort_values(
    ["id_ons", "din_instante"]
).copy()

# ============================================================
# EPISODIOS: construir ANTES de qualquer filtro GE
# ============================================================

m["prev_coff"] = (
    m.groupby("id_ons")["COFF"]
    .shift(1)
    .fillna(False)
)

m["novo_ep"] = (
    m["COFF"] &
    (~m["prev_coff"])
)

m["ep_id"] = (
    m.groupby("id_ons")["novo_ep"]
    .cumsum()
)

episodios = (
    m[m["COFF"]]
    .groupby(["id_ons", "ep_id"])
    .agg(
        inicio=("din_instante", "min"),
        fim=("din_instante", "max"),
        n_intervalos=("COFF", "size")
    )
    .reset_index()
)

episodios["duracao_horas"] = (
    episodios["n_intervalos"] * 0.5
)

print("=== GATE 2.9 CORRIGIDO ===")
print()
print("episodios:", len(episodios))
print("observacoes COFF:", int(m["COFF"].sum()))
print()

print("=== DISTRIBUICAO DOS EPISODIOS ===")

print(
    episodios["n_intervalos"]
    .describe(
        percentiles=[
            .25,
            .50,
            .75,
            .90,
            .95,
            .99
        ]
    )
    .round(2)
    .to_string()
)

print()

print("=== DURACAO DOS EPISODIOS ===")

print(
    episodios["n_intervalos"]
    .value_counts()
    .sort_index()
    .head(30)
    .to_string()
)

print()

# ============================================================
# REALIZACAO
# ============================================================

m["GE"] = m["val_geracaoestimada"]
m["GV"] = m["val_geracaoverificada"]

m["R"] = (
    m["GV"] /
    m["GE"].replace(0, np.nan)
)

# Apenas para analisar realização
r = m[
    m["COFF"] &
    (m["GE"] >= 5)
].copy()

print("=== REALIZACAO DURANTE COFF ===")
print("n:", len(r))
print(
    r["R"]
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

# ============================================================
# EPISODIOS LONGOS
# ============================================================

longos = episodios[
    episodios["n_intervalos"] >= 4
].copy()

print("=== EPISODIOS >= 4 INTERVALOS ===")
print("quantidade:", len(longos))

if len(longos):
    print()
    print(
        longos
        .sort_values("n_intervalos", ascending=False)
        .head(30)
        .to_string(index=False)
    )

print()

print("=== EPISODIOS >= 8 INTERVALOS ===")
print(
    int(
        (episodios["n_intervalos"] >= 8).sum()
    )
)

print()

print("=== EPISODIOS >= 16 INTERVALOS ===")
print(
    int(
        (episodios["n_intervalos"] >= 16).sum()
    )
)
