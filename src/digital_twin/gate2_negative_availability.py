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
    df[c + "_num"] = pd.to_numeric(
        df[c].replace("", pd.NA),
        errors="coerce"
    )

df = df[df["cod_razaorestricao"].isin(["ENE", "CNF", "REL"])].copy()

df["availability_minus_generation"] = (
    df["val_disponibilidade_num"] -
    df["val_geracao_num"]
)

neg = df[df["availability_minus_generation"] < 0].copy()

print("=== NEGATIVOS: DISPONIBILIDADE - GERACAO ===")
print("total:", len(neg))
print()

print("=== POR RAZAO ===")
print(neg["cod_razaorestricao"].value_counts())
print()

print("=== POR USINA ===")
print(neg["nom_usina"].value_counts().head(30))
print()

print("=== EXEMPLOS ===")
cols = [
    "din_instante",
    "nom_usina",
    "cod_razaorestricao",
    "cod_origemrestricao",
    "val_geracao",
    "val_disponibilidade",
    "val_geracaolimitada",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
]
print(neg[cols].head(30).to_string(index=False))
