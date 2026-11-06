# Análise de Divergência Metodológica — `analise-metodologia-01`

**Repositório:** `hubstry-xlayer-engine`  
**Escopo:** Verificação estática (somente leitura sobre o código-fonte e documentação existentes, sem edição de arquivos rastreados e sem commit)  
**Base Normativa:** `docs/NT-ONS_DOP_0022_2025.pdf` (*Critérios para Gestão de Excedentes Energéticos*, ONS, 19/08/2025) e `docs/PROVENIENCIA.md`  

---

## Resumo Executivo

| Ponto | Divergência Verificada? | Critério Aplicável ao Uso do Motor | Impacto Estimado nos Resultados | Recomendação |
| :--- | :--- | :--- | :--- | :--- |
| **1. `replay_v2.py` (`mwh_cortado = val_geracaolimitada * 0.5`)** | **SIM — Procede integralmente.** `replay_v2.py` trata o teto/limite de geração comandado pelo ONS como se fosse o montante de energia cortada. | **Tempo Real (Seção 6.1) e Pós-Operação / Apuração (Seção 7).** O comando enviado via SINapse estabelece o *limite* de geração; o corte é a diferença entre a geração que ocorreria (ou limite/geração na janela) e a geração verificada. | **Crítico (Ordem de Grandeza e Inversão de Ranking):** Infla o corte eólico de jan/2025 em **3,11x** (`1.232,85 GWh` vs. `397,0 GWh` do Gate 3.1, um excesso de **`+835,85 GWh`** ou **`+210,5%`**), sobrevaloriza o potencial bruto em carga flexível (R$ 300/MWh) em **~R$ 250,8 milhões/mês** e exclui usinas totalmente zeradas (`val_geracaolimitada = 0`). | **CORRIGIR** `replay_v2.py` para alinhar ao `Observation Engine` (`gate31_persistencia.py` / `PROVENIENCIA.md`). |
| **2. `baseline_ons.py` (`base="disponibilidade"` em vez de `base="ponto_de_partida"`)** | **SIM — Procede parcialmente (especificamente na função `comparar()`, linha 333, e no bloco `__main__`, linha 373).** Embora `rateio_proporcional()` já tenha `base="ponto_de_partida"` como padrão (linha 173) e exista `baseline_execucao_ene()` (linha 261), a função `comparar()` força `base="disponibilidade"`. | **Tempo Real — Seção 6.1 (`base="ponto_de_partida"`).** O motor avalia eventos executados nos datasets de *constrained-off*, não a programação diária do PDO (Seção 5.1.2-IV). | **Alto na Comparação Por Ativo (`comparar`):** Em jan/2025, os dois critérios divergem em **60,15% das observações válidas** (`17.534` de `29.151`), somando **115.407,7 MWmed (`57.703,85 MWh`)** de divergência acumulada. No evento de pico (`2025-01-13 15:00`), o erro chega a **175,86 MW (`87,93 MWh`, ou R$ 26.379,00 em 30 min)** em um único conjunto, além de zerar o corte de ativos com `val_disponibilidade == 0` e `val_geracao > 0` (3,30% da base). | **CORRIGIR** `comparar()` (e rótulos de `__main__`) para usar `base="ponto_de_partida"`, e **MANTER** `programacao_excedente()` (`base="disponibilidade"`) apenas como referência documental da Seção 5.1.2-IV. |

---

## Ponto 1: Semântica de `val_geracaolimitada` e Cálculo de `mwh_cortado` em `replay_v2.py`

### 1.1 Verificação de Procedência

**A divergência metodológica procede integralmente.** O módulo `src/digital_twin/replay_v2.py` permanece com a hipótese inicial (H1 da `calibragem_v2.py`), segundo a qual a coluna `val_geracaolimitada` representaria diretamente o montante de geração cortada em MWmed. Essa hipótese foi posteriormente refutada por `src/digital_twin/calibragem_v3.py`, `src/digital_twin/gate31_persistencia.py`, `src/digital_twin/gate31b_quarentena.py` e documentada em `docs/PROVENIENCIA.md`, que estabeleceram que `val_geracaolimitada` é o **limite (teto) de geração comandado pelo ONS**, e não a energia cortada.

