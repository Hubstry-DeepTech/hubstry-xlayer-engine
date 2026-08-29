"""
Calibragem v3 — identificar a formula do corte
==============================================
A v2 derrubou a hipotese de que val_geracaolimitada e o corte: na
amostra ela aparece na mesma ordem de grandeza da geracao
(311,196 contra 298,631), o que caracteriza um TETO imposto pela
restricao, nao um montante cortado.

Descoberta estrutural da v2: val_geracaoreferenciafinal tem
exatamente 14.666 valores nao nulos, o mesmo numero de linhas REL.
A referencia final so e preenchida para restricao por
indisponibilidade externa eletrica. Isso indica que cada razao de
restricao tem metodo de apuracao proprio — uma formula unica para
todas seria errada por construcao.

Esta rodada testa os candidatos a corte e aplica uma ancora de
plausibilidade: converte MWmed para MWh e compara com a ordem de
grandeza publica do curtailment brasileiro.
"""

from __future__ import annotations

import pandas as pd

try:
    from . import ons_client as ons
except ImportError:
    import ons_client as ons

PREFIXO_AGG = "dataset/restricao_coff_eolica_tm/"
ANO, MES = 2025, 1
PASSO_HORAS = 0.5

VAL_COLS = [
    "val_geracao", "val_geracaolimitada", "val_disponibilidade",
    "val_geracaoreferencia", "val_geracaoreferenciafinal",
]


def para_numero(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip()
    t = t.mask(t.isin(["", "-", "nan", "None"]))
    if t.str.contains(r"\d\.\d{3},", na=False).any():
        t = t.str.replace(".", "", regex=False)
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")


def carregar() -> pd.DataFrame:
    objs = ons.listar(PREFIXO_AGG, contendo=f"_{ANO}_{MES:02d}.parquet")
    if not objs:
        raise FileNotFoundError("parquet agregado nao encontrado")
    df = pd.read_parquet(ons.baixar(objs[0].key))
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    for c in VAL_COLS:
        if c in df.columns:
            df[c] = para_numero(df[c])
    for c in ("cod_razaorestricao", "cod_origemrestricao"):
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    return df


def avaliar(nome: str, serie: pd.Series, razao: pd.Series) -> None:
    """Um candidato a corte: volume, sinal e plausibilidade."""
    valido = serie.dropna()
    if valido.empty:
        print(f"{nome:.<44} sem dados")
        return
    pos = valido.clip(lower=0)
    twh = pos.sum() * PASSO_HORAS / 1e6
    neg_pct = (valido < -1e-6).mean() * 100
    print(f"{nome:.<44} {twh:8.3f} TWh   negativas {neg_pct:5.1f}%   "
          f"n={len(valido):,}")
    if neg_pct > 5:
        print(f"{'':46}ALERTA: muitas negativas — formula provavelmente errada")
    # quebra por razao
    por = (
        pd.DataFrame({"v": pos, "r": razao})
        .dropna(subset=["r"])
        .groupby("r")["v"]
        .sum()
    )
    if len(por):
        total = por.sum()
        detalhe = "  ".join(f"{k}={v/total*100:.1f}%" for k, v in por.items())
        print(f"{'':46}{detalhe}")


if __name__ == "__main__":
    df = carregar()
    com = df[df["cod_razaorestricao"].notna()].copy()
    print(f"Linhas com restricao: {len(com):,} de {len(df):,}\n")

    print("Preenchimento de cada coluna, por razao:")
    tab = com.groupby("cod_razaorestricao")[VAL_COLS].apply(
        lambda g: g.notna().sum()
    )
    print(tab.to_string())

    print("\n--- Candidatos a corte (TWh no mes) ---")
    r = com["cod_razaorestricao"]
    avaliar("C1  referencia - geracao", com["val_geracaoreferencia"] - com["val_geracao"], r)
    avaliar("C2  disponibilidade - geracao", com["val_disponibilidade"] - com["val_geracao"], r)
    avaliar("C3  limitada - geracao", com["val_geracaolimitada"] - com["val_geracao"], r)
    avaliar("C4  referenciafinal - geracao", com["val_geracaoreferenciafinal"] - com["val_geracao"], r)
    avaliar("C5  disponibilidade - limitada", com["val_disponibilidade"] - com["val_geracaolimitada"], r)
    avaliar("C6  referencia - limitada", com["val_geracaoreferencia"] - com["val_geracaolimitada"], r)

    print("\n--- Ancora de plausibilidade ---")
    ger_twh = df["val_geracao"].sum() * PASSO_HORAS / 1e6
    print(f"Geracao eolica total no mes ........ {ger_twh:8.3f} TWh")
    print("Referencia publica: cerca de 37 TWh de eolica + solar cortados")
    print("em 2025 inteiro. Um mes de eolica deve ficar bem abaixo disso.")
    print("Candidato que exceda a propria geracao do mes esta errado.")

    print("\n--- Comportamento por razao, medianas ---")
    print(com.groupby("cod_razaorestricao")[VAL_COLS].median().to_string())
