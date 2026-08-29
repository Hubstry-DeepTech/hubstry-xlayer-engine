import pandas as pd
import numpy as np

p1 = r".\data\ons\RESTRICAO_COFF_EOLICA_2025_01.parquet"
p2 = r".\data\ons\RESTRICAO_COFF_EOLICA_DETAIL_2025_01.parquet"

a = pd.read_parquet(p1)
b = pd.read_parquet(p2)

ids = sorted(set(a["id_ons"].dropna()) & set(b["id_ons"].dropna()))

a = a[a["id_ons"].isin(ids)].copy()
b = b[b["id_ons"].isin(ids)].copy()

# COFF = qualquer uma das tres razoes estudadas
a["COFF"] = a["cod_razaorestricao"].isin(["ENE", "CNF", "REL"])

cols = [
    "val_ventoverificado",
    "val_geracaoestimada",
    "val_geracaoverificada",
]

b[cols] = b[cols].apply(pd.to_numeric, errors="coerce")
b["GF"] = b["val_geracaoestimada"] - b["val_geracaoverificada"]

# Junta a classificacao COFF ao DETAIL
m = b.merge(
    a[["id_ons", "din_instante", "COFF"]],
    on=["id_ons", "din_instante"],
    how="left",
)

m["COFF"] = m["COFF"].fillna(False)

# Faixas de vento
m["vento_bin"] = pd.cut(
    m["val_ventoverificado"],
    bins=[-0.001, 4, 6, 8, 10, 12, 15, 100],
    include_lowest=True,
)

# Estatisticas por ativo x regime x faixa de vento
q = (
    m.groupby(
        ["id_ons", "COFF", "vento_bin"],
        observed=True
    )
    .agg(
        n=("val_geracaoverificada", "size"),
        vento=("val_ventoverificado", "mean"),
        GE=("val_geracaoestimada", "mean"),
        GV=("val_geracaoverificada", "mean"),
        GF=("GF", "mean"),
    )
    .reset_index()
)

# Pivot sem f-string problematico
z = q.pivot_table(
    index=["id_ons", "vento_bin"],
    columns="COFF",
    values=["n", "vento", "GE", "GV", "GF"],
)

# Renomeia explicitamente
novas_colunas = []

for coluna, regime in z.columns:
    if regime is True:
        nome_regime = "COFF"
    else:
        nome_regime = "NAO"
    novas_colunas.append(coluna + "_" + nome_regime)

z.columns = novas_colunas
z = z.reset_index()

# Precisamos dos dois grupos para calcular diferenca
necessarias = [
    "n_COFF",
    "n_NAO",
    "vento_COFF",
    "vento_NAO",
    "GE_COFF",
    "GE_NAO",
    "GV_COFF",
    "GV_NAO",
    "GF_COFF",
    "GF_NAO",
]

for c in necessarias:
    if c not in z.columns:
        z[c] = np.nan

z["delta_GV"] = z["GV_COFF"] - z["GV_NAO"]
z["delta_GF"] = z["GF_COFF"] - z["GF_NAO"]

z = z[
    z["n_COFF"].notna()
    & z["n_NAO"].notna()
].copy()

print("=== WITHIN-ASSET: COFF VS NAO-COFF ===")
print()

cols_saida = [
    "id_ons",
    "vento_bin",
    "n_COFF",
    "n_NAO",
    "vento_COFF",
    "vento_NAO",
    "GE_COFF",
    "GE_NAO",
    "GV_COFF",
    "GV_NAO",
    "delta_GV",
    "GF_COFF",
    "GF_NAO",
    "delta_GF",
]

print(
    z[cols_saida]
    .round(3)
    .to_string(index=False)
)

print()
print("=== RESUMO POR ATIVO ===")
print()

resumo = (
    z.groupby("id_ons")
    .agg(
        n_bins=("vento_bin", "size"),
        delta_GV_med=("delta_GV", "median"),
        delta_GV_mean=("delta_GV", "mean"),
        delta_GV_neg_pct=(
            "delta_GV",
            lambda s: 100 * (s < 0).mean()
        ),
        delta_GF_med=("delta_GF", "median"),
    )
    .round(3)
)

print(resumo.to_string())