### 1.2 Citações Exatas dos Arquivos e da Nota Técnica

#### A. O que faz e afirma `src/digital_twin/replay_v2.py`
* **Docstring do módulo (`src/digital_twin/replay_v2.py`, linhas 17–25):**
  ```python
  COLUNA DE CORTE: val_geracaolimitada
  ------------------------------------
  Evidencia da calibragem (janeiro de 2025):
    - soma 2.465.707 MWmed = 1,233 TWh em base semi-horaria
    - geracao eolica no mes: 5,571 TWh
    - taxa resultante: 18,1%, coerente com os 20,6% apurados para
      eolica + solar em 2025 inteiro
    - zero valores negativos em 41.483 linhas
    - preenchida apenas onde ha restricao declarada
  ```
* **Função `preparar()` (`src/digital_twin/replay_v2.py`, linhas 76 e 124–146):**
  ```python
  PASSO_HORAS = 0.5
  ```
  ```python
  def preparar(df: pd.DataFrame) -> pd.DataFrame:
      """
      Isola as linhas com restricao declarada e calcula a energia
      cortada. Nao ha derivacao: val_geracaolimitada e o corte apurado.
      """
      if "val_geracaolimitada" not in df.columns:
          raise ValueError("dataset sem val_geracaolimitada — fonte errada?")

      out = df[df["cod_razaorestricao"].notna()].copy()
      out = out.dropna(subset=["val_geracaolimitada"])

      negativas = int((out["val_geracaolimitada"] < -1e-6).sum())
      if negativas:
          raise ValueError(
              f"{negativas} valores negativos em val_geracaolimitada — "
              "o dataset mudou de semantica, recalibrar antes de usar"
          )

      out["mwh_cortado"] = out["val_geracaolimitada"] * PASSO_HORAS
      out.attrs.update(df.attrs)
      out.attrs["linhas_totais"] = len(df)
      out.attrs["geracao_twh"] = float(df["val_geracao"].sum() * PASSO_HORAS / 1e6)
      return out
  ```

#### B. O que dizem `docs/PROVENIENCIA.md`, `src/digital_twin/calibragem_v3.py` e os Gates 3.1 / 3.1b
* **`docs/PROVENIENCIA.md` (linhas 140–172):**
  ```markdown
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
  ...
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
  ```
* **`src/digital_twin/calibragem_v3.py` (linhas 2–15):**
  ```python
  Calibragem v3 — identificar a formula do corte
  ==============================================
  A v2 derrubou a hipotese de que val_geracaolimitada e o corte: na
  amostra ela aparece na mesma ordem de grandeza da geracao
  (311,196 contra 298,631), o que caracteriza um TETO imposto pela
  restricao, nao um montante cortado.

  Descoberta estrutural da v2: val_geracaoreferenciafinal tem
  exatamente 14.666 valores nao nulos, o mesmo numero de linhas REL.
  A referencia final so e preenchida para restricao por
  indisponibilidade externa eletrica. Isso indica que cada razao de
  restricao tem metodo de apuracao proprio — uma formula unica para
  todas seria errada por construcao.
  ```
* **`src/digital_twin/gate31_persistencia.py` (linhas 36–38 e 99–104):**
  ```python
  Corte = val_geracaolimitada - val_geracao   (formula validada:
  zero negativas em 142 usinas no instante testado; as alternativas
  produziram negativas ou violacoes fisicas).
  ```
  ```python
  out["corte_mw"] = out["val_geracaolimitada"] - out["val_geracao"]

  quarentena = out[out["corte_mw"] < -1e-6]
  out = out[out["corte_mw"] >= -1e-6].copy()
  out["corte_mw"] = out["corte_mw"].clip(lower=0.0)
  out["corte_mwh"] = out["corte_mw"] * PASSO_HORAS
  ```
