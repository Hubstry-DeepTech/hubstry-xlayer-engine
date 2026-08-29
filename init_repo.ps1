<#
=============================================================================
 Hubstry X-Layer Engine — Inicializacao do repositorio
=============================================================================
 Executar em $HOME\dev\xlayer, com o ambiente virtual ja criado.

 SUBSTITUI o migrate_to_xlayer.ps1, que fazia clone do repositorio de
 logistica. Aquele script ficou obsoleto: ja existe trabalho local
 que nao veio de la, e o clone sobrescreveria a estrutura.

 A rastreabilidade de Background IP e preservada de outra forma: o
 repositorio de logistica entra como remoto secundario, e o primeiro
 commit registra a genealogia por escrito.

 NADA E APAGADO. O script nao toca em data\ons\ nem em .venv\.
=============================================================================
#>

$ErrorActionPreference = "Stop"

$OrgName    = "Hubstry-DeepTech"
$NewRepo    = "hubstry-xlayer-engine"
$SourceRepo = "hubstry-logistics-quantum"
$Branch     = "feat/observation-engine"
$BaseBranch = "main"

# --- 0. Verificacoes ---------------------------------------------------
Write-Host "`n[0/7] Verificando o diretorio..." -ForegroundColor Cyan
if (-not (Test-Path ".\src")) {
    throw "Rode este script de dentro de $HOME\dev\xlayer (nao encontrei .\src)."
}
if (Test-Path ".git") {
    throw "Ja existe um repositorio git aqui. Pare e verifique com 'git status'."
}
Get-ChildItem -Recurse .\src -Filter *.py | Select-Object FullName, Length | Format-Table

# --- 1. .gitignore ANTES de qualquer git add ---------------------------
Write-Host "`n[1/7] Escrevendo .gitignore..." -ForegroundColor Cyan
@"
# Dados do ONS — NUNCA commitar.
# O CSV mensal chega a 160 MB e estoura o limite rigido de 100 MB do
# GitHub. O parquet, mesmo com 3-9 MB, infla o repositorio de forma
# irreversivel a cada mes baixado.
data/
*.parquet
*.csv
*.xlsx

