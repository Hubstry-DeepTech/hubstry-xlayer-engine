# Proveniencia dos dados e da metodologia

## Fonte

Portal de Dados Abertos do ONS, via bucket publico no Registry of Open
Data on AWS.

- Bucket: `ons-aws-prod-opendata` (regiao `sa-east-1`)
- Acesso: anonimo (`--no-sign-request` / `UNSIGNED`)
- Licenca: CC-BY 4.0
- Os dados fazem parte de processo de consistencia recorrente do ONS e
  podem ser revisados apos a publicacao.

Prefixos usados:

| Prefixo | Conteudo |
|---|---|
| `dataset/restricao_coff_eolica_tm/` | COFF eolica, agregado por usina/conjunto |
| `dataset/restricao_coff_eolica_detail_tm/` | COFF eolica, detalhado por usina |
| `dataset/restricao_coff_fotovoltaica_tm/` | COFF fotovoltaica |
| `dataset/cmo_tm/` | Custo Marginal de Operacao semi-horario |

## Base normativa

- **NT-ONS DOP 0022/2025** — Criterios para Gestao de Excedentes
  Energeticos, 19 de agosto de 2025 (divulgada em 23/09/2025). Copia em
  `docs/`, nao versionada.
- **RO-AO.BR.13** — Apuracao de Restricao de Operacao por
  Constrained-off, Manual de Procedimentos da Operacao, submodulo 5.13.
- **REN ANEEL nº 1.030/2022** — procedimentos e criterios para apuracao
  e pagamento de restricao de operacao por constrained-off.

---

## RECLASSIFICACAO METODOLOGICA (29/08/2026)

A leitura integral da NT-ONS DOP 0022/2025 mostrou que os dois criterios
de rateio antes tratados como concorrentes pertencem a **fases
diferentes** do processo operativo.

| Secao | Fase | Criterio | Papel no projeto |
|---|---|---|---|
| 5.1.2-IV | Programacao da Operacao (PDO, dia anterior) | reducao "proporcional as suas disponibilidades" | referencia documental |
| 6.1 | Operacao em Tempo Real (Gerdin) | rateio proporcional ao ponto de partida | **baseline de execucao para ENE** |

Os datasets de constrained-off registram restricoes **executadas**.
Compara-las contra o criterio de programacao e comparar objetos de
naturezas diferentes.

### Resultado descartado

O achado de que **60,15% das observacoes divergiam** entre os dois
criterios, com divergencia acumulada de **115.407,7 MW**, NAO e evidencia
de conflito entre criterios normativos. E artefato de comparar
programacao com execucao.

**Nao usar como resultado cientifico.** O codigo e o historico dos Gates
3.1A.1 e 3.1A.2 permanecem no repositorio: o erro faz parte da auditoria
do modelo.

O que sobrevive do Gate 3.1A.2: a prova de que a redistribuicao iterativa
nao gera divergencia espuria — zero divergencia nas 1.162 observacoes de
pesos identicos, nas duas versoes do algoritmo. Esse teste continua
valido como verificacao de implementacao.

### Ponto de partida (secao 6.1)

```
ponto_de_partida = min(geracao_verificada, limite_atual)   se ha limite vigente
                 = geracao_atual                            caso contrario
corte_i proporcional a ponto_de_partida_i
```

A norma preve **ajuste de parcela**: o rateio e proporcional ao ponto de
partida "exceto nos casos em que a parcela correspondente a determinado
conjunto/usina possa provocar violacao de limites de transmissao ou de
outros criterios operativos, situacao em que a parcela e ajustada".

Ajustar parcela e normativo. **Como** ajustar, a norma nao especifica. A
redistribuicao proporcional implementada em `baseline_ons.py` e escolha
nossa, compativel com o texto mas nao determinada por ele. Declarar como
tal em qualquer resultado.

### Reprodutibilidade por razao de restricao

| Razao | Criterio de execucao | Situacao |
|---|---|---|
| ENE | 6.1 — rateio proporcional ao ponto de partida | **reproduzivel** |
| CNF | 6.2.1 / 6.2.2 — sensibilidade equivalente, esgotamento em ordem decrescente, rateio proporcional so no ultimo grupo | pendente |
| REL | 6.2.1 / 6.2.2 — idem CNF | pendente |

CNF e REL exigem as tabelas de sensibilidade calculadas pelo SACI e
cadastradas no Gerdin. Sem elas, qualquer reproducao seria invencao. A
propria NT indica que o historico e publicado no SINtegre — frente a
investigar.

`baseline_ons.baseline_execucao_eletrica()` levanta `NotImplementedError`
em vez de produzir numero.

### Cobertura de ENE — atencao ao denominador

Janeiro de 2025, eolica:

| Base | ENE | Proporcao |
|---|---|---|
| ocorrencias de restricao declarada (41.483) | 22.583 | **54,4%** |
| observacoes com corte valido apos quarentena (29.151) | 17.787 | **61,0%** |

A diferenca entre os dois totais sao as 12.332 linhas em quarentena
(corte negativo). **Sempre declarar qual base esta em uso** — os dois
numeros estao corretos e parecem contradicao sem o denominador.

### Nota de literalidade

O rateio "proporcional a disponibilidade **declarada de potencia**"
aparece no item **III**, para hidreletricas com vertimento. O item IV,
das renovaveis variaveis, diz apenas "proporcional as suas
disponibilidades". Que ambos usem a mesma base e inferencia nossa, nao
literalidade do texto.

---

## QUEBRA METODOLOGICA — LER ANTES DE COMPARAR MESES

