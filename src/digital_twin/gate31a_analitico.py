"""
Gate 3.1A — Alocacao de excedente com sinks continuos (versao analitica)
=======================================================================
POR QUE ESTA VERSAO NAO USA O OTIMIZADOR
----------------------------------------
No recorte do Gate 3.1A — um sink continuo, co-localizado, por parque,
sem estado interno — NAO EXISTE PROBLEMA COMBINATORIO.

A energia cortada no Conjunto Sao Roque so pode ir para o sink do
Sao Roque. Nao ha escolha a fazer. A alocacao otima e, exatamente:

    absorvido_i = min(corte_i, capacidade_i)

Modelar isso como QUBO gera centenas de milhares de variaveis
binarias para reproduzir, aproximadamente, o que uma linha de pandas
resolve exatamente. A versao anterior deste gate criava mais de
700.000 variaveis para 141 conjuntos — inviavel em maquina comum e
sem qualquer ganho de qualidade.

O Allocation Engine (QUBO) ganha seu lugar quando ha disputa real
pela mesma energia:

  - sinks compartilhados entre parques (exige topologia de rede)
  - acoplamento temporal com armazenamento (Gate 3.1B)
  - limite de linha comum a varios parques (Gate 3.1C)

Nenhuma dessas condicoes esta presente aqui.

CUSTO COMPUTACIONAL
-------------------
Segundos. Roda com os 141 conjuntos, sem restricao de memoria.

STATUS POR CAMADA — LER ANTES DE CITAR QUALQUER NUMERO
------------------------------------------------------
  Estado temporal .............. VALIDADO (gate31_persistencia)
  Selecao dos episodios ........ VALIDADA
  Alocacao ..................... EXATA (nao heuristica)
  Magnitude do excedente ....... PROVISORIA
  Ganho de alocacao ............ CONDICIONAL AS PREMISSAS
  Interpretacao normativa ...... PENDENTE

A magnitude deriva de (val_geracaolimitada - val_geracao), formula que
produz 29,7% de valores negativos em janeiro de 2025. A causa provavel
esta na secao 7.1 da NT-ONS DOP 0022/2025: pode haver mais de um
comando de restricao, com duracoes distintas, dentro do mesmo patamar
de 30 minutos, enquanto a geracao publicada e a media do patamar.
Sao grandezas de janelas diferentes.

Quando isso for resolvido, ESTE MESMO GATE deve ser reexecutado e a
diferenca medida. A correcao vira teste de sensibilidade.

AS DUAS PERGUNTAS SAO SEPARADAS
-------------------------------
1. DISTRIBUICAO DO CORTE — quem perde quanto. Baseline A e B sao
   diretamente comparaveis entre si e com o observado.

2. APROVEITAMENTO DO EXCEDENTE — quanto deixa de ser perdido. O
   baseline NAO e concorrente: e o cenario de referencia sem sink,
   no qual a energia se perde integralmente.

PREMISSAS CONGELADAS (v0) — NENHUMA E DADO DO ONS
-------------------------------------------------
  Capacidade ....... 50 / 150 / 300 MW por parque
  Cobertura ........ 10 (conservador) / 30 (intermediario) /
                     todos (limite superior contrafactual)
  Janela ........... 06:00-18:00
  Eficiencia ....... 95%
  Valor local ...... R$ 300/MWh  (premissa; trocar por tarifa observada)
  Localizacao ...... co-localizado, um sink por parque
  Fluxo de potencia. nao modelado
  BESS ............. nao (Gate 3.1B)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from . import gate31_persistencia as g31
except ImportError:
    import gate31_persistencia as g31

from baseline_ons import Usina, rateio_proporcional

PASSO_HORAS = 0.5

CAPACIDADES_MW = [50.0, 150.0, 300.0]
COBERTURAS: List[Tuple[Optional[int], str]] = [
    (10, "conservador"),
    (30, "intermediario"),
    (None, "limite superior contrafactual"),
]
JANELA = (6, 18)
EFICIENCIA = 0.95
VALOR_LOCAL_RS_MWH = 300.0


@dataclass
class Premissas:
    capacidade_mw: float
    n_parques: Optional[int]
    rotulo: str
    janela: Tuple[int, int] = JANELA
    eficiencia: float = EFICIENCIA
    valor_rs_mwh: float = VALOR_LOCAL_RS_MWH

    def capacidade_no_patamar(self, instante: pd.Timestamp) -> float:
        """MWh absorviveis no patamar, dado o perfil de disponibilidade."""
        ini, fim = self.janela
        if not (ini <= instante.hour < fim):
            return 0.0
        return self.capacidade_mw * PASSO_HORAS * self.eficiencia

    def descrever(self) -> str:
        n = "todos" if self.n_parques is None else str(self.n_parques)
        return (f"{self.capacidade_mw:.0f} MW/parque · {n} parques "
                f"({self.rotulo}) · janela {self.janela[0]:02d}h-"
                f"{self.janela[1]:02d}h · eficiencia {self.eficiencia:.0%} · "
                f"R$ {self.valor_rs_mwh:.0f}/MWh")


# ----------------------------------------------------------------------

def escolher_instante(df: pd.DataFrame) -> pd.Timestamp:
    ene = df[(df["cod_razaorestricao"] == "ENE") & (df["corte_mw"] > 0)]
    ene = ene[ene["din_instante"].dt.hour.between(JANELA[0], JANELA[1] - 1)]
    return ene.groupby("din_instante")["corte_mwh"].sum().idxmax()


def usinas_do_instante(df: pd.DataFrame, instante: pd.Timestamp) -> pd.DataFrame:
    return (df[(df["din_instante"] == instante) & (df["corte_mw"] > 0)]
            .sort_values("corte_mwh", ascending=False)
            .reset_index(drop=True))


# ----- Pergunta 1 -----------------------------------------------------

def distribuicao_do_corte(recorte: pd.DataFrame) -> pd.DataFrame:
    usinas = [
        Usina(id_ons=str(r.id_ons), nome=str(r.nom_usina),
              disponibilidade_mw=float(r.val_disponibilidade),
              geracao_mw=float(r.val_geracao),
              limite_atual_mw=float(r.val_geracaolimitada))
        for r in recorte.itertuples()
    ]
    total = float(recorte["corte_mw"].sum())
    a = rateio_proporcional(usinas, total, base="ponto_de_partida")
    b = rateio_proporcional(usinas, total, base="disponibilidade")

    linhas = []
    for u in usinas:
        obs = float(recorte.loc[recorte["id_ons"] == u.id_ons, "corte_mw"].iloc[0])
        linhas.append({
            "id_ons": u.id_ons, "nome": u.nome[:28],
            "observado_mw": round(obs, 2),
            "baseline_A_mw": round(a.corte_por_usina.get(u.id_ons, 0.0), 2),
            "baseline_B_mw": round(b.corte_por_usina.get(u.id_ons, 0.0), 2),
        })
    out = pd.DataFrame(linhas)
    out["A_menos_B"] = (out["baseline_A_mw"] - out["baseline_B_mw"]).round(2)
    return out.sort_values("observado_mw", ascending=False)


# ----- Pergunta 2 (exata) ---------------------------------------------

def alocar(recorte: pd.DataFrame, instante: pd.Timestamp,
           p: Premissas) -> dict:
    """
    Alocacao exata. Um sink por parque, sem compartilhamento:
    absorvido_i = min(corte_i, capacidade_i)
    """
    sel = recorte if p.n_parques is None else recorte.head(p.n_parques)
    cap = p.capacidade_no_patamar(instante)

    corte = sel["corte_mwh"].astype(float)
    absorvido = corte.clip(upper=cap)
    excedente_sel = float(corte.sum())
    excedente_evento = float(recorte["corte_mwh"].sum())
    abs_total = float(absorvido.sum())

    return {
        "cap_MW": int(p.capacidade_mw),
        "parques": "todos" if p.n_parques is None else p.n_parques,
        "cobertura": p.rotulo,
        "excedente_evento_MWh": round(excedente_evento, 1),
        "excedente_coberto_MWh": round(excedente_sel, 1),
        "absorvido_MWh": round(abs_total, 1),
        "pct_do_evento": round(abs_total / excedente_evento * 100, 1)
        if excedente_evento else 0.0,
        "pct_do_coberto": round(abs_total / excedente_sel * 100, 1)
        if excedente_sel else 0.0,
        "residual_MWh": round(excedente_evento - abs_total, 1),
        # NAO e valor economico realizavel: e o produto da energia por
        # uma PREMISSA de preco. Devolve a premissa multiplicada.
        "valor_premissa_RS": round(abs_total * p.valor_rs_mwh, 2),
        # Parques cujo corte ATINGE OU SUPERA a capacidade do sink —
        # sinks CHEIOS, com energia sobrando do lado de fora. Por isso a
        # contagem CAI quando a capacidade sobe.
        "sinks_saturados": int((corte >= cap - 1e-9).sum()) if cap > 0 else 0,
    }


def diagnosticar_divergencia(dist: pd.DataFrame, recorte: pd.DataFrame,
                            n: int = 10) -> pd.DataFrame:
    """
    Conjuntos onde os dois baselines normativos discordam.

    A hipotese a TESTAR — nao a assumir — e que a divergencia se
    concentra em parques com disponibilidade alta e geracao baixa: o
    rateio por disponibilidade (baseline B) atribuiria corte que o
    parque nao tem como entregar, enquanto o rateio por ponto de
    partida (baseline A) nao produz esse efeito.

    A coluna razao_disp_ger permite verificar. Se os divergentes
    tiverem razao sistematicamente maior que os demais, a hipotese se
    sustenta; se nao, cai.
    """
    d = dist.copy()
    d["divergencia"] = (d["baseline_A_mw"] - d["baseline_B_mw"]).abs()
    total_div = d["divergencia"].sum()

    ctx = recorte[["id_ons", "val_geracao", "val_disponibilidade",
                   "val_geracaolimitada", "cod_razaorestricao",
                   "cod_origemrestricao"]].copy()
    d = d.merge(ctx, on="id_ons", how="left")
    d["razao_disp_ger"] = (d["val_disponibilidade"] /
                           d["val_geracao"].replace(0, pd.NA)).round(2)
    d["pct_da_divergencia_total"] = (d["divergencia"] / total_div * 100).round(1) \
        if total_div else 0.0

    div = d[d["divergencia"] > 0.01].sort_values("divergencia", ascending=False)
    return div.head(n)


def escrever_relatorio(caminho: Path, instante: pd.Timestamp,
                       recorte: pd.DataFrame, dist: pd.DataFrame,
                       grade: pd.DataFrame) -> None:
    exced = float(recorte["corte_mwh"].sum())
    div = (dist["baseline_A_mw"] - dist["baseline_B_mw"]).abs()
    txt = f"""# Gate 3.1A — Alocacao de excedente com sinks continuos

