# Hubstry X-Layer Engine

Camada de inteligência decisória para orquestração de excedente energético
(*curtailment*) no Sistema Interligado Nacional.

Transforma dados públicos de operação em evidência, padrões e recomendações
auditáveis de aproveitamento de excedente. Não reproduz o despacho do ONS,
não substitui o operador, e não trata resultado contrafactual como energia
recuperada.

## Arquitetura

| Engine | Papel | Estado |
|---|---|---|
| **Observation** | Reconstrói o estado observado a partir de dados públicos do ONS | funcional |
| **Heuristic** | Extrai recorrências e regimes operacionais do histórico | em pesquisa |
| **Allocation** | Aloca excedente entre destinos sujeitos a capacidade, localização e eficiência | protótipo |

A decisão final permanece humana. A saída é uma recomendação auditável, com
evidência, premissas e restrições declaradas.

## O problema

O objetivo não é determinar se o corte deveria ter ocorrido. É responder:
dada uma restrição observada e energia que seria perdida, existem destinos
tecnicamente admissíveis capazes de absorver parte desse excedente?

Cada destino é descrito por parâmetros explícitos — capacidade, eficiência,
disponibilidade temporal, localização, valor de referência. Nenhum deles é
dado do ONS.

## Resultados estabelecidos

Janeiro de 2025, geração eólica, modalidades Tipo I, II-B e II-C:

- Episódios de restrição por razão energética formam **blocos sistêmicos de
  9 a 11,5 horas**, com mais de 130 conjuntos cortados simultaneamente.
- **95,4% da energia** cortada por essa razão está em episódios de 4 horas
  ou mais; pulsos de 30 minutos somam 0,2%.
- Ocorrências por razão: ENE 22.583, REL 14.666, CNF 4.234. Origem sistêmica
  em 37.185 contra 4.298 locais.

A duração dos eventos define o que é viável: processos industriais contínuos
podem ser modelados como cargas sem estado interno; armazenamento exige
acoplamento temporal e estado de carga; cargas interrompíveis de resposta
rápida atendem apenas a fração minoritária do problema.

## Baseline normativo

O motor é comparado contra critérios documentados, não contra ausência de
otimização.

A **NT-ONS DOP 0022/2025** (cópia em `docs/`) separa duas fases. Na
programação diária, a seção 5.1.2 descreve o redespacho para fechamento de
balanço. Na execução em tempo real, a seção 6.1 estabelece, para razão
energética, o rateio proporcional ao ponto de partida verificado.

Como os dados de *constrained-off* registram execução, o baseline do projeto
é o critério da seção 6.1. O critério de programação permanece implementado
como referência documental.

| Razão | Critério de execução | Estado |
|---|---|---|
| ENE | proporcional ao ponto de partida (6.1) | reproduzível |
| CNF | sensibilidade equivalente (6.2) | pendente das tabelas do SACI |
| REL | sensibilidade equivalente (6.2) | pendente das tabelas do SACI |

## Escolha do método

**O QUBO não é o método padrão do X-Layer.** Ele é empregado apenas quando
a estrutura do problema introduz competição real entre destinos,
acoplamento temporal ou restrições compartilhadas. Em problemas separáveis,
o motor usa solução analítica exata.

Com um destino co-localizado por parque, sem estado interno e sem disputa,
não há problema combinatório: a solução é `min(excedente, capacidade)`,
exata e em milissegundos.

O QUBO — *Quadratic Unconstrained Binary Optimization* — entra onde há
decisão simultânea: destinos compartilhados entre parques, acoplamento
temporal de armazenamento, limite de infraestrutura comum, funções objetivo
concorrentes.

O método é escolhido pela estrutura do problema, não assumido de partida.

## Gate 3.1A — demonstração de funcionamento

Primeiro cenário sobre evento real de janeiro de 2025: 142 conjuntos,
8.560,5 MWh de excedente modelado, grade de nove combinações entre três
capacidades de destino (50, 150 e 300 MW) e três coberturas (10, 30 e todos
os conjuntos).

No limite superior contrafactual — 300 MW e cobertura total — 7.874,7 MWh
foram alocáveis, com 685,9 MWh residuais.

Isso demonstra que a arquitetura funciona sobre dado real. **Não significa
que essa energia seria recuperável no SIN.** Ver `docs/GATE_3_1A.md` para as
premissas e limitações.

O gate revelou uma propriedade estrutural: mesmo com capacidade agregada
superior ao excedente, permanece energia residual, porque um destino
co-localizado não absorve energia de outro parque. O gargalo pode ser
distribuição espacial, não capacidade total.

## Regra de reporte

Resultados de alocação são contrafactuais condicionados a premissas
declaradas.

> Sob as premissas X, Y e Z de capacidade, eficiência e valor dos destinos,
> o Allocation Engine identificou capacidade de alocação de N MWh do
> excedente modelado.

Nunca: "o X-Layer recuperou N MWh".

## Proveniência e reprodutibilidade

O projeto privilegia reprodutibilidade sobre opacidade. Dados públicos do
ONS, critérios normativos, hipóteses, limitações e resultados intermediários
são documentados. Quando uma interpretação é refutada por teste, a alteração
metodológica é registrada em vez de ocultada.

A cadeia que o repositório permite auditar:

```text
dado público → interpretação → norma → hipótese → teste → alocação → decisão humana
```

## Limitações

- A magnitude de alguns eventos depende de reconstrução normativa ainda em
  aberto.
- CNF e REL dependem das tabelas históricas de sensibilidade do SACI.
- Não há modelo de fluxo de potência; destinos são tratados como
  co-localizados.
- Armazenamento exige acoplamento temporal antes de virar resultado.
- Capacidade, disponibilidade e valor dos destinos são premissas de cenário.

Detalhamento em `docs/PROVENIENCIA.md`.

## Dados

Os arquivos brutos do ONS não são versionados: vão de 3 MB em Parquet a
160 MB em CSV por mês, acima do limite do GitHub. O repositório contém o
código e os metadados necessários à reprodução.

## Estrutura

```text
xlayer/
├── docs/
│   ├── PROVENIENCIA.md
│   ├── GATE_3_1A.md
│   └── NT-ONS_DOP_0022_2025.pdf
├── src/
│   ├── baseline_ons.py
│   ├── xlayer_optimizer.py
│   └── digital_twin/
│       ├── ons_client.py
│       ├── replay_v2.py
│       ├── gate2_*.py
│       └── gate31*.py
├── requirements.txt
└── README.md
```

Os scripts `gate2_*` preservam a trajetória de investigação. Resultados
superados não representam o estado vigente do modelo.

## Estado

Concluído: ingestão dos dados públicos do ONS, Observation Engine,
reconstrução e classificação de eventos, análise de persistência temporal,
baseline de execução para ENE, primeiro cenário de alocação com grade de
sensibilidade, auditoria independente de viabilidade, proveniência
documentada.

Em pesquisa: tabelas de sensibilidade do SACI, reprodução de CNF e REL,
Heuristic Engine, cenários multi-parque, acoplamento temporal de
armazenamento, restrições elétricas de rede.

## Licença

Apache License 2.0, exceto materiais de terceiros identificados em `NOTICE`.
Ver `docs/PROVENIENCIA.md` para a fronteira de licenciamento.
