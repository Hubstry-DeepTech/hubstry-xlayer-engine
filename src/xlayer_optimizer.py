"""
Hubstry X-Layer Engine — Optimizer
==================================
Reformulacao QUBO da alocacao de excedente energetico (curtailment)
para cargas flexiveis, sob restricoes de capacidade de linha.

Herda a formulacao-base do QUBO-VRP (Background IP da Hubstry):
as regras operacionais deixam de ser proibicoes e passam a ser
custos quadraticos dentro da propria funcao objetivo.

Solver: neal.SimulatedAnnealingSampler (classico).
Migra para DWaveSampler() sem alterar a formulacao.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import dimod

try:
    import neal
    _NEAL = True
except ImportError:  # pragma: no cover
    _NEAL = False


@dataclass
class BlocoExcedente:
    """Bloco de energia que seria cortado (curtailment)."""
    id: str
    mwh: float
    submercado: str


@dataclass
class CargaFlexivel:
    """No capaz de absorver excedente: data center, BESS, carga industrial."""
    id: str
    capacidade_mwh: float
    valor_por_mwh: float          # R$/MWh que este no paga ou economiza
    linha: str                    # linha de transmissao que o atende


@dataclass
class ResultadoAlocacao:
    alocacao: Dict[str, str]
    mwh_alocado: float
    valor_recuperado: float
    energia_qubo: float
    tempo_solucao_s: float
    viavel: bool
    violacoes: List[str] = field(default_factory=list)


class HubstryXLayer:
    """
    Variavel binaria x[i][j] = 1 se o bloco de excedente i for
    despachado para a carga flexivel j.

    Termos do Hamiltoniano:
      1. Objetivo   -- maximizar valor absorvido (entra negativo)
      2. Igualdade  -- cada bloco vai para no maximo um destino
      3. Desigualdade -- soma despachada por linha <= limite fisico
    """

    def __init__(self, penalty_weight: float = 1000.0, seed: int = 42):
        self.penalty_weight = penalty_weight
        self.seed = seed
        self.bqm = dimod.BinaryQuadraticModel(vartype="BINARY")
        self._x: Dict[Tuple[str, str], str] = {}
        self._blocos: Dict[str, BlocoExcedente] = {}
        self._cargas: Dict[str, CargaFlexivel] = {}

    # ------------------------------------------------------------------

    def build(
        self,
        blocos: List[BlocoExcedente],
        cargas: List[CargaFlexivel],
        limites_rede: Dict[str, float],
    ) -> dimod.BinaryQuadraticModel:
        self._blocos = {b.id: b for b in blocos}
        self._cargas = {c.id: c for c in cargas}

        for b in blocos:
            for c in cargas:
                self._x[(b.id, c.id)] = f"x_{b.id}_{c.id}"

        # 1. OBJETIVO — valor recuperado entra com sinal negativo,
        #    porque o sampler minimiza energia.
        for b in blocos:
            for c in cargas:
                mwh_util = min(b.mwh, c.capacidade_mwh)
                valor = mwh_util * c.valor_por_mwh
                self.bqm.add_linear(self._x[(b.id, c.id)], -valor)

        # 2. Cada bloco em no maximo um destino.
        #    Formulado como igualdade a 1 (soma - 1)^2; blocos sem destino
        #    viavel pagam a penalidade, o que e o comportamento desejado:
        #    o modelo prefere alocar.
        for b in blocos:
            termos = [(self._x[(b.id, c.id)], 1) for c in cargas]
            self.bqm.add_linear_equality_constraint(
                termos,
                lagrange_multiplier=self.penalty_weight,
                constant=-1,
            )

        # 3. Limite fisico por linha de transmissao.
        #    Coeficiente = MWh do bloco; soma <= limite da linha.
        #    Inteiros sao exigidos pela API, entao trabalhamos em MWh
        #    arredondados.
        for linha, limite in limites_rede.items():
            termos = [
                (self._x[(b.id, c.id)], int(round(b.mwh)))
                for b in blocos
                for c in cargas
                if c.linha == linha
            ]
            if not termos:
                continue
            self.bqm.add_linear_inequality_constraint(
                termos,
                lagrange_multiplier=self.penalty_weight,
                label=f"linha_{linha}",
                ub=int(round(limite)),
            )

        # 4. Capacidade de absorcao de cada carga flexivel.
        #    Sem este termo o solver encontra solucoes mais valiosas que
        #    violam a capacidade fisica do no — falha real observada em
        #    execucao. Restricao nao modelada vira ganho ilusorio.
        for c in cargas:
            termos = [
                (self._x[(b.id, c.id)], int(round(b.mwh)))
                for b in blocos
            ]
            self.bqm.add_linear_inequality_constraint(
                termos,
                lagrange_multiplier=self.penalty_weight,
                label=f"cap_{c.id}",
                ub=int(round(c.capacidade_mwh)),
            )

        return self.bqm

    # ------------------------------------------------------------------

    def solve(self, num_reads: int = 200, limites_rede: Optional[Dict[str, float]] = None) -> ResultadoAlocacao:
        if not _NEAL:
            raise RuntimeError("neal nao instalado: pip install dwave-neal")

        t0 = time.perf_counter()
        sampler = neal.SimulatedAnnealingSampler()
        resposta = sampler.sample(self.bqm, num_reads=num_reads, seed=self.seed)
        elapsed = time.perf_counter() - t0

        melhor = resposta.first.sample
        energia = resposta.first.energy

        alocacao: Dict[str, str] = {}
        for (bid, cid), var in self._x.items():
            if melhor.get(var, 0) == 1:
                alocacao[bid] = cid

        mwh = 0.0
        valor = 0.0
        for bid, cid in alocacao.items():
            b, c = self._blocos[bid], self._cargas[cid]
            util = min(b.mwh, c.capacidade_mwh)
            mwh += util
            valor += util * c.valor_por_mwh

        violacoes = self._auditar(alocacao, limites_rede or {})

        return ResultadoAlocacao(
            alocacao=alocacao,
            mwh_alocado=round(mwh, 3),
            valor_recuperado=round(valor, 2),
            energia_qubo=round(float(energia), 3),
            tempo_solucao_s=round(elapsed, 4),
            viavel=len(violacoes) == 0,
            violacoes=violacoes,
        )

    # ------------------------------------------------------------------

    def _auditar(self, alocacao: Dict[str, str], limites: Dict[str, float]) -> List[str]:
        """
        Verificacao independente do solver. E esta funcao que produz a
        taxa de viabilidade — a metrica que decide o projeto na Fase 1.
        Nunca confiar apenas na energia do QUBO.
        """
        violacoes: List[str] = []

        # Um bloco nao pode ir a dois destinos (garantido pelo dict, mas
        # deixamos explicito para quando a estrutura mudar).
        for bid in alocacao:
            if bid not in self._blocos:
                violacoes.append(f"bloco desconhecido: {bid}")

        # Carga de cada linha
        por_linha: Dict[str, float] = {}
        for bid, cid in alocacao.items():
            linha = self._cargas[cid].linha
            por_linha[linha] = por_linha.get(linha, 0.0) + self._blocos[bid].mwh
        for linha, carga in por_linha.items():
            limite = limites.get(linha)
            if limite is not None and carga > limite + 1e-6:
                violacoes.append(
                    f"linha {linha}: {carga:.1f} MWh acima do limite de {limite:.1f}"
                )

        # Capacidade de cada carga flexivel
        por_carga: Dict[str, float] = {}
        for bid, cid in alocacao.items():
            por_carga[cid] = por_carga.get(cid, 0.0) + self._blocos[bid].mwh
        for cid, total in por_carga.items():
            cap = self._cargas[cid].capacidade_mwh
            if total > cap + 1e-6:
                violacoes.append(
                    f"carga {cid}: {total:.1f} MWh acima da capacidade de {cap:.1f}"
                )

        return violacoes


# ----------------------------------------------------------------------

def baseline_curtailment(blocos: List[BlocoExcedente]) -> Tuple[float, float]:
    """Cenario real: tudo cortado. Zero MWh aproveitado, zero valor."""
    return 0.0, 0.0


if __name__ == "__main__":
    blocos = [
        BlocoExcedente("B1", 120.0, "NE"),
        BlocoExcedente("B2", 80.0, "NE"),
        BlocoExcedente("B3", 150.0, "NE"),
        BlocoExcedente("B4", 60.0, "NE"),
    ]
    cargas = [
        CargaFlexivel("datacenter_A", 200.0, 310.0, "L1"),
        CargaFlexivel("bess_B", 150.0, 180.0, "L1"),
        CargaFlexivel("industria_C", 100.0, 240.0, "L2"),
    ]
    limites = {"L1": 220.0, "L2": 100.0}

    eng = HubstryXLayer(penalty_weight=5000.0)
    eng.build(blocos, cargas, limites)
    res = eng.solve(num_reads=300, limites_rede=limites)

    mwh_base, valor_base = baseline_curtailment(blocos)
    total = sum(b.mwh for b in blocos)

    print(f"Blocos de excedente ........ {total:.1f} MWh")
    print(f"Baseline (curtailment) ..... {mwh_base:.1f} MWh | R$ {valor_base:,.2f}")
    print(f"X-Layer .................... {res.mwh_alocado:.1f} MWh | R$ {res.valor_recuperado:,.2f}")
    print(f"Aproveitamento ............. {100*res.mwh_alocado/total:.1f}%")
    print(f"Tempo de solucao ........... {res.tempo_solucao_s:.3f}s")
    print(f"Variaveis binarias ......... {len(eng.bqm.variables)}")
    print(f"Viavel ..................... {res.viavel}")
    if res.violacoes:
        for v in res.violacoes:
            print(f"  VIOLACAO: {v}")
    print(f"Alocacao ................... {res.alocacao}")