* **`src/digital_twin/gate31b_quarentena.py` (linhas 11–13 e 187–189):**
  ```python
  Alem disso, duas contas do mesmo dado divergiram por ordem de
  grandeza: o replay somava ~1,2 TWh de corte mensal, o Gate 3.1
  totalizou 397 GWh por episodio. Uma das duas esta errada.
  ```
  ```python
  print("  Referencia publica: 20,6% para eolica + solar em 2025 inteiro.")
  print("  ATENCAO: nao aceitar uma formula porque o percentual se")
  print("  aproxima dessa referencia. Ja erramos assim uma vez.")
  ```

#### C. O que diz a Nota Técnica `docs/NT-ONS_DOP_0022_2025.pdf`
* **Seção 6.1 — Controle de Frequência (Motivo Energético), páginas 15–16:**
  > "Este ponto de partida da restrição corresponde ao mínimo entre a geração verificada e o **limite atual de cada conjunto/usina**, caso o conjunto/usina já esteja sofrendo uma restrição no momento da restrição. Se não houver um limite atual, o ponto de partida da restrição é igual à geração atual do conjunto/usina." (p. 15)
  >
  > "O ponto de partida de uma liberação consiste na diferença entre a potência instalada e o **limite atual de cada conjunto/usina**." (p. 15)
  >
  > "A solicitação da restrição ou elevação da geração calculada pelo Gerdin é entregue aos agentes por meio de mensagens da aplicação SINapse [...] As mensagens informam o motivo da restrição de geração, o ponto de partida utilizado para o cálculo do rateio da restrição, bem como **o valor do novo limite estabelecido para o conjunto/usina**." (p. 16)
* **Seção 6.4 — Classificação do motivo da restrição, página 18:**
  > "Nesses casos, o ponto de partida do valor de geração dos conjuntos de usinas e/ou usinas envolvidos, para o novo motivo da restrição, é **o limite que estava sendo adotado para a restrição anterior**." (p. 18)
* **Seção 7 — Apuração de Restrições de Geração, páginas 19–20:**
  > "Conforme descrito nas seções anteriores, **o comando de limitação de geração é enviado aos Agentes Operadores das usinas e conjuntos eólicos e fotovoltaicos pela equipe de Tempo Real do ONS através do sistema SINapse. Neste sistema, além de enviar o valor de limitação**, é encaminhado adicionalmente o motivo com o detalhamento da informação referente à necessidade de restrição de geração." (p. 19)
  >
  > "Para a apuração dos valores de referência de geração final, o ONS considera: [...]
  > • geração verificada; e
  > • **registro dos valores de limitação de geração solicitados em tempo real pelo ONS**." (p. 20)
* **Seção 7.1 — Ordem de prioridade das restrições de geração, página 21:**
  > "A necessidade de restrição, bem como os motivos, pode variar ao longo do dia, **implicando registros com classificação, duração e valores diferentes dentro do patamar de 30 minutos, utilizado na apuração**." (p. 21)

### 1.3 Critério Aplicável ao Uso do Motor (Programação vs. Tempo Real / Pós-Operação)

* O módulo `replay_v2.py` reconstrói eventos históricos a partir do dataset `dataset/restricao_coff_eolica_tm/`, que consolida restrições **executadas na Operação em Tempo Real (Seção 6)** e **apuradas em Pós-Operação pelo SAGER (Seção 7)**. **Não se trata da fase de Programação Diária da Operação (Seção 5).**
* Na **Operação em Tempo Real (Seção 6.1)**, o Gerdin calcula a redução necessária e envia ao agente, via SINapse, o **novo limite de geração** (`val_geracaolimitada`), e não o delta cortado. Na **Pós-Operação (Seção 7)**, esse valor fica registrado como o limite comandado pelo ONS no patamar semi-horário.

