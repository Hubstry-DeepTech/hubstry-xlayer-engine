# Hubstry X-Layer Engine

Camada de inteligencia decisoria para orquestracao de excedente
energetico (curtailment) no Sistema Interligado Nacional.

## Arquitetura

| Engine | Papel | Estado |
|---|---|---|
| **Observation** | reconstroi o estado observado a partir de dados publicos do ONS | funcional |
| **Heuristic** | identifica recorrencia e regimes; reduz o espaco de busca | em pesquisa |
| **Allocation** | resolve a alocacao do excedente entre destinos, via QUBO | em desenvolvimento |

A decisao final permanece humana. A saida nao e uma ordem, e uma
recomendacao auditavel com evidencia, heuristica, restricoes fisicas e
funcao objetivo declaradas.

## Resultados estabelecidos

Janeiro de 2025, eolica, modalidades Tipo I, II-B e II-C:

- Episodios de restricao por razao energetica formam **blocos sistemicos
  de 9 a 11,5 horas**, com mais de 130 conjuntos cortados simultaneamente.
- **95,4% da energia** cortada por razao energetica esta em episodios de
  4 horas ou mais; pulsos de 30 minutos somam 0,2%.
- Ocorrencias por razao: ENE 22.583, REL 14.666, CNF 4.234. Origem
  sistemica em 37.185 contra 4.298 locais.

Consequencia para o produto: destinos com inercia (armazenamento,
processo industrial continuo) sao viaveis. Carga interrompivel de
resposta rapida atenderia a fracao minoritaria do problema.

## Baseline normativo

O motor e comparado contra a regra vigente, nao contra ausencia de
otimizacao. A NT-ONS DOP 0022/2025 estabelece que renovavel variavel e a
ultima da fila de reducao e que o corte entre usinas e rateio
proporcional. O proprio ONS registra que esse criterio "foi proposto em
uma condicao de ausencia de criterios e em uma situacao de pouca
capacidade instalada de geracao eolica/fotovoltaica".

## Regras de reporte

Resultados de alocacao sao **contrafactuais condicionados a premissas
declaradas de sink**. A formulacao correta e:

> "Sob as premissas X, Y e Z de capacidade, eficiencia e valor dos
> destinos, o Allocation Engine teria absorvido N MWh adicionais em
> relacao ao baseline A e M MWh em relacao ao baseline B."

Nunca: "o X-Layer recuperou N MWh."

## Dados

Nao versionados. Ver `docs/PROVENIENCIA.md` para fonte, licenca,
semantica das colunas e quebras metodologicas conhecidas.

## Restricao etica

As tecnologias da Hubstry nao sao licenciadas para armas autonomas de
inteligencia artificial nem para vigilancia de cidadaos. Clausula
inegociavel.