**Evento:** {instante}
**Conjuntos cortados:** {len(recorte)}
**Excedente no patamar:** {exced:,.1f} MWh

> A magnitude do excedente e **provisoria**, sujeita a resolucao da
> divergencia entre `val_geracaolimitada` e `val_geracao` (29,7% de
> valores negativos em janeiro de 2025). Os resultados de alocacao sao
> condicionais a magnitude reconstruida e **nao constituem estimativa
> definitiva de energia recuperavel**.

## Pergunta 1 — Distribuicao do corte

Baseline A: rateio por ponto de partida (NT-ONS DOP 0022/2025, secao 6.1).
Baseline B: rateio por disponibilidade (NT-ONS DOP 0022/2025, secao 5.1.2-IV).

Divergencia media entre as duas regras: **{div.mean():.2f} MW**
(maxima: {div.max():.2f} MW).

{dist.head(20).to_markdown(index=False)}

## Pergunta 2 — Aproveitamento do excedente

O baseline nao e concorrente aqui: representa o cenario de referencia
sem sink flexivel, no qual a energia se perde integralmente.

Alocacao **exata**, nao heuristica: com um sink co-localizado por parque
e sem estado interno, a solucao otima e `min(corte, capacidade)`.

{grade.to_markdown(index=False)}

## Premissas declaradas