### 1.4 Estimativa de Impacto nos Resultados

1. **Superestimação de 3,11x no Volume Mensal de Energia Cortada (Janeiro de 2025, Eólica):**
   * `replay_v2.py` soma diretamente `val_geracaolimitada * 0.5`, obtendo **`2.465.707 MWmed` = `1.232,85 GWh` (`1,233 TWh`)** no mês, o que leva à taxa aparente de `18,1%` reportada no cabeçalho do script.
   * No `gate31_persistencia.py` (confirmado em `gate31b_quarentena.py`, linha 13), aplicando `corte_mw = val_geracaolimitada - val_geracao` sobre os registros válidos após quarentena (`29.151` observações), o volume total cortado em janeiro de 2025 é de **`397,0 GWh` (`0,397 TWh`)**.
   * **Diferença absoluta:** sobreavaliação de **`+835,85 GWh`** no mês (**`+210,5%`**, ou fator de **`3,11x`**).
2. **Distorção Financeira na Valoração (`valorar()` em `replay_v2.py`, linhas 216–237):**
   * Ao valorar o excedente à premissa de carga flexível (`preco_carga_flexivel = R$ 300,00/MWh`), o volume total mensal em todas as razões passa de **R$ 119,10 milhões** (`397,0 GWh`) para **R$ 369,86 milhões** (`1.232,85 GWh`), inflando o potencial financeiro bruto em **R$ 250,76 milhões** em apenas um mês.
   * Mesmo filtrando apenas razão energética (`ENE`, que representa `66,1%` da soma de `val_geracaolimitada` em `replay_v2.py`, isto é, `~814,9 GWh`), a valoração em carga flexível em `replay_v2.py` atinge **~R$ 244,47 milhões**, mais que o dobro de todo o corte válido do mês.
3. **Inversão Física do Ranking e Exclusão de Cortes Totais no Otimizador (`blocos_do_instante()`, linhas 244–268):**
   * Como `val_geracaolimitada` é o **teto permitido** e não o corte:
     * Um conjunto de grande porte que sofreu um **corte mínimo** (ex.: capacidade de 300 MW limitada pelo ONS a `val_geracaolimitada = 290 MW`) recebe `mwh_cortado = 145 MWh`, sendo selecionado no topo de `.nlargest(top_n, "mwh_cortado")` para alimentar o `HubstryXLayer`.
     * Inversamente, um conjunto que sofreu **corte total** (`val_geracaolimitada = 0 MW`) recebe `mwh_cortado = 0,0 MWh` e é **descartado** pelo filtro `df["mwh_cortado"] > 0` na linha 255.

### 1.5 Recomendação (Manter ou Corrigir)

* **Recomendação: CORRIGIR.**
* **Justificativa e Ação Recomendada:** A implementação atual de `replay_v2.py` contradiz a semântica provada empiricamente no projeto e a definição normativa do SINapse/SAGER na NT-ONS DOP 0022/2025. Deve-se substituir `out["mwh_cortado"] = out["val_geracaolimitada"] * PASSO_HORAS` pela função canônica de cálculo de corte com camada explícita de quarentena (`gate31_persistencia.calcular_corte`), além de atualizar a docstring de `replay_v2.py` para declarar o caráter provisório da magnitude enquanto persistir a investigação de janelas sub-patamar (Seção 7.1 da NT).

---

## Ponto 2: Uso de `base="disponibilidade"` (Seção 5.1.2-IV) vs. `base="ponto_de_partida"` (Seção 6.1) em `baseline_ons.py`

### 2.1 Verificação de Procedência

