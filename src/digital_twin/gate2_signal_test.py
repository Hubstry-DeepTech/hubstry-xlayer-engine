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
    df[c + "_num"] = pd.to_numeric(
        df[c].replace("", pd.NA),
        errors="coerce"
    )

df = df[df["cod_razaorestricao"].isin(["ENE", "CNF", "REL"])].copy()

tests = {
    "limited_minus_generation":
        df["val_geracaolimitada_num"] - df["val_geracao_num"],

    "availability_minus_generation":
        df["val_disponibilidade_num"] - df["val_geracao_num"],

    "reference_minus_generation":
        df["val_geracaoreferencia_num"] - df["val_geracao_num"],

    "referencefinal_minus_generation":
        df["val_geracaoreferenciafinal_num"] - df["val_geracao_num"],
}

print("=== PERCENTUAIS DE SINAL POR RAZAO ===")

for name, s in tests.items():

    tmp = pd.DataFrame({
        "valor": s,
        "razao": df["cod_razaorestricao"],
    }).dropna(subset=["valor"])

    g = tmp.groupby("razao")["valor"]

    n = g.count()
    negativos = g.apply(lambda x: (x < 0).sum())
    zeros = g.apply(lambda x: (x == 0).sum())
    positivos = g.apply(lambda x: (x > 0).sum())

    resultado = pd.DataFrame({
        "n": n,
        "negativos": negativos,
        "zeros": zeros,
        "positivos": positivos,
        "pct_negativos": (100 * negativos / n).round(2),
        "pct_zeros": (100 * zeros / n).round(2),
        "pct_positivos": (100 * positivos / n).round(2),
    })

    print()
    print(name)
    print(resultado.to_string())
