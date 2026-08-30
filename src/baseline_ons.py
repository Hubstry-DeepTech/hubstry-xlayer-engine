"""
Hubstry X-Layer Engine — Baselines normativos do ONS
====================================================
AVISO — RECLASSIFICACAO APOS LEITURA DA NORMA (29/08/2026)
----------------------------------------------------------
A leitura integral da NT-ONS DOP 0022/2025 mostrou que os dois
"baselines" antes tratados como criterios concorrentes pertencem a
FASES DIFERENTES do processo operativo:

  secao 5 — PROGRAMACAO DA OPERACAO (dia anterior, no PDO)
    5.1.2-IV: reduz-se a geracao das usinas/conjuntos eolicos e/ou
    solar fotovoltaicos "proporcional as suas disponibilidades".

  secao 6 — OPERACAO EM TEMPO REAL (execucao, via Gerdin)
    6.1 (razao energetica): rateio proporcional ao PONTO DE PARTIDA
    verificado no instante da restricao.

Os dados de constrained-off registram restricoes EXECUTADAS. Compara-
las contra o criterio de programacao e comparar objetos de naturezas
diferentes.

CONSEQUENCIA: o resultado de 60,15% de observacoes divergentes e a
divergencia acumulada de 115.407 MW NAO sao evidencia de conflito
entre criterios normativos. Sao artefato de comparar programacao com
execucao. Nao devem ser usados como resultado cientifico.

O rateio por disponibilidade permanece neste modulo como
`programacao_excedente` — referencia documental da fase de
programacao, nao baseline de execucao.

NOTA DE LITERALIDADE: o rateio "proporcional a disponibilidade
DECLARADA DE POTENCIA" aparece no item III, para hidreletricas com
vertimento. O item IV, das renovaveis variaveis, diz apenas
"proporcional as suas disponibilidades". Que ambos usem a mesma base
e inferencia nossa, nao literalidade do texto.

CRITERIOS DE EXECUCAO POR RAZAO (secao 6)
-----------------------------------------
  ENE  6.1     rateio proporcional ao ponto de partida
               -> REPRODUZIVEL: implementado aqui
  CNF  6.2.1/2 agrupamento por sensibilidade equivalente, esgotamento
               em ordem decrescente, rateio proporcional apenas no
               ultimo grupo
               -> NAO REPRODUZIVEL sem as tabelas de sensibilidade
  REL  6.2.1/2 mesmo criterio de CNF
               -> NAO REPRODUZIVEL sem as tabelas de sensibilidade

As tabelas de sensibilidade sao calculadas pelo SACI e cadastradas no
Gerdin. O historico e publicado no SINtegre. Enquanto nao forem
incorporadas, CNF e REL nao tem baseline de execucao neste modulo.
==================================================
Implementa a ordem de prioridade de reducao de geracao em excedente
energetico, conforme NT-ONS DOP 0022/2025, "Criterios para Gestao de
Excedentes Energeticos", 19 de agosto de 2025, secao 5.1.2.

POR QUE ESTE MODULO EXISTE
--------------------------
O motor QUBO precisa ser comparado contra a regra que vigora, nao
contra "nenhuma otimizacao". Sem este baseline, qualquer ganho
reportado e incomparavel — e a primeira pergunta de uma banca
tecnica seria exatamente essa.

A REGRA VIGENTE (NT-ONS DOP 0022/2025, secao 5.1.2)
---------------------------------------------------
Em caso de excedente energetico (geracao prevista maior que a carga
do SIN), a reducao segue esta ordem:

  I    hidroeletrica sem vertimento
  II   termoeletrica despachada fora da ordem de merito de custo,
       por ordem decrescente de custo
  III  hidroeletrica com vertimento, rateando proporcionalmente a
       disponibilidade declarada de potencia de cada usina
  IV   esgotados os recursos acima, reduz-se a geracao das
       usinas/conjuntos eolicos e fotovoltaicos, PROPORCIONAL AS
       SUAS DISPONIBILIDADES

O ponto que interessa ao X-Layer esta no item IV: renovavel variavel
e a ultima da fila, e o corte entre usinas e RATEIO PROPORCIONAL a
disponibilidade. Nao ha otimizacao nessa etapa — e proporcionalidade
pura.

O PROPRIO ONS DECLARA O CRITERIO COMO PROVISORIO
------------------------------------------------
A nota registra que o ordenamento segue a carta CTA-ONS DOP
1571-2021 e cita textualmente que ele "foi proposto em uma condicao
de ausencia de criterios e em uma situacao de pouca capacidade
instalada de geracao eolica/fotovoltaica, associada ao conceito de
inflexibilidade de tais fontes", com evolucao condicionada a
normativo relacionado a Consulta Publica 45/2019 da ANEEL.

Ou seja: a regra foi escrita para um sistema que nao existe mais, o
operador reconhece isso por escrito, e a substituicao depende de um
criterio que ainda nao foi formulado. E esse o espaco em que o
X-Layer opera.

TEMPO REAL x PROGRAMACAO
------------------------
Em tempo real (secao 6.1), o rateio por motivo energetico e
proporcional ao PONTO DE PARTIDA verificado no instante da restricao
— definido como o minimo entre a geracao verificada e o limite atual
do conjunto, quando ja ha restricao vigente; caso nao haja limite
atual, o ponto de partida e a geracao atual. Isso difere do rateio
por disponibilidade da programacao, e as duas variantes estao
implementadas.

Para motivo eletrico (secoes 6.2.1 e 6.2.2) a logica e outra:
ordenacao por sensibilidade equivalente ao fluxo controlado,
esgotando conjuntos em ordem decrescente. NAO implementado aqui —
as tabelas de sensibilidade nao sao publicas no mesmo grau, e o
escopo do X-Layer e excedente energetico (ENE).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

import pandas as pd


@dataclass
class Usina:
    """Conjunto ou usina sujeita a restricao."""
    id_ons: str
    nome: str
    disponibilidade_mw: float
    geracao_mw: float
    limite_atual_mw: Optional[float] = None   # None = sem restricao vigente

    @property
    def ponto_de_partida(self) -> float:
        """
        Secao 6.1: ponto de partida do rateio em tempo real.
        Minimo entre geracao verificada e limite atual, quando ha
        restricao vigente; caso contrario, a geracao atual.
        """
        if self.limite_atual_mw is None:
            return self.geracao_mw
        return min(self.geracao_mw, self.limite_atual_mw)


@dataclass
class ResultadoBaseline:
    criterio: str
    corte_por_usina: Dict[str, float]
    corte_total_mw: float
    residual_mw: float = 0.0
    observacoes: List[str] = field(default_factory=list)

    def como_frame(self, usinas: List[Usina]) -> pd.DataFrame:
        idx = {u.id_ons: u for u in usinas}
        linhas = []
        for uid, corte in self.corte_por_usina.items():
            u = idx[uid]
            linhas.append({
                "id_ons": uid,
                "nome": u.nome,
                "disponibilidade_mw": u.disponibilidade_mw,
                "geracao_mw": u.geracao_mw,
                "corte_mw": round(corte, 4),
                "geracao_pos_corte_mw": round(u.geracao_mw - corte, 4),
                "pct_cortado": round(corte / u.geracao_mw * 100, 2)
                if u.geracao_mw > 0 else 0.0,
            })
        return pd.DataFrame(linhas).sort_values("corte_mw", ascending=False)


# ----------------------------------------------------------------------

def rateio_proporcional(
    usinas: List[Usina],
    corte_necessario_mw: float,
    base: Literal["disponibilidade", "ponto_de_partida"] = "ponto_de_partida",
) -> ResultadoBaseline:
    """
    base="ponto_de_partida" -> secao 6.1, EXECUCAO em tempo real para
                               razao energetica. E este o baseline.
    base="disponibilidade"  -> secao 5.1.2-IV, PROGRAMACAO diaria.
                               Referencia documental; nao comparar com
                               dados de execucao.

    O rateio e iterativo: uma usina nao pode ser cortada alem da
    propria geracao. Quando o cabimento de alguma satura, o excedente
    e redistribuido entre as demais — comportamento necessario para o
    rateio fechar o montante solicitado.

    A secao 6.1 PREVE ajuste de parcela: o rateio e proporcional ao
    ponto de partida "exceto nos casos em que a parcela correspondente
    a determinado conjunto/usina possa provocar violacao de limites de
    transmissao ou de outros criterios operativos, situacao em que a
    parcela e ajustada".

    Ou seja: ajustar parcela e normativo. O QUE a norma NAO especifica
    e COMO ajustar. A redistribuicao proporcional implementada aqui e
    uma escolha nossa, compativel com o texto mas nao determinada por
    ele. Documentar como tal em qualquer resultado.
    """
    if corte_necessario_mw <= 0:
        return ResultadoBaseline("nenhum corte necessario", {}, 0.0)

    obs: List[str] = []
    cortes: Dict[str, float] = {u.id_ons: 0.0 for u in usinas}
    cabimento: Dict[str, float] = {u.id_ons: u.geracao_mw for u in usinas}
    pesos: Dict[str, float] = {
        u.id_ons: (u.disponibilidade_mw if base == "disponibilidade"
                   else u.ponto_de_partida)
        for u in usinas
    }

    restante = corte_necessario_mw
    ativos = {u.id_ons for u in usinas if cabimento[u.id_ons] > 1e-9
              and pesos[u.id_ons] > 1e-9}

    iteracoes = 0
    while restante > 1e-6 and ativos and iteracoes < len(usinas) + 5:
        iteracoes += 1
        soma_pesos = sum(pesos[i] for i in ativos)
        if soma_pesos <= 1e-9:
            break
        saturaram = set()
        for i in list(ativos):
            parcela = restante * pesos[i] / soma_pesos
            livre = cabimento[i] - cortes[i]
            if parcela >= livre - 1e-9:
                cortes[i] += livre
                saturaram.add(i)
            else:
                cortes[i] += parcela
        aplicado = sum(cortes.values())
        restante = corte_necessario_mw - aplicado
        ativos -= saturaram
        if saturaram:
            obs.append(f"iteracao {iteracoes}: {len(saturaram)} usina(s) "
                       f"saturaram o cabimento; excedente redistribuido")

    total = sum(cortes.values())
    if restante > 1e-6:
        obs.append(f"residual de {restante:.3f} MW nao alocavel: a soma da "
                   f"geracao das usinas nao cobre o corte solicitado")

    rotulo = ("NT-ONS DOP 0022/2025 5.1.2-IV — rateio proporcional a "
              "disponibilidade" if base == "disponibilidade"
              else "NT-ONS DOP 0022/2025 6.1 — rateio proporcional ao "
                   "ponto de partida")
    return ResultadoBaseline(rotulo, cortes, round(total, 4),
                             round(max(restante, 0.0), 4), obs)


def programacao_excedente(usinas: List[Usina],
                          corte_necessario_mw: float) -> ResultadoBaseline:
    """
    Secao 5.1.2-IV — criterio da PROGRAMACAO diaria, nao da execucao.

    Mantido como referencia documental. NAO usar como baseline contra
    dados de constrained-off, que registram execucao.
    """
    return rateio_proporcional(usinas, corte_necessario_mw,
                               base="disponibilidade")


def baseline_execucao_ene(usinas: List[Usina],
                          corte_necessario_mw: float) -> ResultadoBaseline:
    """
    Secao 6.1 — criterio de EXECUCAO em tempo real para razao
    energetica (ENE). E o unico baseline reproduzivel com os dados
    publicos disponiveis.
    """
    return rateio_proporcional(usinas, corte_necessario_mw,
                               base="ponto_de_partida")


def baseline_execucao_eletrica(razao: str) -> None:
    """
    Secoes 6.2.1 e 6.2.2 — CNF e REL.

    NAO IMPLEMENTADO. O criterio exige as tabelas de sensibilidade
    calculadas pelo SACI e cadastradas no Gerdin: agrupamento por
    sensibilidade equivalente (apos arredondamento ao inteiro),
    ordenacao decrescente, esgotamento em ordem, e rateio proporcional
    ao ponto de partida apenas no ultimo grupo.

    Sem essas tabelas, qualquer reproducao seria invencao. O historico
    e publicado no SINtegre.
    """
    raise NotImplementedError(
        f"criterio de execucao para {razao} exige tabelas de sensibilidade "
        "do SACI/Gerdin (NT-ONS DOP 0022/2025, secoes 6.2.1 e 6.2.2); "
        "historico publicado no SINtegre"
    )


def prioridade_por_razao(razoes_no_patamar: List[str]) -> str:
    """
    Secao 7.1 — titulacao quando ha mais de um motivo no mesmo patamar
    semi-horario.

    REL prevalece sobre as demais, independente da duracao. Entre CNF
    e ENE, prevalece a de maior duracao — como esta funcao recebe
    apenas os codigos, sem duracao, ela devolve o par em empate para
    resolucao pelo chamador.
    """
    r = set(razoes_no_patamar)
    if "REL" in r:
        return "REL"
    if {"CNF", "ENE"} <= r:
        return "CNF|ENE (desempatar pela maior duracao)"
    return next(iter(r)) if r else ""


# ----------------------------------------------------------------------

def comparar(
    usinas: List[Usina],
    corte_necessario_mw: float,
    corte_qubo: Dict[str, float],
    valor_por_usina_rs_mwh: Dict[str, float],
    passo_horas: float = 0.5,
) -> pd.DataFrame:
    """
    Compara o baseline normativo com a alocacao proposta pelo motor.

    valor_por_usina_rs_mwh: valor que a energia daquela usina teria
    numa carga flexivel co-localizada. E o parametro que precisa vir
    de tarifa observada, nao de premissa.

    ATENCAO: o baseline nao e uma alocacao "ruim" a ser batida. Ele
    otimiza outro objetivo — simplicidade e isonomia entre agentes.
    Qualquer ganho reportado deve declarar que foi medido contra um
    criterio proporcional, e que o criterio proporcional tem virtudes
    proprias (previsibilidade, ausencia de discricionariedade) que a
    otimizacao nao entrega automaticamente.
    """
    base = rateio_proporcional(usinas, corte_necessario_mw,
                               base="disponibilidade")
    idx = {u.id_ons: u for u in usinas}

    linhas = []
    for uid, u in idx.items():
        cb = base.corte_por_usina.get(uid, 0.0)
        cq = corte_qubo.get(uid, 0.0)
        preco = valor_por_usina_rs_mwh.get(uid, 0.0)
        linhas.append({
            "id_ons": uid,
            "nome": u.nome,
            "corte_baseline_mw": round(cb, 3),
            "corte_qubo_mw": round(cq, 3),
            "delta_mw": round(cq - cb, 3),
            "rs_mwh_local": preco,
            "perda_baseline_rs": round(cb * passo_horas * preco, 2),
            "perda_qubo_rs": round(cq * passo_horas * preco, 2),
        })

    df = pd.DataFrame(linhas)
    df["ganho_rs"] = df["perda_baseline_rs"] - df["perda_qubo_rs"]
    return df.sort_values("ganho_rs", ascending=False)


# ----------------------------------------------------------------------

if __name__ == "__main__":
    # Cenario ilustrativo: quatro conjuntos com disponibilidades
    # distintas e valores locais distintos. Os numeros sao de exemplo,
    # nao de apuracao.
    usinas = [
        Usina("CJU_A", "Conjunto A", disponibilidade_mw=500, geracao_mw=420),
        Usina("CJU_B", "Conjunto B", disponibilidade_mw=300, geracao_mw=280),
        Usina("CJU_C", "Conjunto C", disponibilidade_mw=200, geracao_mw=60),
        Usina("CJU_D", "Conjunto D", disponibilidade_mw=150, geracao_mw=140),
    ]
    corte = 600.0

    print("=== BASELINE NORMATIVO — rateio por disponibilidade ===")
    r1 = rateio_proporcional(usinas, corte, base="disponibilidade")
    print(f"criterio: {r1.criterio}")
    print(r1.como_frame(usinas).to_string(index=False))
    print(f"total cortado: {r1.corte_total_mw} MW   residual: {r1.residual_mw} MW")
    for o in r1.observacoes:
        print(f"  nota: {o}")

    print("\n=== VARIANTE TEMPO REAL — rateio por ponto de partida ===")
    r2 = rateio_proporcional(usinas, corte, base="ponto_de_partida")
    print(r2.como_frame(usinas).to_string(index=False))
    print(f"total cortado: {r2.corte_total_mw} MW   residual: {r2.residual_mw} MW")

    print("\n  Observe o Conjunto C: disponibilidade alta (200 MW) mas")
    print("  geracao baixa (60 MW). O rateio por disponibilidade lhe")
    print("  atribui uma parcela que ele nao tem como entregar, e o")
    print("  excedente e redistribuido. O rateio por ponto de partida")
    print("  nao produz esse efeito.")

    print("\n=== TITULACAO POR RAZAO (secao 7.1) ===")
    for caso in (["ENE"], ["CNF", "ENE"], ["REL", "ENE"], ["REL", "CNF", "ENE"]):
        print(f"  {str(caso):<26} -> {prioridade_por_razao(caso)}")
