# Gate 3.1A — Alocacao de excedente com sinks continuos

**Evento:** 2025-01-13 15:00:00
**Conjuntos cortados:** 142
**Excedente no patamar:** 8,560.5 MWh

> A magnitude do excedente e **provisoria**, sujeita a resolucao da
> divergencia entre `val_geracaolimitada` e `val_geracao` (29,7% de
> valores negativos em janeiro de 2025). Os resultados de alocacao sao
> condicionais a magnitude reconstruida e **nao constituem estimativa
> definitiva de energia recuperavel**.

## Pergunta 1 — Distribuicao do corte

Baseline A: rateio por ponto de partida (NT-ONS DOP 0022/2025, secao 6.1).
Baseline B: rateio por disponibilidade (NT-ONS DOP 0022/2025, secao 5.1.2-IV).

Divergencia media entre as duas regras: **2.05 MW**
(maxima: 175.86 MW).

| id_ons      | nome                         |   observado_mw |   baseline_A_mw |   baseline_B_mw |   A_menos_B |
|:------------|:-----------------------------|---------------:|----------------:|----------------:|------------:|
| CJU_PI4ECNP | CONJ. CURRAL NOVO DO PIAUÍ I |         580.21 |          128.89 |          128.89 |           0 |
| CJU_PIVSR   | CONJ. SÃO ROQUE              |         532.35 |            4.49 |            4.49 |           0 |
| CJU_BASAR   | CONJ. SERRA DO ASSURUÁ       |         515.42 |           60.72 |           60.72 |           0 |
| CJU_PILDV   | CONJ. LAGOA DOS VENTOS       |         479.52 |           11.22 |           11.22 |           0 |
| CJU_PIOIT   | CONJ. OITIS                  |         397.2  |            4.03 |            4.03 |           0 |
| CJU_RNCAJ1  | CONJ. CAJU                   |         368.14 |          159.16 |          159.16 |           0 |
| CJU_BAVSE   | CONJ. EOL. VENTOS SANTA EUGÊ |         359.71 |           45.26 |           45.26 |           0 |
| CJU_BALRA   | CONJ. LARANJEIRAS            |         334.6  |           25.14 |           25.14 |           0 |
| CJU_PIARP   | CONJ. CURRAL NOVO DO PIAUI I |         316.82 |           37.41 |           37.41 |           0 |
| CJU_RNRVE   | CONJ. RIO DO VENTO EXPANSÃO  |         304.22 |           97.11 |           97.11 |           0 |
| CJU_PBCSDS  | CONJ. SERRA DO SERIDÓ        |         301.79 |           63.11 |           63.11 |           0 |
| CJU_BASVT   | CONJ. VENTOS DE SÃO VITOR    |         301.76 |           27.57 |           27.57 |           0 |
| CJU_BAOUR   | CONJ. OUROLÂNDIA II          |         266.29 |          109.31 |          109.31 |           0 |
| CJU_RNRDV   | CONJ. RIO DO VENTO           |         255.64 |          107.13 |          107.13 |           0 |
| CJU_BACLA2  | CONJ. CAMPO LARGO 2          |         232.16 |           32.8  |           32.8  |           0 |
| CJU_BAEMS2  | CONJ. MORRO DO CHAPÉU SUL II |         232.12 |           48.88 |           48.88 |           0 |
| CJU_BATUC   | CONJ. TUCANO                 |         229.06 |            9.2  |            9.2  |           0 |
| CJU_BAUBN   | CONJ. UMBURANAS              |         226.96 |           50.84 |           50.84 |           0 |
| CJU_BASDB   | CONJ. SERRA DA BABILÔNIA     |         224.69 |           53.37 |           53.37 |           0 |
| CJU_RNSAG   | CONJ. SANTO AGOSTINHO        |         223.91 |           99.83 |           99.83 |           0 |

## Pergunta 2 — Aproveitamento do excedente

O baseline nao e concorrente aqui: representa o cenario de referencia
sem sink flexivel, no qual a energia se perde integralmente.

Alocacao **exata**, nao heuristica: com um sink co-localizado por parque
e sem estado interno, a solucao otima e `min(corte, capacidade)`.

|   cap_MW | parques   | cobertura                     |   excedente_evento_MWh |   excedente_coberto_MWh |   absorvido_MWh |   pct_do_evento |   pct_do_coberto |   residual_MWh |   valor_premissa_RS |   sinks_saturados |
|---------:|:----------|:------------------------------|-----------------------:|------------------------:|----------------:|----------------:|-----------------:|---------------:|--------------------:|------------------:|
|       50 | 10        | conservador                   |                 8560.5 |                  2094.1 |           237.5 |             2.8 |             11.3 |         8323   |     71250           |                10 |
|       50 | 30        | intermediario                 |                 8560.5 |                  4324   |           712.5 |             8.3 |             16.5 |         7848   |    213750           |                30 |
|       50 | todos     | limite superior contrafactual |                 8560.5 |                  8560.5 |          3019   |            35.3 |             35.3 |         5541.6 |    905690           |               106 |
|      150 | 10        | conservador                   |                 8560.5 |                  2094.1 |           712.5 |             8.3 |             34   |         7848   |    213750           |                10 |
|      150 | 30        | intermediario                 |                 8560.5 |                  4324   |          2137.5 |            25   |             49.4 |         6423   |    641250           |                30 |
|      150 | todos     | limite superior contrafactual |                 8560.5 |                  8560.5 |          6268.1 |            73.2 |             73.2 |         2292.5 |         1.88042e+06 |                43 |
|      300 | 10        | conservador                   |                 8560.5 |                  2094.1 |          1425   |            16.6 |             68   |         7135.5 |    427500           |                10 |
|      300 | 30        | intermediario                 |                 8560.5 |                  4324   |          3638.1 |            42.5 |             84.1 |         4922.4 |         1.09143e+06 |                12 |
|      300 | todos     | limite superior contrafactual |                 8560.5 |                  8560.5 |          7874.7 |            92   |             92   |          685.9 |         2.3624e+06  |                12 |

## Premissas declaradas

Nenhum destes valores e dado do ONS. Sao premissas de cenario.

| Parametro | Valor |
|---|---|
| Capacidade | 50 / 150 / 300 MW por parque |
| Cobertura | 10 / 30 / todos os conjuntos |
| Janela de disponibilidade | 06h-18h |
| Eficiencia | 95% |
| Valor local | R$ 300/MWh |
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