**A divergência procede especificamente na função `comparar()` (`src/baseline_ons.py`, linhas 333–334) e na demonstração `__main__` (`linhas 372–373`).**  
Cabe registrar uma distinção importante na auditoria do arquivo `src/baseline_ons.py`:
1. Na função principal `rateio_proporcional()` (linha 173), o parâmetro padrão **já foi atualizado** para `base: Literal["disponibilidade", "ponto_de_partida"] = "ponto_de_partida"`, e existe a função dedicada `baseline_execucao_ene()` (linhas 261–269) que chama `base="ponto_de_partida"`.
2. **Contudo**, a função `comparar()` (linhas 312–355) — que é justamente a interface que confronta o baseline normativo do ONS com a alocação do motor (`corte_qubo`) e calcula `perda_baseline_rs` e `ganho_rs` — **sobrescreve o padrão e chama explicitamente `base="disponibilidade"` nas linhas 333–334**, violando o próprio aviso normativo inserido no topo de `src/baseline_ons.py` (linhas 4–30).

### 2.2 Citações Exatas dos Arquivos e da Nota Técnica

#### A. O que faz e afirma `src/baseline_ons.py`
* **Cabeçalho de reclassificação normativa (`src/baseline_ons.py`, linhas 4–30):**
  ```python
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
  ...
  O rateio por disponibilidade permanece neste modulo como
  `programacao_excedente` — referencia documental da fase de
  programacao, nao baseline de execucao.
  ```
* **Assinatura de `rateio_proporcional()` e wrappers (`src/baseline_ons.py`, linhas 170–180 e 249–269):**
  ```python
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
  ```
  ```python
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
  ```
* **Chamada divergente dentro de `comparar()` (`src/baseline_ons.py`, linhas 312–335):**
  ```python
  def comparar(
      usinas: List[Usina],
      corte_necessario_mw: float,
      corte_qubo: Dict[str, float],
      valor_por_usina_rs_mwh: Dict[str, float],
      passo_horas: float = 0.5,
  ) -> pd.DataFrame:
      """
      Compara o baseline normativo com a alocacao proposta pelo motor.
      ...
      """
      base = rateio_proporcional(usinas, corte_necessario_mw,
                                 base="disponibilidade")
      idx = {u.id_ons: u for u in usinas}
  ```
* **Bloco `__main__` (`src/baseline_ons.py`, linhas 372–381):**
  ```python
  print("=== BASELINE NORMATIVO — rateio por disponibilidade ===")
  r1 = rateio_proporcional(usinas, corte, base="disponibilidade")
  ...
  print("\n=== VARIANTE TEMPO REAL — rateio por ponto de partida ===")
  r2 = rateio_proporcional(usinas, corte, base="ponto_de_partida")
  ```

#### B. O que diz `docs/PROVENIENCIA.md`
* **`docs/PROVENIENCIA.md` (linhas 35–48 e 114–119):**
  ```markdown
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
  ```
  ```markdown
  ### Nota de literalidade

  O rateio "proporcional a disponibilidade **declarada de potencia**"
  aparece no item **III**, para hidreletricas com vertimento. O item IV,
  das renovaveis variaveis, diz apenas "proporcional as suas
  disponibilidades". Que ambos usem a mesma base e inferencia nossa, nao
  literalidade do texto.
  ```

#### C. O que diz a Nota Técnica `docs/NT-ONS_DOP_0022_2025.pdf`
* **Seção 5.1.2 — Redespachos para fechamento de balanço de carga e geração (Programação da Operação, página 12):**
  > "Especificamente, nos casos de excedente energético, ou seja, geração prevista maior do que a carga no SIN, é proposto redução de geração seguindo o critério:
  > I. Redução de geração hidroelétrica, sem vertimento;
  > II. Redução de geração termoelétrica despachada fora da ordem de mérito de custo, por ordem decrescente de custo. [...]
  > III. Redução de geração hidroelétrica com vertimento. Caso haja mais de uma usina com vertimento, a redução deverá ocorrer rateando proporcionalmente o montante de redução com a disponibilidade declarada de potência de cada usina, respeitando-se as restrições operativas e ambientais das usinas.
  > IV. Esgotados todos os recursos acima, **reduz-se a geração nas usinas/conjuntos eólicos e/ou solar fotovoltaicos, proporcional às suas disponibilidades**." (p. 12)