# PDFs normativos: sao publicos e grandes; guardar o link, nao o arquivo.
docs/*.pdf

# Ambiente
.venv/
__pycache__/
*.pyc
.ipynb_checkpoints/

# Sistema
Thumbs.db
.DS_Store
"@ | Set-Content -Encoding UTF8 .gitignore

# --- 2. Estrutura ------------------------------------------------------
Write-Host "`n[2/7] Criando diretorios faltantes..." -ForegroundColor Cyan
foreach ($d in @("src", "src\digital_twin", "docs", "tests", "notebooks")) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}
foreach ($f in @("src\__init__.py", "src\digital_twin\__init__.py")) {
    if (-not (Test-Path $f)) { New-Item -ItemType File -Force -Path $f | Out-Null }
}

# --- 3. Dependencias ---------------------------------------------------
Write-Host "`n[3/7] Congelando dependencias..." -ForegroundColor Cyan
pip freeze | Set-Content -Encoding UTF8 requirements.txt
Write-Host "  requirements.txt: $((Get-Content requirements.txt).Count) pacotes"

# --- 4. Documento de proveniencia --------------------------------------
Write-Host "`n[4/7] Registrando proveniencia dos dados..." -ForegroundColor Cyan
@"
# Proveniencia dos dados e da metodologia

## Fonte

Portal de Dados Abertos do ONS, via bucket publico no Registry of Open
Data on AWS.

- Bucket: ``ons-aws-prod-opendata`` (regiao ``sa-east-1``)
- Acesso: anonimo (``--no-sign-request`` / ``UNSIGNED``)
- Licenca: CC-BY 4.0
- Os dados fazem parte de processo de consistencia recorrente do ONS
  e podem ser revisados apos a publicacao.

Prefixos usados:

| Prefixo | Conteudo |
|---|---|
| ``dataset/restricao_coff_eolica_tm/`` | COFF eolica, agregado por usina/conjunto |
| ``dataset/restricao_coff_eolica_detail_tm/`` | COFF eolica, detalhado por usina |
| ``dataset/restricao_coff_fotovoltaica_tm/`` | COFF fotovoltaica |
| ``dataset/cmo_tm/`` | Custo Marginal de Operacao semi-horario |

## Base normativa

- **NT-ONS DOP 0022/2025** — Criterios para Gestao de Excedentes
  Energeticos, 19/08/2025. Ordem de prioridade de reducao (secao 5.1.2),
  rateio em tempo real (secao 6.1), titulacao por razao (secao 7.1).
- **RO-AO.BR.13** — Apuracao de Restricao de Operacao por Constrained-off,
  Manual de Procedimentos da Operacao, submodulo 5.13.
- **REN ANEEL nº 1.030/2022** — procedimentos e criterios para apuracao e
  pagamento de restricao de operacao por constrained-off.

## QUEBRA METODOLOGICA — LER ANTES DE COMPARAR MESES

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

## Semantica das colunas — estabelecida por teste, nao por leitura

O dicionario de dados oficial e ambiguo em pontos criticos. As leituras
abaixo foram estabelecidas empiricamente e ja produziram duas
interpretacoes erradas antes de convergir.

| Coluna | Leitura |
|---|---|
| ``val_geracao`` | geracao verificada no patamar, MWmed |
| ``val_geracaolimitada`` | limite comandado pelo ONS, nao uma medicao |
| ``val_disponibilidade`` | disponibilidade eletromecanica declarada |
| ``val_geracaoreferencia`` | referencia pela curva de produtividade |
| ``val_geracaoreferenciafinal`` | menor valor entre disponibilidade e referencia; preenchida SO para REL |

**Pendencia conhecida:** ``val_geracaolimitada - val_geracao`` produz 29,7%
de valores negativos em janeiro de 2025. A causa provavel esta na secao 7.1
da NT-ONS DOP 0022/2025: pode haver mais de um comando de restricao, com
duracoes distintas, dentro do mesmo patamar de 30 minutos, enquanto a
geracao publicada e a media do patamar inteiro. Sao grandezas de janelas
diferentes. **Nenhum numero de corte agregado deve ir para documento
publico ate isso ser resolvido.**

## Genealogia

A formulacao QUBO deste motor deriva do repositorio
``Hubstry-DeepTech/${SourceRepo}``, aplicado originalmente a roteamento de
veiculos. A relacao entre os dois problemas e homologica: mesma estrutura
formal de otimizacao combinatoria binaria sob restricoes de capacidade e
sequencia, nao analogia. Aquele repositorio permanece como registro da
anterioridade da formulacao-base (Background IP da Hubstry).
"@ | Set-Content -Encoding UTF8 docs\PROVENIENCIA.md

# --- 5. README ---------------------------------------------------------
Write-Host "`n[5/7] Escrevendo README..." -ForegroundColor Cyan
@"
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

Nao versionados. Ver ``docs/PROVENIENCIA.md`` para fonte, licenca,
semantica das colunas e quebras metodologicas conhecidas.

## Restricao etica

As tecnologias da Hubstry nao sao licenciadas para armas autonomas de
inteligencia artificial nem para vigilancia de cidadaos. Clausula
inegociavel.
"@ | Set-Content -Encoding UTF8 README.md

# --- 6. Git ------------------------------------------------------------
Write-Host "`n[6/7] Inicializando git..." -ForegroundColor Cyan
git init -b $BaseBranch
git add .gitignore
git commit -m "chore: .gitignore antes de qualquer dado entrar no indice"

Write-Host "`n  Arquivos que serao versionados:" -ForegroundColor Cyan
git add -A
git status --short

$dados = git status --short | Select-String -Pattern "\.(parquet|csv|xlsx)$"
if ($dados) {
    Write-Host "`n  ABORTANDO: arquivo de dados no indice." -ForegroundColor Red
    $dados
    git reset
    throw "Corrija o .gitignore antes de continuar."
}

git commit -m @"
feat: Observation Engine sobre dados abertos do ONS

Leitura do bucket publico ons-aws-prod-opendata, calibragem empirica da
semantica das colunas de restricao, analise de persistencia dos episodios
e baseline normativo conforme NT-ONS DOP 0022/2025.

Deriva da formulacao QUBO de ${SourceRepo}; a relacao entre roteamento e
alocacao energetica e homologica, nao analogica.

Pendencia registrada em docs/PROVENIENCIA.md: 29,7% de valores negativos
em (limitada - geracao) ainda sem explicacao fechada.
"@

# --- 7. Remotos e push -------------------------------------------------
Write-Host "`n[7/7] Criando remoto e enviando..." -ForegroundColor Cyan
gh repo create "$OrgName/$NewRepo" --private `
    --description "Hubstry X-Layer Engine - orquestracao de excedente energetico via QUBO" `
    --source . --remote origin

git remote add logistics "https://github.com/$OrgName/$SourceRepo.git"
git push -u origin $BaseBranch

git checkout -b $Branch
Write-Host "`nPronto. Branch de trabalho: $Branch" -ForegroundColor Green
Write-Host "Ao terminar uma frente, abra PR contra $BaseBranch e faca o merge:" -ForegroundColor Green
Write-Host "  git push -u origin $Branch" -ForegroundColor DarkGray
Write-Host "  gh pr create --base $BaseBranch --title '...' --body '...'" -ForegroundColor DarkGray
Write-Host "  gh pr merge --merge --delete-branch" -ForegroundColor DarkGray
git remote -v
git log --oneline