Nenhum destes valores e dado do ONS. Sao premissas de cenario.

| Parametro | Valor |
|---|---|
| Capacidade | 50 / 150 / 300 MW por parque |
| Cobertura | 10 / 30 / todos os conjuntos |
| Janela de disponibilidade | {JANELA[0]:02d}h-{JANELA[1]:02d}h |
| Eficiencia | {EFICIENCIA:.0%} |
| Valor local | R$ {VALOR_LOCAL_RS_MWH:.0f}/MWh |
| Localizacao | co-localizado, um sink por parque |
| Fluxo de potencia | nao modelado |
| Armazenamento | ausente (Gate 3.1B) |

A cobertura "limite superior contrafactual" **nao e realista**: responde
"e se todo conjunto tivesse sink co-localizado?".

## Achado estrutural: fragmentacao espacial

Com capacidade de 300 MW por parque em todos os conjuntos, a capacidade
nominal agregada supera o excedente em varias vezes — e ainda assim
permanece energia residual, com sinks saturados.

A razao e que **o sink nao pode receber energia de outro parque**. Sobra
capacidade em parques que cortaram pouco e falta em parques que cortaram
muito, e a co-localizacao impede a transferencia.

O gargalo, portanto, nao e capacidade agregada — e distribuicao. Este e
o resultado que justifica o Gate 3.1C: quando sinks puderem ser
compartilhados entre parques, o problema deixa de ser
`min(corte, capacidade)` e passa legitimamente a ser otimizacao
combinatoria. E nesse ponto, nao antes, que o motor QUBO ganha
protagonismo.

