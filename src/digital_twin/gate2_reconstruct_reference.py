import pandas as pd
import numpy as np

p = r".\data\ons\RESTRICAO_COFF_EOLICA_2025_01.parquet"

df = pd.read_parquet(p)

NUMERICOS = [
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
]

for c in NUMERICOS:
    df[c + "_num"] = pd.to_numeric(
        df[c].replace("", pd.NA),
        errors="coerce"
    )

df = df[
    df["cod_razaorestricao"].isin(["ENE", "CNF", "REL"])
].copy()

# Hiptese de reconstruo da metodologia histrica pr-01/08/2025.
#
# IMPORTANTE:
# isto ainda NO  declarado como implementao oficial.
#  uma reproduo experimental para ser confrontada
# com val_geracaoreferenciafinal nos registros REL.

df["referencia_base"] = df[
    ["val_geracaoreferencia_num", "val_disponibilidade_num"]
].min(axis=1)

# Critrio histrico descrito na documentao tcnica:
# gerao > 95% da gerao limitada.
#
# Como o ONS permite gerao limitada igual a zero,
# evitamos diviso e tratamos explicitamente esse caso.

criterio_tolerancia = (
    df["val_geracaolimitada_num"].notna()
    & (
        df["val_geracao_num"]
        > 0.95 * df["val_geracaolimitada_num"]
    )
)

df["referencia_final_reconstruida"] = np.where(
    criterio_tolerancia,
    np.where(
        df["referencia_base"] > df["val_geracao_num"],
        df["referencia_base"],
        0.0
    ),
    0.0
)

# Comparao somente onde o ONS publicou
# val_geracaoreferenciafinal: REL.

rel = df[
    df["cod_razaorestricao"] == "REL"
].copy()

rel["erro_reconstrucao"] = (
    rel["referencia_final_reconstruida"]
    - rel["val_geracaoreferenciafinal_num"]
)

print("=== RECONSTRUCAO EXPERIMENTAL DA REFERENCIA FINAL ===")
print()

print("REL total:", len(rel))
print(
    "REL com referencia final oficial:",
    int(rel["val_geracaoreferenciafinal_num"].notna().sum())
)
print()

erro = rel["erro_reconstrucao"].dropna()

print("=== ERRO CONTRA O VALOR PUBLICADO PELO ONS ===")
print("n:", len(erro))
print("erro absoluto max:", float(erro.abs().max()))
print("erro absoluto mediano:", float(erro.abs().median()))
print("erro medio:", float(erro.mean()))
print(
    "matches exatos:",
    int((erro.abs() < 1e-9).sum()),
    "/",
    len(erro)
)
print(
    "matches tolerancia 0.001 MW:",
    int((erro.abs() < 0.001).sum()),
    "/",
    len(erro)
)
print()

print("=== EXEMPLOS DE DIVERGENCIA ===")

cols = [
    "din_instante",
    "nom_usina",
    "val_geracao_num",
    "val_geracaolimitada_num",
    "val_disponibilidade_num",
    "val_geracaoreferencia_num",
    "val_geracaoreferenciafinal_num",
    "referencia_base",
    "referencia_final_reconstruida",
    "erro_reconstrucao",
]

div = rel[
    rel["erro_reconstrucao"].abs() >= 0.001
]

print(
    div[cols]
    .sort_values("erro_reconstrucao", key=lambda s: s.abs(), ascending=False)
    .head(30)
    .to_string(index=False)
)
