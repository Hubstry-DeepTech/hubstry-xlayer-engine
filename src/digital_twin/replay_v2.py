"""
Hubstry X-Layer Engine — Replay historico (shadow mode) v2
=========================================================
Reconstroi eventos reais de restricao de operacao a partir do corte
APURADO pelo ONS e os converte em blocos de excedente para o
otimizador.

FONTE
-----
dataset/restricao_coff_eolica_tm/  (agregado, 3,2 MB/mes em parquet)

Substitui a v1, que usava o dataset _detail_ e derivava o corte de
(val_geracaoestimada - val_geracaoverificada). Aquele metodo tinha
36,1% de vies de truncamento em janeiro de 2025 e nao distinguia
corte de erro da curva vento x potencia.

COLUNA DE CORTE: val_geracaolimitada
------------------------------------
Evidencia da calibragem (janeiro de 2025):
  - soma 2.465.707 MWmed = 1,233 TWh em base semi-horaria
  - geracao eolica no mes: 5,571 TWh
  - taxa resultante: 18,1%, coerente com os 20,6% apurados para
    eolica + solar em 2025 inteiro
  - zero valores negativos em 41.483 linhas
  - preenchida apenas onde ha restricao declarada

Candidata descartada: (val_disponibilidade - val_geracao) passou no
teste de sinal com 4,7% de negativas, mas e fisicamente errada.
Disponibilidade e capacidade disponivel, nao potencial eolico: uma
usina de 200 MW gerando 25 MW por falta de vento nao foi cortada em
175 MW. Ela inflaria o corte para 2,389 TWh, quase o dobro.

RAZAO DA RESTRICAO
------------------
  ENE  razao energetica — sobra frente a carga
  REL  indisponibilidade externa (eletrica)
  CNF  atendimento a requisitos de confiabilidade
  PAR  restricao indicada no parecer de acesso

Janeiro de 2025, participacao na energia cortada:
  ENE 66,1%   CNF 19,0%   REL 14,9%

ORIGEM
------
  SIS  sistemica    LOC  local

LIMITES DO DADO — CITAR SEMPRE QUE O NUMERO FOR USADO
-----------------------------------------------------
1. Cobre apenas usinas EOLICAS. Fotovoltaicas estao em
   dataset/restricao_coff_fotovoltaica_tm/.
2. Cobre apenas modalidades Tipo I, II-B e II-C. Usinas Tipo III,
   conectadas a rede das distribuidoras, ficam de fora.
3. Os dados fazem parte de processo de consistencia recorrente do
   ONS e podem ser revisados apos a publicacao.
4. Valores em MWmed. Em base semi-horaria, energia = MWmed * 0.5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    from . import ons_client as ons
except ImportError:
    import ons_client as ons

PREFIXO_EOLICA = "dataset/restricao_coff_eolica_tm/"
PREFIXO_SOLAR = "dataset/restricao_coff_fotovoltaica_tm/"
PREFIXO_CMO = "dataset/cmo_tm/"

PASSO_HORAS = 0.5

VAL_COLS = [
    "val_geracao", "val_geracaolimitada", "val_disponibilidade",
    "val_geracaoreferencia", "val_geracaoreferenciafinal",
]
COD_COLS = ["cod_razaorestricao", "cod_origemrestricao", "dsc_restricao"]

RAZOES = {
    "ENE": "razao energetica",
    "REL": "indisponibilidade externa (eletrica)",
    "CNF": "requisitos de confiabilidade",
    "PAR": "parecer de acesso",
}


@dataclass
class BlocoCorte:
    id_ons: str
    usina: str
    mwh: float
    subsistema: str
    razao: str
    origem: str


# ----------------------------------------------------------------------
# Carga e preparo
# ----------------------------------------------------------------------

def para_numero(s: pd.Series) -> pd.Series:
    """Colunas de valor chegam como texto, com campo vazio em vez de nulo."""
    t = s.astype("string").str.strip()
    t = t.mask(t.isin(["", "-", "nan", "None"]))
    if t.str.contains(r"\d\.\d{3},", na=False).any():
        t = t.str.replace(".", "", regex=False)
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")


def carregar_mes(ano: int, mes: int, fonte: str = "eolica") -> pd.DataFrame:
    prefixo = PREFIXO_EOLICA if fonte == "eolica" else PREFIXO_SOLAR
    objs = ons.listar(prefixo, contendo=f"_{ano}_{mes:02d}.parquet")
    if not objs:
        raise FileNotFoundError(f"parquet de {ano}-{mes:02d} nao encontrado em {prefixo}")
    df = pd.read_parquet(ons.baixar(objs[0].key))
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    for c in VAL_COLS:
        if c in df.columns:
            df[c] = para_numero(df[c])
    for c in COD_COLS:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    df.attrs["fonte"] = fonte
    df.attrs["periodo"] = f"{ano}-{mes:02d}"
    return df


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Isola as linhas com restricao declarada e calcula a energia
    cortada. Nao ha derivacao: val_geracaolimitada e o corte apurado.
    """
    if "val_geracaolimitada" not in df.columns:
        raise ValueError("dataset sem val_geracaolimitada — fonte errada?")

    out = df[df["cod_razaorestricao"].notna()].copy()
    out = out.dropna(subset=["val_geracaolimitada"])

    negativas = int((out["val_geracaolimitada"] < -1e-6).sum())
    if negativas:
        raise ValueError(
            f"{negativas} valores negativos em val_geracaolimitada — "
            "o dataset mudou de semantica, recalibrar antes de usar"
        )

    out["mwh_cortado"] = out["val_geracaolimitada"] * PASSO_HORAS
    out.attrs.update(df.attrs)
    out.attrs["linhas_totais"] = len(df)
    out.attrs["geracao_twh"] = float(df["val_geracao"].sum() * PASSO_HORAS / 1e6)
    return out