A revisao 08 da RO-AO.BR.13 alterou o criterio de tolerancia de 5% ou
5 MW usado na verificacao de atendimento ao comando do ONS, para razao
de indisponibilidade externa.

A revisao 07, vigente desde 12/05/2025, passou a permitir substituicao de
dados invalidos de vento, irradiancia e disponibilidade eletromecanica em
pos-operacao.

**Consequencia:** os dados de janeiro de 2025 analisados aqui foram
apurados pela metodologia ANTERIOR a ambas. Calibragens feitas nesse mes
nao valem para dados posteriores, e series que cruzem essas datas tem
quebra metodologica que precisa ser declarada.

---

## Semantica das colunas — estabelecida por teste, nao por leitura

O dicionario de dados oficial e ambiguo em pontos criticos. As leituras
abaixo foram estabelecidas empiricamente e ja produziram duas
interpretacoes erradas antes de convergir.

| Coluna | Leitura |
|---|---|
| `val_geracao` | geracao verificada no patamar, MWmed |
| `val_geracaolimitada` | limite comandado pelo ONS, nao uma medicao |
| `val_disponibilidade` | disponibilidade eletromecanica declarada |
| `val_geracaoreferencia` | referencia pela curva de produtividade |
| `val_geracaoreferenciafinal` | menor valor entre disponibilidade e referencia, rateado proporcionalmente a capacidade instalada de cada usina do conjunto; preenchida **so para REL** |

A norma confirma a leitura de `val_geracaoreferenciafinal`: o calculo e
feito apenas para eventos classificados como razao de indisponibilidade
externa, para fins de pagamento de Encargos de Servicos do Sistema pela
CCEE (secao 7).

### Pendencia conhecida — magnitude do corte

`val_geracaolimitada - val_geracao` produz **29,7%** de valores negativos
em janeiro de 2025 (12.332 de 41.483).

A norma da a causa provavel, na secao 7.1: a necessidade de restricao e
seus motivos **podem variar ao longo do dia, implicando registros com
classificacao, duracao e valores diferentes dentro do patamar de 30
minutos** usado na apuracao. O limite comandado e a geracao media do
patamar sao grandezas de janelas diferentes.

**Nenhum numero de corte agregado deve ir para documento publico ate isso
ser resolvido.** Todos os gates que dependem da magnitude declaram o
valor como provisorio.

### Qualidade dos dados — zeros podem ser normativos

A secao 7.2 estabelece que, se a qualidade dos dados de vento ou
irradiancia for insatisfatoria — invalidos ou congelados por seis minutos
consecutivos dentro do patamar —, **o valor de geracao de referencia da
usina e zero e nao entra no calculo do conjunto**.

Ou seja: zeros nesses campos podem ter origem regulamentar. Isso nao
explica `val_disponibilidade == 0` com `val_geracao > 0`, mas reforca que
zeros nao devem ser tratados como erro sem investigacao.

O Gate 3.1A.1 documenta 961 observacoes (3,30%) com essa inconsistencia,
em 26 de 156 ativos e 20 de 24 dias. **Inconsistencia entre campos
publicados esta demonstrada; a causa — semantica, defasagem temporal,
artefato de apuracao ou preenchimento — permanece aberta.**

---

## Genealogia

A formulacao QUBO deste motor deriva do repositorio
`Hubstry-DeepTech/hubstry-logistics-quantum`, aplicado originalmente a
roteamento de veiculos. A relacao entre os dois problemas e homologica:
mesma estrutura formal de otimizacao combinatoria binaria sob restricoes
de capacidade e sequencia, nao analogia. Aquele repositorio permanece
como registro da anterioridade da formulacao-base (Background IP da
Hubstry).

## Nota sobre o uso do QUBO

No recorte do Gate 3.1A — um sink continuo, co-localizado, por parque,
sem estado interno — **nao existe problema combinatorio**: a solucao
otima e `min(corte, capacidade)`, exata e em milissegundos. A versao QUBO
gerava mais de 700.000 variaveis binarias para reproduzir
aproximadamente o mesmo resultado.

O motor combinatorio ganha lugar quando ha disputa real pela mesma
energia: sinks compartilhados entre parques, acoplamento temporal com
armazenamento, ou limite de linha comum. O X-Layer escolhe o metodo
adequado a estrutura do problema.

---

## Fronteira de licenciamento

Este repositório é distribuído sob **Apache License 2.0** (ver `LICENSE`),
com exceção dos materiais de terceiros identificados em `NOTICE`.

### Materiais não cobertos pela Apache-2.0

| Item | Titular | Regime |
|---|---|---|
| `docs/NT-ONS_DOP_0022_2025.pdf` | ONS | documento público, direitos do ONS |
| Dados operacionais do ONS | ONS | CC-BY 4.0, não versionados |

### Relação com o Hubstry Logistics Quantum

`Hubstry-DeepTech/hubstry-logistics-quantum` é distribuído sob
**CC BY-NC-SA 4.0** e permanece sob essa licença. Os regimes são
deliberadamente distintos: são projetos diferentes, com finalidades
diferentes.

**Este repositório não incorpora, copia nem deriva código daquele.** A
relação entre os dois é de genealogia intelectual — a mesma classe de
reformulação matemática aplicada a outro domínio — e não de derivação de
obra. Todo o código aqui foi escrito originalmente para este projeto.

A formulação de otimização binária quadrática tem publicação anterior
(Zenodo, DOI 10.5281/zenodo.20467804) e deve ser considerada em conjunto
com sua fonte.

### Autoria

Autoria única, sem contribuições de terceiros, em ambos os repositórios.
