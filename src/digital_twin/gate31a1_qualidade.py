"""
Gate 3.1A.1 — Qualidade do dado de disponibilidade
==================================================
ORIGEM DESTE GATE
-----------------
No evento de 2025-01-13 15:00, os 8 conjuntos (de 142) em que os dois
baselines normativos divergem tinham TODOS val_disponibilidade == 0
com val_geracao > 0.

Mecanica: o baseline B (NT-ONS DOP 0022/2025, secao 5.1.2-IV) rateia
por disponibilidade. Disponibilidade zero significa peso zero — o
parque sai do rateio e nao recebe corte algum. O baseline A (secao
6.1) rateia por ponto de partida, que nesses casos e a geracao. Dai a
divergencia ser exatamente igual ao valor do baseline A.

O QUE ESTE GATE TESTA
---------------------
Aquilo foi observado em UM instante. Este gate mede se e episodico ou
estrutural, no mes inteiro:

  1. frequencia de (disponibilidade == 0 E geracao > 0)
  2. quantos ativos, quanta energia, qual distribuicao temporal
  3. distribuicao por razao de restricao
  4. TESTE DECISIVO: entre todas as observacoes com essa
     inconsistencia, que proporcao produz divergencia entre os
     baselines? E que proporcao da divergencia total elas explicam?

O QUE ESTE GATE NAO AFIRMA
--------------------------
Que disponibilidade zero com geracao positiva e "erro de dado".

E uma INCONSISTENCIA ENTRE CAMPOS PUBLICADOS — isso os numeros
sustentam. A causa nao: pode ser semantica da coluna, defasagem
temporal entre medicoes, artefato do processo de apuracao ou falha de
preenchimento. Nenhuma dessas hipoteses foi testada.

CONSEQUENCIA ARQUITETURAL
-------------------------
Se a concentracao se confirmar, o achado nao e "ha registros
inconsistentes". E que A ESCOLHA ENTRE CRITERIOS NORMATIVOS DE RATEIO
E SENSIVEL A UMA CONDICAO DE QUALIDADE DE DADO IDENTIFICAVEL — o
rateio por disponibilidade falha silenciosamente quando a
disponibilidade esta mal declarada.

Isso implica uma camada de confianca no Observation Engine:

  dado publicado -> consistencia interna -> confianca do sinal
  -> heuristica -> alocacao -> human-in-the-loop

O motor nao deve consumir val_disponibilidade como verdade.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from . import gate31_persistencia as g31
except ImportError:
    import gate31_persistencia as g31

from baseline_ons import Usina, rateio_proporcional

PASSO_HORAS = 0.5


def marcar_inconsistencia(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["disp_zero_ger_positiva"] = (
        (out["val_disponibilidade"].fillna(-1) == 0) & (out["val_geracao"] > 0)
    )
    return out


def divergencia_no_instante(recorte: pd.DataFrame) -> pd.DataFrame:
    """Aplica os dois baselines a um patamar e devolve a divergencia."""
    usinas = [
        Usina(id_ons=str(r.id_ons), nome=str(r.nom_usina),
              disponibilidade_mw=float(r.val_disponibilidade),
              geracao_mw=float(r.val_geracao),
              limite_atual_mw=float(r.val_geracaolimitada))
        for r in recorte.itertuples()
    ]
    total = float(recorte["corte_mw"].sum())
    if total <= 0 or not usinas:
        return pd.DataFrame()
    a = rateio_proporcional(usinas, total, base="ponto_de_partida")
    b = rateio_proporcional(usinas, total, base="disponibilidade")
    return pd.DataFrame([{
        "id_ons": u.id_ons,
        "din_instante": recorte["din_instante"].iloc[0],
        "divergencia": abs(a.corte_por_usina.get(u.id_ons, 0.0)
                           - b.corte_por_usina.get(u.id_ons, 0.0)),
    } for u in usinas])


if __name__ == "__main__":
    ANO, MES = 2025, 1
    print(f"Carregando COFF eolica {ANO}-{MES:02d}...")
    df = marcar_inconsistencia(g31.calcular_corte(g31.carregar(ANO, MES)))

    n = len(df)
    inc = df[df["disp_zero_ger_positiva"]]

    print("\n" + "=" * 72)
    print("1. FREQUENCIA DA INCONSISTENCIA (disponibilidade = 0 e geracao > 0)")
    print("=" * 72)
    print(f"  observacoes com restricao ........ {n:,}")
    print(f"  com inconsistencia ............... {len(inc):,} "
          f"({len(inc)/n*100:.2f}%)")
    print(f"  ativos afetados .................. {inc['id_ons'].nunique()} "
          f"de {df['id_ons'].nunique()}")
    if len(inc):
        print(f"  geracao envolvida ................ "
              f"{inc['val_geracao'].sum()*PASSO_HORAS:,.1f} MWh")
        print(f"  corte envolvido .................. "
              f"{inc['corte_mwh'].sum():,.1f} MWh "
              f"({inc['corte_mwh'].sum()/df['corte_mwh'].sum()*100:.1f}% do total)")

    if not len(inc):
        print("\n  Nenhuma ocorrencia no mes. O caso do evento analisado")
        print("  seria entao pontual — verificar o recorte usado.")
        raise SystemExit(0)

    print("\n" + "=" * 72)
    print("2. ATIVOS MAIS AFETADOS")
    print("=" * 72)
    por_ativo = (
        df.groupby(["id_ons", "nom_usina"])
        .agg(obs=("disp_zero_ger_positiva", "size"),
             inconsistentes=("disp_zero_ger_positiva", "sum"))
    )
    por_ativo["pct"] = (por_ativo["inconsistentes"] / por_ativo["obs"] * 100).round(1)
    afetados = por_ativo[por_ativo["inconsistentes"] > 0] \
        .sort_values("inconsistentes", ascending=False)
    print(afetados.head(15).to_string())

    print("\n" + "=" * 72)
    print("3. DISTRIBUICAO POR RAZAO E NO TEMPO")
    print("=" * 72)
    tab = (
        df.groupby("cod_razaorestricao")
        .agg(obs=("disp_zero_ger_positiva", "size"),
             inconsistentes=("disp_zero_ger_positiva", "sum"))
    )
    tab["pct_da_razao"] = (tab["inconsistentes"] / tab["obs"] * 100).round(1)
    print(tab.to_string())

    por_dia = inc.groupby(inc["din_instante"].dt.date).size()
    print(f"\n  dias com ocorrencia: {len(por_dia)} de "
          f"{df['din_instante'].dt.date.nunique()}")
    print(f"  concentracao: os 5 piores dias respondem por "
          f"{por_dia.nlargest(5).sum()/len(inc)*100:.1f}%")
    print("\n  ocorrencias por dia (10 maiores):")
    print(por_dia.nlargest(10).to_string())

    print("\n" + "=" * 72)
    print("4. TESTE DECISIVO — a inconsistencia explica a divergencia?")
    print("=" * 72)
    print("  Aplicando os dois baselines a cada patamar do mes...")

    partes = []
    instantes = sorted(df["din_instante"].unique())
    for i, t in enumerate(instantes):
        recorte = df[df["din_instante"] == t]
        if len(recorte) < 2:
            continue
        d = divergencia_no_instante(recorte)
        if len(d):
            partes.append(d)
        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{len(instantes)} patamares")

    if not partes:
        print("  sem divergencias calculaveis")
        raise SystemExit(0)

    div = pd.concat(partes, ignore_index=True)
    base = df[["id_ons", "din_instante", "disp_zero_ger_positiva",
               "corte_mwh", "cod_razaorestricao"]]
    m = div.merge(base, on=["id_ons", "din_instante"], how="left")
    m["tem_divergencia"] = m["divergencia"] > 0.01

    total_div = m["divergencia"].sum()
    inc_m = m[m["disp_zero_ger_positiva"] == True]
    lim_m = m[m["disp_zero_ger_positiva"] != True]

    print(f"\n  observacoes avaliadas ............ {len(m):,}")
    print(f"  com divergencia .................. {int(m['tem_divergencia'].sum()):,} "
          f"({m['tem_divergencia'].mean()*100:.2f}%)")

    print(f"\n  PROPORCAO QUE PRODUZ DIVERGENCIA:")
    if len(inc_m):
        print(f"    com inconsistencia ............ "
              f"{inc_m['tem_divergencia'].mean()*100:5.1f}%  (n={len(inc_m):,})")
    print(f"    sem inconsistencia ............ "
          f"{lim_m['tem_divergencia'].mean()*100:5.1f}%  (n={len(lim_m):,})")

    print(f"\n  PROPORCAO DA DIVERGENCIA TOTAL EXPLICADA:")
    if total_div > 0:
        print(f"    por observacoes inconsistentes  "
              f"{inc_m['divergencia'].sum()/total_div*100:5.1f}%")
        print(f"    pelas demais .................. "
              f"{lim_m['divergencia'].sum()/total_div*100:5.1f}%")

    print("\n--- Leitura ---")
    if total_div > 0 and inc_m['divergencia'].sum() / total_div > 0.8:
        print("  CONCENTRACAO ALTA. A escolha entre os criterios normativos de")
        print("  rateio e sensivel a uma condicao de qualidade de dado")
        print("  identificavel: o rateio por disponibilidade falha")
        print("  silenciosamente quando a disponibilidade esta mal declarada.")
    else:
        print("  CONCENTRACAO BAIXA OU MODERADA. A divergencia entre baselines")
        print("  tem outras fontes alem da inconsistencia de disponibilidade.")
        print("  Investigar antes de generalizar o achado do evento isolado.")

    print("\n  Este gate estabelece INCONSISTENCIA ENTRE CAMPOS PUBLICADOS.")
    print("  NAO estabelece a causa: pode ser semantica da coluna, defasagem")
    print("  temporal, artefato de apuracao ou falha de preenchimento.")
    print("  Nenhuma dessas hipoteses foi testada aqui.")