* **Seção 6.1 — Controle de Frequência (Motivo Energético) (Operação em Tempo Real, página 15):**
  > "A restrição para o controle de frequência, classificada como motivo energético, é prevista na etapa de programação diária, com definição dos valores previstos de restrição por submercado e por fonte (eólica e fotovoltaica). A execução da restrição por motivo energético em tempo real é realizada utilizando-se os critérios estabelecidos pela Programação e observando-se as variáveis em tempo real, conforme segue.
  > [...]
  > A execução das restrições de geração eólica e/ou fotovoltaica é realizada pela aplicação Gerdin. **O critério adotado para a restrição por motivo energético é o rateio em tempo real, aplicado a todos os conjuntos/usinas eólicas e fotovoltaicas do SIN, proporcional ao ponto de partida verificado no instante da restrição, exceto nos casos em que a parcela correspondente a determinado conjunto/usina possa provocar violação de limites de transmissão ou de outros critérios operativos, situação em que a parcela é ajustada. Este ponto de partida da restrição corresponde ao mínimo entre a geração verificada e o limite atual de cada conjunto/usina, caso o conjunto/usina já esteja sofrendo uma restrição no momento da restrição. Se não houver um limite atual, o ponto de partida da restrição é igual à geração atual do conjunto/usina.**" (p. 15)

### 2.3 Critério Aplicável ao Uso do Motor (Programação vs. Tempo Real)

* **Aplica-se o critério de Operação em Tempo Real — Seção 6.1 (`base="ponto_de_partida"`).**
* Conforme detalhado na Seção 6.1 (p. 15) da `NT-ONS DOP 0022/2025`, a Programação Diária (PDO, Seção 5.1.2) apenas define os montantes previstos de restrição agregados por submercado e por fonte para fechamento de balanço pós-DESSEM. O rateio individualizado que efetivamente limita cada conjunto/usina eólico ou fotovoltaico ocorre **em Tempo Real via aplicação Gerdin**, ponderado pelo **ponto de partida verificado no instante da restrição** ($\min(\text{geração verificada}, \text{limite atual})$). Como o X-Layer atua sobre eventos reais de *constrained-off* (e compara sua alocação contra a regra operacional vigente de execução para razão `ENE`), o baseline normativo correto para `comparar()` é `base="ponto_de_partida"`.

### 2.4 Estimativa de Impacto nos Resultados

1. **Impacto nos Resultados Já Gerados em `docs/GATE_3_1A.md` (Nulo, pois não invocam `comparar()`):**
   * Os scripts `gate31a_analitico.py` (linhas 154–155), `gate31a1_qualidade.py` (linhas 92–93) e `gate31a2_decomposicao.py` (linhas 128–129) invocam `rateio_proporcional()` passando explicitamente `base="ponto_de_partida"` (Baseline A) e `base="disponibilidade"` (Baseline B). Portanto, os números publicados em `docs/GATE_3_1A.md` já distinguem corretamente as duas bases.
