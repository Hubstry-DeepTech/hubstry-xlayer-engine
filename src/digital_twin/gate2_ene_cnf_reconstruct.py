import pandas as pd

p = r".\data\ons\RESTRICAO_COFF_EOLICA_2025_01.parquet"

df = pd.read_parquet(p)

for c in [
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
]:
    df[c] = pd.to_numeric(df[c].replace("", pd.NA), errors="coerce")

df = df[
    df["cod_razaorestricao"].isin(["ENE", "CNF"])
].copy()

df["delta_limitada"] = (
    df["val_geracaolimitada"] -
    df["val_geracao"]
)

df["tolerancia"] = (
    0.05 * df["val_geracaolimitada"]
).clip(upper=5.0)

df["criterio_atendido"] = (
    df["delta_limitada"] <= df["tolerancia"]
)

df["referencia_base"] = df[
    ["val_geracaoreferencia", "val_disponibilidade"]
].min(axis=1)

df["referencia_final_reconstruida"] = (
    df["referencia_base"]
    .where(df["criterio_atendido"], 0.0)
)

print("=== ENE + CNF: RECONSTRUCAO EXPERIMENTAL ===")
print()

print(
    df.groupby("cod_razaorestricao")[
        "criterio_atendido"
    ].agg(["count", "sum", "mean"])
)

print()
print(
    "Observacao: ENE/CNF nao possuem "
    "val_geracaoreferenciafinal publicado neste dataset."
)
print()

print("=== DISTRIBUICAO DA REFERENCIA FINAL RECONSTRUIDA ===")

print(
    df.groupby("cod_razaorestricao")[
        "referencia_final_reconstruida"
    ].agg([
        "count",
        "min",
        "median",
        "mean",
        "max"
    ]).to_string()
)
