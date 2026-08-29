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

df = df[df["cod_razaorestricao"] == "REL"].copy()

df["delta_limitada"] = (
    df["val_geracaolimitada"] -
    df["val_geracao"]
)

df["tolerancia_5pct"] = (
    0.05 * df["val_geracaolimitada"]
)

df["tolerancia_5mw"] = 5.0

df["tolerancia_aplicavel"] = df[
    ["tolerancia_5pct", "tolerancia_5mw"]
].min(axis=1)

df["criterio_atendido"] = (
    df["delta_limitada"] <= df["tolerancia_aplicavel"]
)

df["referencia_base"] = df[
    ["val_geracaoreferencia", "val_disponibilidade"]
].min(axis=1)

df["referencia_final_v2"] = (
    df["referencia_base"]
    .where(df["criterio_atendido"], 0.0)
)

df["erro"] = (
    df["referencia_final_v2"] -
    df["val_geracaoreferenciafinal"]
)

print("=== TESTE REV06 V2 ===")
print()

print("REL:", len(df))
print(
    "criterio atendido:",
    int(df["criterio_atendido"].sum()),
    "(",
    round(100 * df["criterio_atendido"].mean(), 2),
    "%)"
)

print(
    "criterio nao atendido:",
    int((~df["criterio_atendido"]).sum())
)

print()

erro = df["erro"]

print("=== COMPARACAO COM ONS ===")
print("erro absoluto max:", float(erro.abs().max()))
print("erro absoluto mediano:", float(erro.abs().median()))
print("erro medio:", float(erro.mean()))
print(
    "matches < 0.001 MW:",
    int((erro.abs() < 0.001).sum()),
    "/",
    len(df)
)

print()

print("=== DIVERGENCIAS ===")

cols = [
    "din_instante",
    "nom_usina",
    "val_geracao",
    "val_geracaolimitada",
    "delta_limitada",
    "tolerancia_aplicavel",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
    "criterio_atendido",
    "referencia_final_v2",
    "erro",
]

print(
    df[df["erro"].abs() >= 0.001]
    .sort_values("erro", key=lambda s: s.abs(), ascending=False)
    [cols]
    .head(30)
    .to_string(index=False)
)