def diagnostico(df: pd.DataFrame) -> dict:
    corte_twh = float(df["mwh_cortado"].sum() / 1e6)
    ger_twh = df.attrs.get("geracao_twh", float("nan"))
    return {
        "fonte": df.attrs.get("fonte"),
        "periodo": df.attrs.get("periodo"),
        "linhas_com_restricao": len(df),
        "linhas_totais": df.attrs.get("linhas_totais"),
        "usinas": df["nom_usina"].nunique(),
        "corte_twh": round(corte_twh, 4),
        "geracao_twh": round(ger_twh, 4),
        "taxa_curtailment_pct": round(corte_twh / ger_twh * 100, 1) if ger_twh else None,
        "valores_negativos": int((df["val_geracaolimitada"] < 0).sum()),
    }


# ----------------------------------------------------------------------
# Quebras analiticas
# ----------------------------------------------------------------------

def por_razao(df: pd.DataFrame) -> pd.DataFrame:
    t = df.groupby("cod_razaorestricao").agg(
        mwh=("mwh_cortado", "sum"), ocorrencias=("mwh_cortado", "size")
    )
    t["pct_energia"] = (t["mwh"] / t["mwh"].sum() * 100).round(1)
    t["descricao"] = [RAZOES.get(i, "?") for i in t.index]
    return t.sort_values("mwh", ascending=False)


def por_origem(df: pd.DataFrame) -> pd.DataFrame:
    t = df.groupby("cod_origemrestricao").agg(
        mwh=("mwh_cortado", "sum"), ocorrencias=("mwh_cortado", "size")
    )
    t["pct_energia"] = (t["mwh"] / t["mwh"].sum() * 100).round(1)
    return t.sort_values("mwh", ascending=False)