## Nota sobre as colunas

- **`sinks_saturados`**: parques cujo corte atinge ou supera a capacidade
  do sink — sinks cheios, com energia sobrando do lado de fora. A
  contagem CAI quando a capacidade sobe.
- **`valor_premissa_RS`**: produto da energia absorvida por uma premissa
  de R$ 300/MWh. **Nao representa valor economico realizavel** — devolve
  a premissa multiplicada. Substituir por tarifa observada antes de
  qualquer uso externo.

## Limitacoes

1. Magnitude do corte provisoria.
2. Cobre apenas eolica, modalidades Tipo I, II-B e II-C. Fotovoltaica e
   Tipo III ficam de fora.
3. Um unico patamar de 30 minutos. Episodios reais duram de 9 a 11,5
   horas — a extensao para o episodio completo exige acoplamento
   temporal.
4. Dados de janeiro de 2025 foram apurados pela metodologia anterior a
   revisao 08 da RO-AO.BR.13, vigente desde 01/08/2025.
"""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(txt, encoding="utf-8")


# ----------------------------------------------------------------------

if __name__ == "__main__":
    ANO, MES = 2025, 1

    print(f"Carregando evento real {ANO}-{MES:02d}...")
    df = g31.calcular_corte(g31.carregar(ANO, MES))
    instante = escolher_instante(df)
    recorte = usinas_do_instante(df, instante)
    exced = float(recorte["corte_mwh"].sum())

    print(f"Instante ....... {instante}")
    print(f"Conjuntos ...... {len(recorte)}")
    print(f"Excedente ...... {exced:,.1f} MWh (PROVISORIO)")

    print("\n" + "=" * 72)
    print("PERGUNTA 1 — DISTRIBUICAO DO CORTE")
    print("=" * 72)
    dist = distribuicao_do_corte(recorte)
    print(dist.head(15).to_string(index=False))
    div = (dist["baseline_A_mw"] - dist["baseline_B_mw"]).abs()
    print(f"\n  divergencia |A-B|: media {div.mean():.2f} MW  "
          f"maxima {div.max():.2f} MW  "
          f"usinas com divergencia: {int((div > 0.01).sum())}/{len(div)}")

    print("\n--- Conjuntos onde os baselines discordam ---")
    diag = diagnosticar_divergencia(dist, recorte)
    cols = ["id_ons", "nome", "observado_mw", "baseline_A_mw", "baseline_B_mw",
            "divergencia", "pct_da_divergencia_total", "val_geracao",
            "val_disponibilidade", "razao_disp_ger", "cod_razaorestricao"]
    print(diag[cols].to_string(index=False))
    print(f"\n  concentracao: os {len(diag)} maiores respondem por "
          f"{diag['pct_da_divergencia_total'].sum():.1f}% da divergencia total")

    # Teste da hipotese, sem assumi-la
    ctx = recorte.copy()
    ctx["razao_disp_ger"] = ctx["val_disponibilidade"] / ctx["val_geracao"].replace(0, pd.NA)
    ids_div = set(diag["id_ons"])
    r_div = ctx[ctx["id_ons"].isin(ids_div)]["razao_disp_ger"].median()
    r_out = ctx[~ctx["id_ons"].isin(ids_div)]["razao_disp_ger"].median()
    print(f"\n  HIPOTESE: divergencia se concentra em disponibilidade alta")
    print(f"            e geracao baixa (razao disp/ger elevada).")
    print(f"    mediana disp/ger nos divergentes .: {r_div:.2f}")
    print(f"    mediana disp/ger nos demais ......: {r_out:.2f}")
    if pd.notna(r_div) and pd.notna(r_out):
        print(f"    -> hipotese {'SUSTENTADA' if r_div > r_out * 1.3 else 'NAO sustentada'}"
              f" por este teste")

    print("\n" + "=" * 72)
    print("PERGUNTA 2 — APROVEITAMENTO DO EXCEDENTE (alocacao exata)")
    print("=" * 72)
    linhas = []
    for cap in CAPACIDADES_MW:
        for n, rot in COBERTURAS:
            linhas.append(alocar(recorte, instante,
                                 Premissas(cap, n, rot)))
    grade = pd.DataFrame(linhas)
    print(grade.to_string(index=False))

    saida = Path(__file__).resolve().parents[2] / "docs" / "GATE_3_1A.md"
    escrever_relatorio(saida, instante, recorte, dist, grade)
    print(f"\nRelatorio escrito em: {saida}")
