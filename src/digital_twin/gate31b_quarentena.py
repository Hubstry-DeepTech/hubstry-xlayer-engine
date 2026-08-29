"""
Gate 3.1b — Diagnostico da quarentena
=====================================
PROBLEMA
--------
O Gate 3.1 pos 12.332 de 41.483 linhas em quarentena (29,73%) por
apresentarem val_geracaolimitada - val_geracao < 0. Tratar quase um
terco do dataset como zero introduz vies na mesma direcao do erro
que levou ao abandono do dataset _detail_.

Alem disso, duas contas do mesmo dado divergiram por ordem de
grandeza: o replay somava ~1,2 TWh de corte mensal, o Gate 3.1
totalizou 397 GWh por episodio. Uma das duas esta errada.

HIPOTESES A TESTAR
------------------
H-A  As negativas se concentram em REL. Seria coerente com
     val_geracaoreferenciafinal existir apenas para REL: cada razao
     teria metodo de apuracao proprio, e limitada - geracao valeria
     so para ENE e CNF.

H-B  As negativas se concentram em poucos ativos. Indicaria problema
     de medicao ou de cadastro em usinas especificas, nao falha da
     formula.

H-C  Ha defasagem temporal entre val_geracaolimitada e val_geracao —
     o teto e publicado para o intervalo seguinte. Testavel deslocando
     a serie em um intervalo e medindo se as negativas caem.

H-D  A magnitude das negativas e pequena (ruido de arredondamento).
     Nesse caso o volume nao importa e a quarentena e inofensiva.

H-E  As negativas ocorrem quando a usina esta cortada mas o teto e
     reportado abaixo da geracao por outro criterio — nesse caso a
     coluna correta para esses casos seria val_disponibilidade.

REGRA
-----
Nenhuma conclusao deste script deve ser aceita por parecer razoavel.
Cada hipotese e avaliada por numero, e o script imprime o que
falsearia cada uma.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from . import ons_client as ons
except ImportError:
    import ons_client as ons

PREFIXO = "dataset/restricao_coff_eolica_tm/"
PASSO = pd.Timedelta(minutes=30)
PASSO_HORAS = 0.5

VAL_COLS = [
    "val_geracao", "val_geracaolimitada", "val_disponibilidade",
    "val_geracaoreferencia", "val_geracaoreferenciafinal",
]
COD_COLS = ["cod_razaorestricao", "cod_origemrestricao", "dsc_restricao"]


def para_numero(s: pd.Series) -> pd.Series:
    t = s.astype("string").str.strip()
    t = t.mask(t.isin(["", "-", "nan", "None"]))
    if t.str.contains(r"\d\.\d{3},", na=False).any():
        t = t.str.replace(".", "", regex=False)
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")


def carregar(ano: int, mes: int) -> pd.DataFrame:
    objs = ons.listar(PREFIXO, contendo=f"_{ano}_{mes:02d}.parquet")
    if not objs:
        raise FileNotFoundError(f"parquet de {ano}-{mes:02d} nao encontrado")
    df = pd.read_parquet(ons.baixar(objs[0].key))
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    for c in VAL_COLS:
        if c in df.columns:
            df[c] = para_numero(df[c])
    for c in COD_COLS:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    return df


def linha(txt: str = "") -> None:
    print("\n" + "-" * 72)
    if txt:
        print(txt)


if __name__ == "__main__":
    ANO, MES = 2025, 1
    df = carregar(ANO, MES)
    com = df[df["cod_razaorestricao"].notna()].dropna(
        subset=["val_geracaolimitada", "val_geracao"]
    ).copy()
    com["delta"] = com["val_geracaolimitada"] - com["val_geracao"]
    com["neg"] = com["delta"] < -1e-6

    n, nneg = len(com), int(com["neg"].sum())
    print(f"Linhas com restricao: {n:,}")
    print(f"Negativas (limitada < geracao): {nneg:,} ({nneg/n*100:.2f}%)")

    # ---------------- H-A: concentracao por razao ----------------
    linha("H-A  As negativas se concentram em REL?")
    t = com.groupby("cod_razaorestricao").agg(
        linhas=("neg", "size"),
        negativas=("neg", "sum"),
    )
    t["pct_negativas"] = (t["negativas"] / t["linhas"] * 100).round(1)
    t["share_do_total_neg"] = (t["negativas"] / nneg * 100).round(1)
    print(t.to_string())
    print("\n  Falsearia H-A: taxa de negativas parecida entre as razoes.")

    # ---------------- H-B: concentracao por ativo ----------------
    linha("H-B  As negativas se concentram em poucos ativos?")
    por_ativo = com.groupby("id_ons").agg(
        linhas=("neg", "size"), negativas=("neg", "sum")
    )
    por_ativo["pct"] = (por_ativo["negativas"] / por_ativo["linhas"] * 100)
    com_neg = por_ativo[por_ativo["negativas"] > 0].sort_values("negativas",
                                                               ascending=False)
    print(f"  ativos com ao menos uma negativa: {len(com_neg)} de {len(por_ativo)}")
    if len(com_neg):
        top10 = com_neg.head(10)["negativas"].sum()
        print(f"  os 10 piores concentram {top10:,} de {nneg:,} "
              f"({top10/nneg*100:.1f}%)")
        print(com_neg.head(10).round(1).to_string())
    print("\n  Falsearia H-B: negativas espalhadas por quase todos os ativos.")

    # ---------------- H-C: defasagem temporal ----------------
    linha("H-C  Ha defasagem de um intervalo entre teto e geracao?")
    d = com.sort_values(["id_ons", "din_instante"]).copy()
    g = d.groupby("id_ons", observed=True)
    for desloc in (-1, 1):
        col = f"lim_desl_{desloc}"
        d[col] = g["val_geracaolimitada"].shift(desloc)
        # so compara onde o intervalo vizinho e realmente adjacente
        passo_ok = g["din_instante"].diff().eq(PASSO) if desloc == 1 \
            else g["din_instante"].diff(-1).eq(-PASSO)
        delta_d = (d[col] - d["val_geracao"]).where(passo_ok)
        val = delta_d.dropna()
        if len(val):
            print(f"  deslocando teto em {desloc:+d} intervalo: "
                  f"{(val < -1e-6).mean()*100:5.2f}% negativas "
                  f"(base {len(val):,})")
    print(f"  sem deslocamento .......................: {nneg/n*100:5.2f}% negativas")
    print("\n  Confirmaria H-C: queda expressiva das negativas com deslocamento.")

    # ---------------- H-D: magnitude ----------------
    linha("H-D  As negativas sao ruido de arredondamento?")
    neg = com.loc[com["neg"], "delta"].abs()
    if len(neg):
        print(neg.describe(percentiles=[.5, .9, .99]).round(3).to_string())
        print(f"\n  abaixo de 0,1 MW ....: {(neg < 0.1).mean()*100:5.1f}%")
        print(f"  abaixo de 1 MW ......: {(neg < 1.0).mean()*100:5.1f}%")
        print(f"  acima de 10 MW ......: {(neg > 10).mean()*100:5.1f}%")
        print(f"  volume absoluto .....: {neg.sum():,.1f} MWmed "
              f"({neg.sum()*PASSO_HORAS/1000:,.1f} GWh)")
    print("\n  Confirmaria H-D: quase tudo abaixo de 1 MW.")

    # ---------------- H-E: disponibilidade como alternativa ----------------
    linha("H-E  Nas negativas, disponibilidade explica melhor?")
    sub = com[com["neg"]].copy()
    if len(sub):
        alt = sub["val_disponibilidade"] - sub["val_geracao"]
        print(f"  disponibilidade - geracao nas linhas negativas:")
        print(f"    negativas ainda: {(alt < -1e-6).mean()*100:5.1f}%")
        print(f"    soma positiva ..: {alt.clip(lower=0).sum():,.1f} MWmed")
        print(f"  comparacao de colunas (medianas nas linhas negativas):")
        print(sub[["val_geracao", "val_geracaolimitada",
                   "val_disponibilidade"]].median().round(2).to_string())
    print("\n  Confirmaria H-E: disponibilidade - geracao quase sem negativas.")

    # ---------------- Impacto no total ----------------
    linha("IMPACTO: quanto a escolha muda o corte do mes")
    pos_only = com["delta"].clip(lower=0).sum() * PASSO_HORAS / 1000
    bruto = com["delta"].sum() * PASSO_HORAS / 1000
    disp = (com["val_disponibilidade"] - com["val_geracao"]).clip(lower=0).sum() \
        * PASSO_HORAS / 1000
    ger = df["val_geracao"].sum() * PASSO_HORAS / 1000
    print(f"  geracao eolica no mes .................. {ger:9,.1f} GWh")
    print(f"  corte, truncando negativas em zero ..... {pos_only:9,.1f} GWh "
          f"({pos_only/ger*100:.1f}%)")
    print(f"  corte, somando delta bruto ............. {bruto:9,.1f} GWh "
          f"({bruto/ger*100:.1f}%)")
    print(f"  corte por disponibilidade - geracao .... {disp:9,.1f} GWh "
          f"({disp/ger*100:.1f}%)")
    print(f"\n  vies do truncamento: {(pos_only - bruto)/pos_only*100:.1f}%")
    print("  Referencia publica: 20,6% para eolica + solar em 2025 inteiro.")
    print("  ATENCAO: nao aceitar uma formula porque o percentual se")
    print("  aproxima dessa referencia. Ja erramos assim uma vez.")

    # ---------------- Amostra ----------------
    linha("AMOSTRA de negativas de grande magnitude")
    cols = ["din_instante", "nom_usina", "cod_razaorestricao",
            "cod_origemrestricao", "val_geracao", "val_geracaolimitada",
            "val_disponibilidade", "delta"]
    cols = [c for c in cols if c in com.columns]
    print(com[com["neg"]].nsmallest(10, "delta")[cols].to_string(index=False))
