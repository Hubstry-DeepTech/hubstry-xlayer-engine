# Proveniencia dos dados e da metodologia

## Fonte

Portal de Dados Abertos do ONS, via bucket publico no Registry of Open
Data on AWS.

- Bucket: `ons-aws-prod-opendata` (regiao `sa-east-1`)
- Acesso: anonimo (`--no-sign-request` / `UNSIGNED`)
- Licenca: CC-BY 4.0
- Os dados fazem parte de processo de consistencia recorrente do ONS
  e podem ser revisados apos a publicacao.

Prefixos usados:

| Prefixo | Conteudo |
|---|---|
| `dataset/restricao_coff_eolica_tm/` | COFF eolica, agregado por usina/conjunto |
| `dataset/restricao_coff_eolica_detail_tm/` | COFF eolica, detalhado por usina |
| `dataset/restricao_coff_fotovoltaica_tm/` | COFF fotovoltaica |
| `dataset/cmo_tm/` | Custo Marginal de Operacao semi-horario |

## Base normativa

- **NT-ONS DOP 0022/2025** â€” Criterios para Gestao de Excedentes
  Energeticos, 19/08/2025. Ordem de prioridade de reducao (secao 5.1.2),
  rateio em tempo real (secao 6.1), titulacao por razao (secao 7.1).
- **RO-AO.BR.13** â€” Apuracao de Restricao de Operacao por Constrained-off,
  Manual de Procedimentos da Operacao, submodulo 5.13.
- **REN ANEEL nÂº 1.030/2022** â€” procedimentos e criterios para apuracao e
  pagamento de restricao de operacao por constrained-off.

## QUEBRA METODOLOGICA â€” LER ANTES DE COMPARAR MESES

A revisao 08 da RO-AO.BR.13 entrou em vigor em **01/08/2025** e alterou o
calculo da Geracao de Referencia Final. Antes disso, cortes nao eram
computados como perda quando a diferenca em relacao a Geracao Limitada
nao ultrapassava 5% ou 5 MW.

A revisao 07, vigente desde 12/05/2025, passou a permitir substituicao de
dados invalidos de vento, irradiancia e disponibilidade eletromecanica em
pos-operacao.

**Consequencia:** os dados de janeiro de 2025 analisados aqui foram
apurados pela metodologia ANTERIOR. Qualquer calibragem feita nesse mes
nao vale para dados de agosto de 2025 em diante, e series que cruzem essa
data tem quebra metodologica que precisa ser declarada.

## Semantica das colunas â€” estabelecida por teste, nao por leitura

O dicionario de dados oficial e ambiguo em pontos criticos. As leituras
abaixo foram estabelecidas empiricamente e ja produziram duas
interpretacoes erradas antes de convergir.

| Coluna | Leitura |
|---|---|
| `val_geracao` | geracao verificada no patamar, MWmed |
| `val_geracaolimitada` | limite comandado pelo ONS, nao uma medicao |
| `val_disponibilidade` | disponibilidade eletromecanica declarada |
| `val_geracaoreferencia` | referencia pela curva de produtividade |
| `val_geracaoreferenciafinal` | menor valor entre disponibilidade e referencia; preenchida SO para REL |

**Pendencia conhecida:** `val_geracaolimitada - val_geracao` produz 29,7%
de valores negativos em janeiro de 2025. A causa provavel esta na secao 7.1
da NT-ONS DOP 0022/2025: pode haver mais de um comando de restricao, com
duracoes distintas, dentro do mesmo patamar de 30 minutos, enquanto a
geracao publicada e a media do patamar inteiro. Sao grandezas de janelas
diferentes. **Nenhum numero de corte agregado deve ir para documento
publico ate isso ser resolvido.**

## Genealogia

A formulacao QUBO deste motor deriva do repositorio
`Hubstry-DeepTech/hubstry-logistics-quantum`, aplicado originalmente a roteamento de
veiculos. A relacao entre os dois problemas e homologica: mesma estrutura
formal de otimizacao combinatoria binaria sob restricoes de capacidade e
sequencia, nao analogia. Aquele repositorio permanece como registro da
anterioridade da formulacao-base (Background IP da Hubstry).
