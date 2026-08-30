# Hubstry X-Layer Engine

Camada de inteligência decisória para orquestração de excedente
energético (curtailment) no Sistema Interligado Nacional.

## Arquitetura

| Engine | Papel | Estado |
|---|---|---|
| **Observation** | reconstrói o estado observado a partir de dados públicos do ONS | funcional |
| **Heuristic** | identifica recorrência e regimes; reduz o espaço de busca | em pesquisa |
| **Allocation** | resolve a alocação do excedente entre destinos, via QUBO | em desenvolvimento |

A decisão final permanece humana. A saída não é uma ordem, e uma
recomendação auditável com evidência, heurística, restrições físicas e
função objetivo declaradas.

## Resultados estabelecidos

Janeiro de 2025, eólica, modalidades Tipo I, II-B e II-C:

- Episódios de restrição por razão energética formam **blocos sistêmicos
  de 9 a 11,5 horas**, com mais de 130 conjuntos cortados simultaneamente.
- **95,4% da energia** cortada por razão energética está em episódios de
  4 horas ou mais; pulsos de 30 minutos somam 0,2%.
- Ocorrências por razão: ENE 22.583, REL 14.666, CNF 4.234. Origem
  sistêmica em 37.185 contra 4.298 locais.

Consequência para o produto: destinos com inércia (armazenamento,
processo industrial contínuo) são viáveis. Carga interrompível de
resposta rápida atenderia à fração minoritária do problema.

## Baseline normativo

O motor é comparado contra a regra vigente, não contra ausência de
otimização. A NT-ONS DOP 0022/2025 estabelece que renovável variável é a
última da fila de redução e que o corte entre usinas é rateio
proporcional. O próprio ONS registra que esse critério "foi proposto em
uma condição de ausência de critérios e em uma situação de pouca
capacidade instalada de geração eólica/fotovoltaica".

## Regras de reporte

Resultados de alocação são **contrafactuais condicionados a premissas
declaradas de sink**. A formulação correta é:

> "Sob as premissas X, Y e Z de capacidade, eficiência e valor dos
> destinos, o Allocation Engine teria absorvido N MWh adicionais em
> relação ao baseline A e M MWh em relação ao baseline B."

Nunca: "o X-Layer recuperou N MWh."

## Dados

Não versionados. Ver `docs/PROVENIENCIA.md` para fonte, licença,
semântica das colunas e quebras metodológicas conhecidas.

## Restrição ética

As tecnologias da Hubstry não são licenciadas para armas autônomas de
inteligência artificial nem para vigilância de cidadãos. Cláusula
inegociável.

## Convencao de acentuacao

Markdown (README, docs) usa acentuacao normal do portugues.

Codigo Python � docstrings, comentarios e strings impressas no terminal �
e escrito SEM acentuacao, deliberadamente. O console do Windows usa
codificacao que quebra em caracteres acentuados na saida dos scripts.
Nao "corrigir" automaticamente: a alteracao quebra a execucao.

## Proveni�ncia e reprodutibilidade

O projeto privilegia reprodutibilidade sobre opacidade. Dados p�blicos do
ONS, crit�rios normativos, hip�teses, limita��es e resultados intermedi�rios
s�o documentados. Quando uma interpreta��o � refutada por teste, a altera��o
metodol�gica � registrada em vez de ocultada.

## Licen�a

Apache License 2.0, exceto materiais de terceiros identificados em `NOTICE`.
Ver `docs/PROVENIENCIA.md` para a fronteira de licenciamento.