def agregar_por_instante(df: pd.DataFrame,
                         razoes: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    Eventos por instante e subsistema. Filtrar por razao e o caminho
    natural: para a tese de excedente, so ENE interessa — REL e
    gargalo de rede, CNF e confiabilidade.
    """
    base = df if razoes is None else df[df["cod_razaorestricao"].isin(list(razoes))]
    return (
        base.groupby(["din_instante", "id_subsistema"], as_index=False)
        .agg(mwh_cortado=("mwh_cortado", "sum"),
             n_usinas=("nom_usina", "nunique"))
        .sort_values("mwh_cortado", ascending=False)
    )


# ----------------------------------------------------------------------
# Valoracao
# ----------------------------------------------------------------------

def carregar_cmo(ano: int) -> pd.DataFrame:
    objs = ons.listar(PREFIXO_CMO, contendo=f"_{ano}.parquet")
    if not objs:
        raise FileNotFoundError(f"CMO semi-horario de {ano} nao encontrado")
    cmo = pd.read_parquet(ons.baixar(objs[0].key))
    cmo["din_instante"] = pd.to_datetime(cmo["din_instante"])
    cmo["val_cmo"] = para_numero(cmo["val_cmo"])
    return cmo[["din_instante", "id_subsistema", "val_cmo"]]


def valorar(eventos: pd.DataFrame, cmo: pd.DataFrame,
            preco_carga_flexivel: float = 300.0) -> pd.DataFrame:
    """
    Duas reguas, deliberadamente.

    CMO — Custo Marginal de Operacao: quanto o proximo MWh vale para o
    sistema. Nos maiores eventos de curtailment ele e ZERO, porque o
    sistema esta sobrando. Isso nao e falha da medida: e a prova
    quantitativa de que o excedente nao tem valor marginal na rede.

    Carga flexivel: quanto o mesmo MWh vale para um consumidor local
    que hoje compra energia. E aqui que esta o valor recuperavel.

    O diferencial entre as duas e a tese do X-Layer: ausencia de rota,
    nao ausencia de demanda.
    """
    j = eventos.merge(cmo, on=["din_instante", "id_subsistema"], how="left")
    j = j.rename(columns={"val_cmo": "cmo_rs_mwh"})
    j["valor_pelo_cmo"] = j["mwh_cortado"] * j["cmo_rs_mwh"]
    j["valor_na_carga_flexivel"] = j["mwh_cortado"] * preco_carga_flexivel
    j["diferencial"] = j["valor_na_carga_flexivel"] - j["valor_pelo_cmo"].fillna(0)
    return j


# ----------------------------------------------------------------------
# Ponte para o otimizador
# ----------------------------------------------------------------------

def blocos_do_instante(df: pd.DataFrame, instante: pd.Timestamp,
                       top_n: int = 12) -> List[BlocoCorte]:
    """
    Converte um instante real em blocos para o HubstryXLayer.

    top_n limita o tamanho da instancia. Crescer gradualmente medindo
    tempo de solucao e taxa de viabilidade — em janeiro de 2025 houve
    instantes com mais de 800 usinas cortadas simultaneamente, entao a
    instancia completa e de outra ordem.
    """
    recorte = (
        df[(df["din_instante"] == instante) & (df["mwh_cortado"] > 0)]
        .nlargest(top_n, "mwh_cortado")
    )
    return [
        BlocoCorte(
            id_ons=str(r.id_ons),
            usina=str(r.nom_usina),
            mwh=float(r.mwh_cortado),
            subsistema=str(r.id_subsistema),
            razao=str(r.cod_razaorestricao),
            origem=str(r.cod_origemrestricao),
        )
        for r in recorte.itertuples()
    ]


def cobertura_dos_blocos(df: pd.DataFrame, instante: pd.Timestamp,
                         top_n: int) -> Tuple[float, float, float]:
    """Quanto do evento os top_n blocos representam. Honestidade de escala."""
    total = float(df[df["din_instante"] == instante]["mwh_cortado"].sum())
    parcial = sum(b.mwh for b in blocos_do_instante(df, instante, top_n))
    return parcial, total, (parcial / total * 100 if total else 0.0)


# ----------------------------------------------------------------------

if __name__ == "__main__":
    ANO, MES = 2025, 1

    print(f"Carregando restricao de operacao eolica {ANO}-{MES:02d}...")
    df = preparar(carregar_mes(ANO, MES))

    print("\n--- Diagnostico ---")
    for k, v in diagnostico(df).items():
        print(f"  {k:.<28} {v}")

    print("\n--- Corte por razao ---")
    print(por_razao(df).to_string())

    print("\n--- Corte por origem ---")
    print(por_origem(df).to_string())

    print("\n--- Eventos por razao energetica (ENE) ---")
    ene = agregar_por_instante(df, razoes=["ENE"])
    print(f"  instantes: {len(ene):,}")
    print(ene.head(8).to_string(index=False))

    print(f"\n--- Valoracao ---")
    try:
        cmo = carregar_cmo(ANO)
        val = valorar(ene, cmo)
        print(f"  CMO igual a zero em {(val['cmo_rs_mwh'] == 0).mean()*100:.1f}% "
              f"dos instantes com corte energetico")
        print(f"  Valor pelo CMO ................. R$ {val['valor_pelo_cmo'].sum():>16,.2f}")
        print(f"  Valor em carga flexivel ....... R$ {val['valor_na_carga_flexivel'].sum():>16,.2f}")
        print(f"  Diferencial recuperavel ....... R$ {val['diferencial'].sum():>16,.2f}")
        print()
        print(val.head(6).to_string(index=False))
    except Exception as exc:
        print(f"  falhou: {exc}")

    if len(ene):
        pior = ene.iloc[0]["din_instante"]
        for n in (12, 50, 200):
            p, t, pct = cobertura_dos_blocos(df, pior, n)
            print(f"\n  top {n:>3} blocos cobrem {p:9.1f} de {t:9.1f} MWh ({pct:4.1f}%)")
        print(f"\n--- Blocos do pior instante ({pior}) ---")
        for b in blocos_do_instante(df, pior, 12):
            print(f"  {b.id_ons:<10} {b.usina[:28]:<28} {b.mwh:8.3f} MWh  "
                  f"{b.subsistema:<3} {b.razao} {b.origem}")