2. **Impacto Direto na Função `baseline_ons.comparar()` (Alto quando utilizada para auferir ganho do otimizador QUBO):**
   * **Frequência e Volume Mensal de Divergência (Janeiro de 2025):** Em todo o mês de janeiro de 2025 (`29.151` observações válidas após quarentena), trocar `base="ponto_de_partida"` por `base="disponibilidade"` altera o corte de baseline em **60,15% das observações (`~17.534` registros usina-patamar)**, acumulando uma divergência absoluta de **`115.407,7 MWmed` (`57.703,85 MWh`)** (`PROVENIENCIA.md`, linhas 52–53; `baseline_ons.py`, linhas 22–23). Valorada à tarifa de referência de R$ 300/MWh, essa diferença representa **R$ 17,31 milhões** de realocação entre usinas no mês.
   * **Impacto em Evento de Pico (`2025-01-13 15:00:00`, `142` conjuntos, `8.560,5 MWh`):** A divergência média entre as duas regras é de **`2,05 MW`** por conjunto, mas atinge o máximo de **`175,86 MW` (`87,93 MWh` em um único patamar de 30 minutos)** (`docs/GATE_3_1A.md`, linhas 18–19). Para esse conjunto, `perda_baseline_rs` e `ganho_rs` calculados por `comparar()` ficam distorcidos em **R$ 26.379,00 em um único patamar de 30 minutos** (a R$ 300/MWh).
   * **Vulnerabilidade a Inconsistência de Disponibilidade Declarada (`val_disponibilidade == 0` com `val_geracao > 0`):** Conforme demonstrado no Gate 3.1A.1 (`PROVENIENCIA.md`, linha 185; `gate31a1_qualidade.py`, linhas 6–14), **961 observações (3,30% da base)** em **26 de 156 ativos** apresentam `val_disponibilidade == 0` simultaneamente a `val_geracao > 0` (incluindo todos os 8 conjuntos divergentes do evento de `2025-01-13 15:00`). Com `base="disponibilidade"`, `comparar()` atribui **peso zero (`corte_baseline_mw = 0,0 MW`)** a esses parques, isentando-os artificialmente de corte no baseline e explicando sozinho **19,3%** de toda a divergência mensal (`gate31a2_decomposicao.py`, linha 8).
   * **Saturação Artificial de Cabimento e Redistribuição Iterativa:** No cenário ilustrativo do próprio `baseline_ons.py` (linhas 364–389, corte de `600 MW` em 4 conjuntos), o Conjunto C possui disponibilidade eletromecânica alta (`200 MW`), mas geração eólica momentânea baixa (`60 MW`). Com `base="disponibilidade"`, sua quota inicial ($600 \times \frac{200}{1150} = 104,35\text{ MW}$) excede sua geração (`60 MW`), saturando o ativo em 100% de corte (`60,0 MW`) e redistribuindo `44,35 MW` para os demais conjuntos (`A = 284,21 MW`, `B = 170,53 MW`, `C = 60,00 MW`, `D = 85,26 MW`). Com `base="ponto_de_partida"`, todos os conjuntos sofrem redução uniforme de $66,67\%$ de sua geração sem saturação espúria (`A = 280,00 MW`, `B = 186,67 MW`, `C = 40,00 MW`, `D = 93,33 MW`).

### 2.5 Recomendação (Manter ou Corrigir)

* **Recomendação: CORRIGIR `comparar()` (e os rótulos de `__main__`) e MANTER `programacao_excedente()` como referência documental.**
* **Justificativa e Ação Recomendada:**
  1. **Corrigir `comparar()` (`src/baseline_ons.py`, linhas 333–334):** Alterar a chamada interna de `base="disponibilidade"` para `base="ponto_de_partida"` (ou invocar `baseline_execucao_ene(usinas, corte_necessario_mw)` / expor parâmetro opcional `base: Literal["ponto_de_partida", "disponibilidade"] = "ponto_de_partida"`), garantindo aderência à Seção 6.1 da NT-ONS DOP 0022/2025.
  2. **Corrigir rótulos em `__main__` (`src/baseline_ons.py`, linhas 372–381):** Renomear a saída do bloco demonstrativo para identificar a Seção 6.1 (`ponto_de_partida`) como o **Baseline Normativo de Execução (Tempo Real)** e a Seção 5.1.2-IV (`disponibilidade`) como **Referência Documental de Programação Diária (PDO)**.
  3. **Manter `programacao_excedente()` (`src/baseline_ons.py`, linhas 249–258) e o suporte a `base="disponibilidade"` em `rateio_proporcional()`:** Devem ser preservados no módulo para fins de documentação normativa da fase de programação (Seção 5.1.2-IV) e reprodutibilidade dos experimentos de decomposição dos Gates 3.1A, 3.1A.1 e 3.1A.2.
