import pandas as pd

p = r".\data\ons\RESTRICAO_COFF_EOLICA_2025_01.parquet"

df = pd.read_parquet(p)

cols = [
    "val_geracao",
    "val_geracaolimitada",
    "val_disponibilidade",
    "val_geracaoreferencia",
    "val_geracaoreferenciafinal",
]

for c in cols:
    df[c] = pd.to_numeric(
        df[c].replace("", pd.NA),
        errors="coerce"
    )

df = df[df["cod_razaorestricao"].isin(["ENE", "CNF", "REL"])].copy()

def resumo(g):
    return pd.Series({
        "n": len(g),

        "geracao_zero_pct":
            100 * (g["val_geracao"] == 0).sum() / len(g),

        "limitada_zero_pct":
            100 * (g["val_geracaolimitada"] == 0).sum() / len(g),

        "disponibilidade_zero_pct":
            100 * (g["val_disponibilidade"] == 0).sum() / len(g),

        "referencia_zero_pct":
            100 * (g["val_geracaoreferencia"] == 0).sum() / len(g),

        "referenciafinal_zero_pct":
            100 * (g["val_geracaoreferenciafinal"] == 0).sum() / len(g),

        "geracao_maior_disponibilidade_pct":
            100 * (
                g["val_geracao"] >
                g["val_disponibilidade"]
            ).sum() / len(g),

        "geracao_maior_limitada_pct":
            100 * (
                g["val_geracao"] >
                g["val_geracaolimitada"]
            ).sum() / len(g),

        "limitada_maior_disponibilidade_pct":
            100 * (
                g["val_geracaolimitada"] >
                g["val_disponibilidade"]
            ).sum() / len(g),

        "referencia_maior_geracao_pct":
            100 * (
                g["val_geracaoreferencia"] >
                g["val_geracao"]
            ).sum() / len(g),

        "referenciafinal_maior_geracao_pct":
            100 * (
                g["val_geracaoreferenciafinal"] >
                g["val_geracao"]
            ).sum() / len(g),
    }).round(2)

print("=== RELACOES ESTRUTURAIS POR RAZAO ===")
print()

resultado = df.groupby("cod_razaorestricao").apply(
    resumo,
    include_groups=False
)

print(resultado.to_string())
