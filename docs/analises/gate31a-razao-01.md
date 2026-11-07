# Análise — Gate 3.1A, Mistura de Razões em `usinas_do_instante()` e Persistência de Episódios por Ocorrência Declarada (`gate31a-razao-01`)

**Repositório:** `hubstry-xlayer-engine`  
**Branch:** `analise/gate31a-razao`  
**Dataset Analisado:** `RESTRICAO_COFF_EOLICA_2025_01.parquet` (`dataset/restricao_coff_eolica_tm/`, janeiro de 2025)  
**Script de Reprodução:** [`analises/gate31a_razao_01.py`](../../analises/gate31a_razao_01.py)  
**Restrição de Escopo:** Nenhuma alteração em arquivos existentes de `src/` ou `docs/`.

---

## Resumo Executivo

| Item | Pergunta da Análise | Resultado Verificado (`ENE`, `REL`, `CNF`, `PAR` — Com e Sem Quarentena) |
| :--- | :--- | :--- |
| **1. Instante do Gate 3.1A (`2025-01-13 15:00:00`) e mistura de razões em `usinas_do_instante()`** | `usinas_do_instante()` mistura conjuntos com `cod_razaorestricao != "ENE"`? Qual o impacto no total de MWh e no rateio da Seção 6.1 se o filtro `ENE` for aplicado? | **No código:** **SIM (falha estrutural latente).** Enquanto `escolher_instante()` filtra `(cod_razaorestricao == "ENE") & (corte_mw > 0)`, `usinas_do_instante()` filtra apenas `(din_instante == instante) & (corte_mw > 0)`, omitindo o filtro de razão.<br>**No instante específico `2025-01-13 15:00:00`:** **NÃO há contaminação numérica**, pois 100% dos conjuntos restritos nesse patamar são `ENE` (**`142 ENE`**, **`0 REL`**, **`0 CNF`**, **`0 PAR`**, tanto sem quarentena quanto com quarentena e com `corte_mw > 0`; os outros `14` dos `156` conjuntos do dataset têm `cod_razaorestricao <NA>`). Aplicar o filtro `ENE` em `2025-01-13 15:00:00` altera **`0` conjuntos**, **`0,00 MWh`** (mantendo **`8.560,5435 MWh`** / `17.121,0870 MWmed`) e **`0,00 MW`** no rateio da Seção 6.1.<br>**Nos demais patamares com `ENE` em jan/2025:** Em **19 dos 164 patamares com `ENE` (`11,59%`)** pós-quarentena (`corte_mw > 0`) — incluindo **6 dos Top 10 candidatos de `escolher_instante()`** — e em **23 dos 164 patamares (`14,02%`)** sem quarentena, `usinas_do_instante()` mistura **`CNF` (`233` obs. com `corte > 0`; `396` sem quarentena)** e **`REL` (`6` obs. com `corte > 0`; `37` sem quarentena)** com `ENE` (`0 PAR`), inflando o excedente em **`+589,32 MWh`** e distorcendo o rateio da Seção 6.1 em até **`7,49 MW`** por conjunto `ENE` no algoritmo iterativo com saturação (ou até **`202,76 MW`** no rateio proporcional puro), além de alocar **`17.372,76 MW`** de corte da Seção 6.1 a conjuntos `CNF`/`REL`. |
| **2. Recálculo da duração dos episódios sem usar `corte_mw > 0` vs. `README.md`** | Como mudam a duração dos episódios e a simultaneidade ("9 a 11,5 horas" e "mais de 130 conjuntos simultâneos") ao usar apenas a ocorrência declarada (`cod_razaorestricao` preenchido)? | **Nível 1 — Episódios por Ativo (`id_ons` + `cod_razaorestricao`):** O filtro `corte_mw > 0` combinado à quarentena (`corte_mw < 0`) **fragmentava artificialmente** episódios contínuos de restrição declarada sempre que `val_geracaolimitada - val_geracao <= 0` no meio do evento.<br>• **`ENE`:** Sem quarentena e sem `corte_mw > 0` (`22.583` ocorr.), o número de episódios cai de `2.213` para **`1.266` (`-42,8%`)**, a duração mediana por ativo **mais que triplica de `3,0 h` para `9,5 h`** (média sobe de `3,94 h` para **`8,92 h`**, P75 = **`11,5 h`**, máx = **`11,5 h`**), e os pulsos de 30 min caem de **`492` (`22,2%`) para apenas `1` (`0,1%`)**! Com quarentena mas sem `corte_mw > 0` (`17.787` ocorr.), são `2.198` episódios com mediana de **`3,0 h`** e média de **`4,05 h`**.<br>• **`REL`:** Era a razão mais distorcida (`71,05%` dos registros têm `corte_mw <= 0`). Sem quarentena e sem `corte_mw > 0` (`14.666` ocorr.), a mediana salta de **`1,0 h` para `7,5 h`** e a média de **`1,93 h` para `10,52 h`** (máx **`61,5 h`**; pulsos de 30 min caem de `42,6%` para `0,7%`). Com quarentena e sem `corte_mw > 0` (`8.097` ocorr.), a mediana é **`1,5 h`** e a média **`3,20 h`** (máx `45,0 h`).<br>• **`CNF`:** Sem quarentena e sem `corte_mw > 0` (`4.234` ocorr.), a mediana sobe de **`2,5 h` para `4,0 h`** e a média de **`2,91 h` para `4,87 h`** (máx `13,5 h`). Com quarentena e sem `corte_mw > 0` (`3.267` ocorr.), mediana **`2,5 h`** e média **`2,91 h`**.<br>• **`PAR`:** **`0` ocorrências** em todas as bases.<br>**Nível 2 — Blocos Sistêmicos (por `din_instante` no SIN):**<br>• Em **`ENE`**, os **9 blocos sistêmicos (`164` patamares)** têm exatamente a mesma duração nas 3 bases (mediana **`10,0 h`**, média **`9,11 h`**, máx **`11,5 h`**): **7 blocos** duram entre **`9,0 h` e `11,5 h`**, **1 bloco massivo (`13/jan`, o do Gate 3.1A) dura `7,5 h`**, e **1 microbloco (`19/jan`) dura `1,0 h`**. Já a simultaneidade em `ENE` sobe de **`133–146` conjuntos de pico** (`49` de `164` patamares com `> 130` conjuntos na base com `corte_mw > 0`, e `133–147` / `49` patamares pós-quarentena sem `corte_mw > 0`) para **`154–156` conjuntos de pico** (**`136` de `164` patamares, ou `82,9%`, com `> 130` conjuntos**; mediana de `149,5` conjuntos/patamar) na base sem quarentena!<br>• Em **`REL`**, remover `corte_mw > 0` e a quarentena funde `13` blocos (`279` patamares, mediana `2,5 h`, pico `63` conjuntos) em **`10` blocos (`298` patamares, mediana `10,0 h`, média `14,90 h`, máx `74,5 h`, pico `110` conjuntos)** (ou `11` blocos / `291` patamares, mediana `9,0 h`, pico `72` conjuntos pós-quarentena sem `corte_mw > 0`).<br>• Em **`CNF`**, são **`26` blocos** (`242` patamares sem quarentena, mediana `3,5 h`, média `4,65 h`, máx `15,0 h`, pico `43` conjuntos; `232` patamares com quarentena, mediana `3,5 h`, média `4,46 h`, máx `14,5 h`, pico `39` conjuntos). |
| **3. Denominadores Com e Sem Quarentena por Razão** | Separação estrita entre `ENE`, `REL`, `CNF` e `PAR` em todas as métricas. | • **Total no Parquet (`2025-01`):** `232.128` linhas (`156` conjuntos $\times$ `1.488` patamares), sendo `190.645` (`82,13%`) sem restrição (`<NA>`).<br>• **Sem Quarentena (`cod_razaorestricao` preenchido = `41.483`):** `ENE = 22.583` (`54,44%`), `REL = 14.666` (`35,35%`), `CNF = 4.234` (`10,21%`), `PAR = 0` (`0,00%`).<br>• **Em Quarentena (`corte_mw < -1e-6` = `12.332` / `29,73%`):** `ENE = 4.796` (`21,24%` de `ENE`), `REL = 6.569` (`44,79%` de `REL`), `CNF = 967` (`22,84%` de `CNF`), `PAR = 0`.<br>• **Com Quarentena, sem `corte_mw > 0` (`corte_mw >= -1e-6` = `29.151`):** `ENE = 17.787` (`61,02%`), `REL = 8.097` (`27,78%`), `CNF = 3.267` (`11,21%`), `PAR = 0` (`0,00%`).<br>• **Com Quarentena e `corte_mw == 0` (`4.214` / `10,16%`):** `ENE = 348` (`1,54%` de `ENE`), `REL = 3.852` (`26,26%` de `REL`), `CNF = 14` (`0,33%` de `CNF`), `PAR = 0`.<br>• **Com Quarentena e `corte_mw > 0` (`24.937`):** `ENE = 17.439` (`69,93%`), `REL = 4.245` (`17,02%`), `CNF = 3.253` (`13,04%`), `PAR = 0` (`0,00%`). |

---

## 1. Denominadores Globais de Janeiro de 2025 por Razão (`ENE`, `REL`, `CNF`, `PAR`) — Com e Sem Quarentena

Em atendimento ao item 3, todas as análises deste documento separam explicitamente as quatro razões previstas no dicionário de dados do ONS (`ENE` — razão energética; `REL` — indisponibilidade externa / elétrica; `CNF` — requisitos de confiabilidade elétrica; `PAR` — parecer de acesso) e reportam os denominadores **sem quarentena** e **com quarentena** (com e sem o filtro adicional `corte_mw > 0`).

O dataset `RESTRICAO_COFF_EOLICA_2025_01.parquet` contém **`232.128` linhas** (`156` conjuntos/usinas eólicas $\times$ `1.488` patamares semi-horários em 31 dias). Dessas:
- **`190.645` linhas (`82,13%`)** têm `cod_razaorestricao` nulo (`<NA>`), indicando ausência de restrição declarada no patamar.
- **`41.483` linhas (`17,87%`)** têm `cod_razaorestricao` preenchido (e zero valores ausentes em `val_geracaolimitada` ou `val_geracao`).

Em `src/digital_twin/gate31_persistencia.py` (`calcular_corte()`, linhas 90–110), o cálculo de `corte_mw = val_geracaolimitada - val_geracao` aplica a **quarentena** removendo as linhas com `corte_mw < -1e-6` (`12.332` linhas, ou `29,73%` das ocorrências declaradas), restando **`29.151` linhas pós-quarentena** (`corte_mw >= 0`). Em seguida, `episodios()` (linha 122) e `usinas_do_instante()` (linha 138 de `gate31a_analitico.py`) aplicam um segundo filtro, `corte_mw > 0`, que descarta mais **`4.214` linhas (`10,16%` das ocorrências declaradas)** onde `val_geracaolimitada == val_geracao` (`corte_mw == 0`), reduzindo o denominador final para **`24.937` linhas**.

### 1.1 Tabela Mestre de Denominadores (Observações, Ativos, Patamares, Origem e Energia)

| Razão | Sem Quarentena (`cod_razaorestricao` preenchido) | % do Total s/ Quarentena (`41.483`) | Em Quarentena (`corte_mw < 0`) | Taxa de Quarentena na Razão (%) | Com Quarentena (`corte_mw >= 0`, s/ filtro `> 0`) | % do Total c/ Quarentena (`29.151`) | Pós-Quarentena com `corte_mw == 0` | Com Quarentena e `corte_mw > 0` (Gate 3.1) | % do Total `corte_mw > 0` (`24.937`) | Retenção Final sobre Declarado (%) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`ENE`** | **22.583** | 54,44% | 4.796 | 21,24% | **17.787** | 61,02% | 348 (1,54%) | **17.439** | 69,93% | 77,22% |
| **`REL`** | **14.666** | 35,35% | 6.569 | 44,79% | **8.097** | 27,78% | 3.852 (26,26%) | **4.245** | 17,02% | 28,94% |
| **`CNF`** | **4.234** | 10,21% | 967 | 22,84% | **3.267** | 11,21% | 14 (0,33%) | **3.253** | 13,04% | 76,83% |
| **`PAR`** | **0** | 0,00% | 0 | 0,00% | **0** | 0,00% | 0 (0,00%) | **0** | 0,00% | — |
| **`TODAS`** | **41.483** | **100,00%** | **12.332** | **29,73%** | **29.151** | **100,00%** | **4.214 (10,16%)** | **24.937** | **100,00%** | **60,11%** |

### 1.2 Ativos Distintos, Patamares Distintos, Origem (`SIS` vs. `LOC`) e Energia por Denominador

| Razão | Ativos Distintos (Sem Quar. / Com Quar. / `corte > 0`) | Patamares Distintos no Mês (Sem Quar. / Com Quar. / `corte > 0`) | Origem `SIS` / `LOC` — Sem Quarentena (`41.483`) | Origem `SIS` / `LOC` — Com Quarentena (`29.151`) | Origem `SIS` / `LOC` — Com Quarentena e `corte > 0` (`24.937`) | Energia Cortada Positiva (`corte_mwh_pos`, GWh) | Soma Algébrica Bruta s/ Quarentena (`corte_mwh_bruto`, GWh) |
| :--- | :---: | :---: | :---: | :---: | :---: | ---: | ---: |
| **`ENE`** | 156 / 156 / 156 | 164 / 164 / 164 | 22.583 / 0 | 17.787 / 0 | 17.439 / 0 | 303,352 | 296,271 |
| **`REL`** | 135 / 135 / 135 | 298 / 291 / 279 | 14.567 / 99 | 8.028 / 69 | 4.178 / 67 | 58,089 | 46,883 |
| **`CNF`** | 62 / 57 / 56 | 242 / 232 / 232 | 35 / 4.199 | 33 / 3.234 | 33 / 3.220 | 35,585 | 33,222 |
| **`PAR`** | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0,000 | 0,000 |
| **`TODAS`** | **156 / 156 / 156** | **592 / 584 / 574** | **37.185 / 4.298** | **25.848 / 3.303** | **21.650 / 3.287** | **397,026** | **376,377** |

> **Observações críticas sobre os denominadores:**
> 1. **Descarte assimétrico em `REL`:** Enquanto `ENE` e `CNF` retêm `77,22%` e `76,83%` de suas ocorrências declaradas após quarentena + `corte_mw > 0`, **`REL` perde `71,06%` de seus registros** (`44,79%` na quarentena com `corte_mw < 0` + `26,26%` com `corte_mw == 0`, restando apenas `28,94%`). Isso explica por que a duração dos episódios de `REL` colapsava quando calculada apenas sobre `corte_mw > 0`.
> 2. **Perda de ativos em `CNF`:** Dos `62` ativos com restrição `CNF` declarada no mês, `5` ativos têm 100% de seus registros em quarentena (reduzindo para `57` ativos pós-quarentena) e `1` ativo adicional tem apenas `corte_mw == 0` (reduzindo para `56` ativos em `corte_mw > 0`).
> 3. **Ausência de `PAR`:** Embora `PAR` (*restrição indicada no parecer de acesso*) faça parte do domínio normativo de `cod_razaorestricao` (`src/digital_twin/replay_v2.py`, linha 88), **não há nenhum registro `PAR` em janeiro de 2025** (`0` linhas em todos os denominadores).

---

## 2. Item 1 — Reprodução do Instante do Gate 3.1A e Verificação de `usinas_do_instante()`

### 2.1 Diagnóstico do Código em `src/digital_twin/gate31a_analitico.py`

Nas linhas 131–140 de `src/digital_twin/gate31a_analitico.py`, a seleção do instante e a extração dos conjuntos daquele instante são definidas como:

```python
def escolher_instante(df: pd.DataFrame) -> pd.Timestamp:
    ene = df[(df["cod_razaorestricao"] == "ENE") & (df["corte_mw"] > 0)]
    ene = ene[ene["din_instante"].dt.hour.between(JANELA[0], JANELA[1] - 1)]
    return ene.groupby("din_instante")["corte_mwh"].sum().idxmax()


def usinas_do_instante(df: pd.DataFrame, instante: pd.Timestamp) -> pd.DataFrame:
    return (df[(df["din_instante"] == instante) & (df["corte_mw"] > 0)]
            .sort_values("corte_mwh", ascending=False)
            .reset_index(drop=True))
```

Verifica-se que:
1. `escolher_instante(df)` restringe a busca a `df["cod_razaorestricao"] == "ENE"` (com `corte_mw > 0` e janela `06:00–17:30`), identificando o patamar **`2025-01-13 15:00:00`**.
2. `usinas_do_instante(df, instante)`, porém, **não aplica o filtro `df["cod_razaorestricao"] == "ENE"`**: seleciona todos os conjuntos do `df` naquele `instante` com `corte_mw > 0`, independentemente de sua `cod_razaorestricao`.
3. Caso existam conjuntos com `cod_razaorestricao` igual a `REL`, `CNF` ou `PAR` no mesmo `instante`, `usinas_do_instante()` os mistura aos conjuntos `ENE`, inflando `excedente_evento_MWh` na Pergunta 2 e incluindo conjuntos não-`ENE` no cálculo de `distribuicao_do_corte()` (Pergunta 1), que aplica o rateio da Seção 6.1 da NT-ONS DOP 0022/2025 (exclusivo para razão energética `ENE`) sobre `total = float(recorte["corte_mw"].sum())`.

### 2.2 Verificação Empírica no Instante do Gate 3.1A (`2025-01-13 15:00:00`)

Reproduzindo a execução exata sobre `RESTRICAO_COFF_EOLICA_2025_01.parquet` no instante **`2025-01-13 15:00:00`**, dos **`156` conjuntos** existentes no dataset naquele patamar:
- **`14` conjuntos** não possuem restrição declarada (`cod_razaorestricao` é `<NA>`).
- **`142` conjuntos** possuem restrição declarada (`cod_razaorestricao` preenchido), e **todos os 142 conjuntos têm `cod_razaorestricao == "ENE"`** (com `0` linhas em quarentena e `0` linhas com `corte_mw == 0`).

| Razão (`cod_razaorestricao`) | Conjuntos Sem Quarentena (`cod_razaorestricao` preenchido) | Conjuntos em Quarentena (`corte_mw < 0`) | Conjuntos Com Quarentena (`corte_mw >= 0`) | Conjuntos com `corte_mw == 0` | Conjuntos em `usinas_do_instante()` (`corte_mw > 0`) | `corte_mw` Total (MWmed) | `corte_mwh` Total (MWh) | `val_geracao` Total (MWmed) | `val_geracaolimitada` Total (MWmed) | `val_disponibilidade` Total (MWmed) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **`ENE`** | **142** | 0 | **142** | 0 | **142** | 17.121,0870 | **8.560,5435** | 5.659,7530 | 22.780,8400 | 22.669,3750 |
| **`REL`** | **0** | 0 | **0** | 0 | **0** | 0,0000 | **0,0000** | 0,0000 | 0,0000 | 0,0000 |
| **`CNF`** | **0** | 0 | **0** | 0 | **0** | 0,0000 | **0,0000** | 0,0000 | 0,0000 | 0,0000 |
| **`PAR`** | **0** | 0 | **0** | 0 | **0** | 0,0000 | **0,0000** | 0,0000 | 0,0000 | 0,0000 |
| **`TODAS`** | **142** | **0** | **142** | **0** | **142** | **17.121,0870** | **8.560,5435** | **5.659,7530** | **22.780,8400** | **22.669,3750** |
| *Sem restrição (`<NA>`)* | *14* | — | — | — | *0* | *0,0000* | *0,0000* | *512,9250* | *<NA>* | *1.391,8290* |

> **Nota sobre os "141 conjuntos" no docstring de `gate31a_analitico.py`:** O docstring de `gate31a_analitico.py` (linhas 17 e 31) menciona `141 conjuntos`, enquanto o relatório `docs/GATE_3_1A.md` (linha 4) e o `README.md` (linha 88) reportam `142 conjuntos`. A diferença não decorre de mistura de razões em `15:00`, mas sim do fato de que no patamar imediatamente anterior (`2025-01-13 14:30:00`) havia `142` conjuntos com `ENE` declarada, dos quais `1` entrou em quarentena (`corte_mw < 0`), restando `141` conjuntos com `corte_mw > 0`; já às `15:00:00` nenhum dos `142` conjuntos `ENE` teve corte negativo.

#### Impacto da Aplicação do Filtro `cod_razaorestricao == "ENE"` no Instante `2025-01-13 15:00:00`

Como `REL = 0`, `CNF = 0` e `PAR = 0` no patamar `2025-01-13 15:00:00` (em todos os denominadores, com e sem quarentena), aplicar explicitamente o filtro `df["cod_razaorestricao"] == "ENE"` em `usinas_do_instante()` produz **impacto nulo** nos resultados publicados em `docs/GATE_3_1A.md`:

| Métrica no Instante `2025-01-13 15:00:00` | Sem Filtro `ENE` (Atual) | Com Filtro `ENE` Aplicado | Impacto ($\Delta$) |
| :--- | ---: | ---: | ---: |
| **Conjuntos incluídos (`N`)** | 142 (`142 ENE`) | 142 (`142 ENE`) | **0** |
| **Corte total em potência (`corte_mw`)** | 17.121,0870 MWmed | 17.121,0870 MWmed | **0,0000 MWmed** |
| **Excedente no patamar (`corte_mwh`)** | 8.560,5435 MWh (`8.560,5 MWh`) | 8.560,5435 MWh (`8.560,5 MWh`) | **0,0000 MWh** |
| **Rateio Seção 6.1 (`baseline_A_mw`, iterativo c/ saturação) — Corte alocado** | 5.659,7530 MW | 5.659,7530 MW | **0,0000 MW** |
| **Rateio Seção 6.1 (`baseline_A_mw`, iterativo c/ saturação) — Residual não alocável** | 11.461,3340 MW | 11.461,3340 MW | **0,0000 MW** |
| **Desvio absoluto máximo ou acumulado em `baseline_A_mw` entre as 142 usinas** | — | — | **0,0000 MW** |
| **Divergência média / máxima `|Baseline A - Baseline B|`** | 2,05 MW / 175,86 MW | 2,05 MW / 175,86 MW | **0,00 MW / 0,00 MW** |
| **Alocação no limite superior contrafactual (300 MW, todos os conjuntos)** | 7.874,7 MWh (residual 685,9 MWh) | 7.874,7 MWh (residual 685,9 MWh) | **0,0 MWh** |

### 2.3 Onde a Falha de `usinas_do_instante()` se Manifesta em Janeiro de 2025 (Patamares Mistos)

Embora no patamar específico `2025-01-13 15:00:00` (e em todos os 15 patamares do dia `2025-01-13`, das `09:00` às `16:00`) ocorra exclusivamente a razão `ENE`, a omissão do filtro `cod_razaorestricao == "ENE"` em `usinas_do_instante()` **contamina 19 dos 164 patamares com `ENE` (`11,59%`) na base pós-quarentena (`corte_mw > 0`)** — e **23 dos 164 patamares (`14,02%`) na base sem quarentena** — em janeiro de 2025.

Mais importante: entre os **Top 10 patamares candidatos de maior corte `ENE` na janela `06h–18h`** avaliados por `escolher_instante()`, **6 patamares sofrem mistura com `CNF`** quando passados para `usinas_do_instante()`:
- 4º maior patamar `ENE` (`2025-01-02 17:00:00`): mistura **`118 ENE` + `15 CNF` = `133` conjuntos** (sem quarentena: `118 ENE` + `24 CNF` = `142`).
- 5º maior patamar `ENE` (`2025-01-04 17:30:00`): mistura **`110 ENE` + `28 CNF` = `138` conjuntos** (sem quarentena: `111 ENE` + `31 CNF` = `142`).
- 6º maior patamar `ENE` (`2025-01-03 15:00:00`): mistura **`107 ENE` + `13 CNF` = `120` conjuntos** (sem quarentena: `111 ENE` + `31 CNF` = `142`).
- 7º maior patamar `ENE` (`2025-01-04 16:30:00`): mistura **`110 ENE` + `12 CNF` = `122` conjuntos** (sem quarentena: `111 ENE` + `31 CNF` = `142`).
- 8º maior patamar `ENE` (`2025-01-04 16:00:00`): mistura **`111 ENE` + `13 CNF` = `124` conjuntos** (sem quarentena: `111 ENE` + `31 CNF` = `142`).
- 10º maior patamar `ENE` (`2025-01-04 17:00:00`): mistura **`111 ENE` + `27 CNF` = `138` conjuntos** (sem quarentena: `111 ENE` + `31 CNF` = `142`).

A tabela abaixo apresenta todos os **19 patamares com `ENE` (`corte_mw > 0`, pós-quarentena)** em que `usinas_do_instante()` mistura outras razões (e, entre parênteses, as contagens **sem quarentena**), quantificando o impacto em MWh e no rateio da Seção 6.1 tanto na implementação iterativa com saturação de cabimento (`baseline_ons.rateio_proporcional`, onde `corte_i <= geracao_i`) quanto no rateio proporcional puro sem saturação (`gate31a2_decomposicao.rateio_puro`, onde `corte_i = peso_i / soma(pesos) * total`):

| Instante (`din_instante`) | Conjuntos c/ Quarentena e `corte > 0` (`ENE` / `REL` / `CNF` / `PAR`) | Conjuntos Sem Quarentena (`ENE` / `REL` / `CNF` / `PAR`) | MWh Total s/ Filtro `ENE` | MWh Apenas `ENE` | Impacto MWh Filtro `ENE` ($\Delta$ MWh) | Rateio 6.1 Iterativo: Corte Indevido em Não-`ENE` (MW) | Rateio 6.1 Iterativo: $\sum |\Delta|$ e $\max |\Delta|$ nas Usinas `ENE` (MW) | Rateio 6.1 Puro: Corte Indevido em Não-`ENE` (MW) | Rateio 6.1 Puro: $\sum |\Delta|$ e $\max |\Delta|$ nas Usinas `ENE` (MW) |
| :--- | :---: | :---: | ---: | ---: | ---: | ---: | :---: | ---: | :---: |
| `2025-01-01 05:30` | 61 / 0 / 2 / 0 (tot=63) | 153 / 0 / 3 / 0 (tot=156) | 219,19 | 218,94 | -0,25 | 20,14 | 19,69 / 1,64 | 20,14 | 19,65 / 1,64 |
| `2025-01-02 16:00` | 113 / 0 / 8 / 0 (tot=121) | 118 / 0 / 24 / 0 (tot=142) | 5.031,39 | 5.027,78 | -3,61 | 608,78 | 0,00 / 0,00* | 791,45 | 784,23 / 47,08 |
| `2025-01-02 16:30` | 114 / 0 / 9 / 0 (tot=123) | 118 / 0 / 24 / 0 (tot=142) | 5.329,68 | 5.326,88 | -2,81 | 655,39 | 0,00 / 0,00* | 811,76 | 806,15 / 49,43 |
| `2025-01-02 17:00` | 118 / 0 / 15 / 0 (tot=133) | 118 / 0 / 24 / 0 (tot=142) | 6.477,29 | 6.460,42 | -16,87 | 1.052,02 | 0,00 / 0,00* | 1.323,29 | 1.289,55 / 73,29 |
| `2025-01-02 17:30` | 94 / 0 / 13 / 0 (tot=107) | 118 / 0 / 24 / 0 (tot=142) | 803,66 | 794,86 | -8,79 | 196,59 | 179,08 / 7,49 | 196,61 | 179,02 / 7,49 |
| `2025-01-03 08:00` | 96 / 0 / 2 / 0 (tot=98) | 150 / 0 / 6 / 0 (tot=156) | 703,00 | 702,35 | -0,65 | 8,63 | 7,31 / 0,49 | 8,63 | 7,33 / 0,49 |
| `2025-01-03 08:30` | 99 / 0 / 3 / 0 (tot=102) | 149 / 0 / 7 / 0 (tot=156) | 1.145,00 | 1.144,51 | -0,48 | 10,07 | 9,10 / 0,59 | 10,07 | 9,10 / 0,59 |
| `2025-01-03 09:00` | 101 / 0 / 2 / 0 (tot=103) | 151 / 0 / 5 / 0 (tot=156) | 902,79 | 902,24 | -0,55 | 23,55 | 22,42 / 1,41 | 23,55 | 22,44 / 1,41 |
| `2025-01-03 14:30` | 108 / 0 / 22 / 0 (tot=130) | 111 / 0 / 31 / 0 (tot=142) | 5.710,13 | 5.586,35 | -123,78 | 2.089,56 | 0,00 / 0,00* | 3.816,20 | 3.568,63 / 202,76 |
| `2025-01-03 15:00` | 107 / 0 / 13 / 0 (tot=120) | 111 / 0 / 31 / 0 (tot=142) | 6.263,28 | 6.247,64 | -15,64 | 1.284,23 | 0,00 / 0,00* | 2.846,23 | 2.814,95 / 158,05 |
| `2025-01-03 15:30` | 108 / 0 / 8 / 0 (tot=116) | 112 / 0 / 29 / 0 (tot=141) | 5.246,52 | 5.240,36 | -6,16 | 584,18 | 0,00 / 0,00* | 1.101,62 | 1.089,30 / 60,23 |
| `2025-01-04 09:00` | 76 / 0 / 27 / 0 (tot=103) | 119 / 0 / 37 / 0 (tot=156) | 332,78 | 217,95 | -114,83 | 208,88 | 20,80 / 2,54 | 208,89 | 20,77 / 2,54 |
| `2025-01-04 15:00` | 109 / 0 / 17 / 0 (tot=126) | 111 / 0 / 31 / 0 (tot=142) | 3.730,54 | 3.711,21 | -19,33 | 1.309,35 | 0,00 / 0,00* | 1.663,11 | 1.624,45 / 124,47 |
| `2025-01-04 15:30` | 110 / 0 / 10 / 0 (tot=120) | 111 / 0 / 31 / 0 (tot=142) | 4.981,11 | 4.971,62 | -9,49 | 682,92 | 0,00 / 0,00* | 1.143,53 | 1.124,55 / 91,72 |
| `2025-01-04 16:00` | 111 / 0 / 13 / 0 (tot=124) | 111 / 0 / 31 / 0 (tot=142) | 6.025,14 | 6.011,95 | -13,19 | 909,62 | 0,00 / 0,00* | 1.556,23 | 1.529,84 / 120,21 |
| `2025-01-04 16:30` | 110 / 0 / 12 / 0 (tot=122) | 111 / 0 / 31 / 0 (tot=142) | 6.112,53 | 6.096,79 | -15,74 | 851,52 | 0,00 / 0,00* | 1.366,90 | 1.335,42 / 103,80 |
| `2025-01-04 17:00` | 111 / 0 / 27 / 0 (tot=138) | 111 / 0 / 31 / 0 (tot=142) | 5.781,46 | 5.737,69 | -43,77 | 2.383,29 | 0,00 / 0,00* | 2.592,00 | 2.504,45 / 166,79 |
| `2025-01-04 17:30` | 110 / 0 / 28 / 0 (tot=138) | 111 / 0 / 31 / 0 (tot=142) | 6.405,02 | 6.259,83 | -145,20 | 2.513,92 | 0,00 / 0,00* | 2.948,62 | 2.658,23 / 175,20 |
| `2025-01-26 07:00` | 63 / 6 / 0 / 0 (tot=69) | 122 / 33 / 0 / 0 (tot=155) | 205,32 | 157,14 | -48,18 | 69,12 | 27,22 / 2,58 | 69,12 | 27,24 / 2,58 |
| **Soma / Pico nos 19 patamares** | **1.929 `ENE` / 6 `REL` / 233 `CNF` / 0 `PAR`** | **2.299 `ENE` / 33 `REL` / 396 `CNF` / 0 `PAR`** | **71.405,82** | **70.816,50** | **-589,32 MWh** | **15.462,36 MW** | **258,62 / 7,49 MW** | **25.496,95 MW** | **21.391,47 / 202,76 MW** |

*\*Nos 13 patamares vespertinos assinalados com asterisco, `sum(corte_mw) >= sum(val_geracao)`, fazendo com que o algoritmo iterativo (`baseline_ons.rateio_proporcional`) sature o cabimento (`corte_i = val_geracao_i`) de todas as usinas `ENE` com ou sem filtro, mas atribuindo indevidamente `15.462,36 MW` de corte da Seção 6.1 aos conjuntos `CNF`/`REL`.*  
*(Nota adicional: na base declarada sem quarentena, existem ainda mais **4 patamares** em `2025-01-12` — `16:00`, `16:30`, `17:00` e `17:30` — onde `2` conjuntos `ENE` coexistem com `1` conjunto `REL` em quarentena, totalizando **23 patamares mistos sem quarentena**).*

---

## 3. Itens 2 e 3 — Recálculo da Duração dos Episódios de Janeiro de 2025 (Sem `corte_mw > 0`) e Comparação com o `README.md`

O módulo `src/digital_twin/gate31_persistencia.py` analisa a persistência temporal em dois níveis distintos, ambos citados na seção **"Resultados estabelecidos"** do `README.md` (linhas 34–40):
1. **Episódios por ativo (`episodios()`, linhas 115–172):** sequências de intervalos semi-horários consecutivos ($\Delta t = 30\text{ min}$) para um mesmo par `(id_ons, cod_razaorestricao)`. Daqui provém a afirmação do `README.md`: *"95,4% da energia cortada por essa razão está em episódios de 4 horas ou mais; pulsos de 30 minutos somam 0,2%."*
2. **Blocos sistêmicos (`EVENTO SISTEMICO`, linhas 222–244):** sequências de intervalos semi-horários consecutivos ($\Delta t = 30\text{ min}$) no nível do SIN em que ao menos um conjunto está sob restrição daquela razão, medindo a duração sistêmica e o número de conjuntos simultaneamente restritos por patamar. Daqui provém a afirmação do `README.md`: *"Episódios de restrição por razão energética formam blocos sistêmicos de 9 a 11,5 horas, com mais de 130 conjuntos cortados simultaneamente."*

A seguir, recalculamos **ambos os níveis** a partir apenas da ocorrência de restrição declarada por razão (`cod_razaorestricao` preenchido, **sem usar `corte_mw > 0`**), comparando três denominadores para **`ENE`, `REL`, `CNF`, `PAR` e `TODAS`**:
- **Base 1 — Sem Quarentena e Sem `corte_mw > 0` (Ocorrência Declarada Pura, $N = 41.483$):** todas as linhas com `cod_razaorestricao` preenchido.
- **Base 2 — Com Quarentena (`corte_mw >= -1e-6`) e Sem `corte_mw > 0` ($N = 29.151$):** remove as `12.332` linhas em quarentena (`corte_mw < 0`), mas mantém as `4.214` linhas com `corte_mw == 0`.
- **Base 3 — Com Quarentena e Com `corte_mw > 0` (Referência Original do Gate 3.1, $N = 24.937$):** remove tanto a quarentena (`12.332`) quanto os cortes nulos (`4.214`).

---

### 3.1 Nível 1: Episódios por Ativo (`id_ons` + `cod_razaorestricao`)

#### Tabela Comparativa de Duração dos Episódios por Ativo (Todas as Bases e Razões)

| Base / Denominador | Razão | Ocorrências (`N`) | Ativos Distintos | Nº de Episódios | Duração P25 (h) | Duração Mediana (h) | Duração Média (h) | Duração P75 (h) | Duração P90 (h) | Duração Máx (h) | Pulsos de 30 min (`N` / % ep. / % MWh) | Episódios $\ge 4\text{ h}$ (`N` / % ep. / % ocorr. / % MWh) | Episódios `9h–11,5h` (`N` / % ep.) |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | :---: |
| **Base 1: Sem Quarentena, Sem `corte > 0`** *(Ocorrência Declarada)* | **`ENE`** | **22.583** | 156 | **1.266** | 7,00 | **9,50** | **8,92** | 11,50 | 11,50 | **11,50** | **1** (0,1% / 0,00%) | **1.216** (96,1% / 99,3% / **99,8%**) | **745** (58,8%) |
| **Base 1: Sem Quarentena, Sem `corte > 0`** *(Ocorrência Declarada)* | **`REL`** | **14.666** | 135 | **697** | 4,00 | **7,50** | **10,52** | 14,50 | 21,00 | **61,50** | **5** (0,7% / 0,00%) | **546** (78,3% / 95,4% / **89,8%**) | **83** (11,9%) |
| **Base 1: Sem Quarentena, Sem `corte > 0`** *(Ocorrência Declarada)* | **`CNF`** | **4.234** | 62 | **435** | 2,50 | **4,00** | **4,87** | 7,50 | 8,00 | **13,50** | **10** (2,3% / 0,04%) | **236** (54,3% / 77,9% / **86,5%**) | **3** (0,7%) |
| **Base 1: Sem Quarentena, Sem `corte > 0`** *(Ocorrência Declarada)* | **`PAR`** | **0** | 0 | **0** | — | — | — | — | — | — | 0 | 0 | 0 |
| **Base 1: Sem Quarentena, Sem `corte > 0`** *(Ocorrência Declarada)* | **`TODAS`** | **41.483** | 156 | **2.398** | 5,50 | **8,00** | **8,65** | 11,50 | 11,50 | **61,50** | **16** (0,7% / 0,00%) | **1.998** (83,3% / 95,8% / **97,1%**) | **831** (34,7%) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`ENE`** | **17.787** | 156 | **2.198** | 1,00 | **3,00** | **4,05** | 7,00 | 9,00 | **11,50** | **478** (21,7% / 0,19%) | **995** (45,3% / 81,9% / **95,5%**) | **276** (12,6%) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`REL`** | **8.097** | 135 | **1.266** | 0,50 | **1,50** | **3,20** | 4,00 | 8,00 | **45,00** | **417** (32,9% / 3,31%) | **337** (26,6% / 72,3% / **67,8%**) | **47** (3,7%) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`CNF`** | **3.267** | 57 | **561** | 1,00 | **2,50** | **2,91** | 4,00 | 6,00 | **13,50** | **114** (20,3% / 0,62%) | **163** (29,1% / 58,5% / **69,3%**) | **1** (0,2%) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`PAR`** | **0** | 0 | **0** | — | — | — | — | — | — | 0 | 0 | 0 |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`TODAS`** | **29.151** | 156 | **4.025** | 0,50 | **2,00** | **3,62** | 6,00 | 8,50 | **45,00** | **1.009** (25,1% / 0,69%) | **1.495** (37,1% / 76,6% / **89,1%**) | **324** (8,0%) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original Gate 3.1)* | **`ENE`** | **17.439** | 156 | **2.213** | 1,00 | **3,00** | **3,94** | 7,00 | 9,00 | **11,50** | **492** (22,2% / 0,20%) | **983** (44,4% / 81,0% / **95,4%**) | **245** (11,1%) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original Gate 3.1)* | **`REL`** | **4.245** | 135 | **1.099** | 0,50 | **1,00** | **1,93** | 2,00 | 4,50 | **26,50** | **468** (42,6% / 5,02%) | **135** (12,3% / 49,8% / **60,6%**) | **13** (1,2%) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original Gate 3.1)* | **`CNF`** | **3.253** | 56 | **559** | 1,00 | **2,50** | **2,91** | 4,00 | 6,00 | **13,50** | **114** (20,4% / 0,62%) | **162** (29,0% / 58,4% / **69,3%**) | **1** (0,2%) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original Gate 3.1)* | **`PAR`** | **0** | 0 | **0** | — | — | — | — | — | — | 0 | 0 | 0 |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original Gate 3.1)* | **`TODAS`** | **24.937** | 156 | **3.871** | 0,50 | **2,00** | **3,22** | 5,00 | 8,00 | **26,50** | **1.074** (27,7% / 0,94%) | **1.280** (33,1% / 72,8% / **88,0%**) | **259** (6,7%) |

#### Distribuição Completa por Faixas de Duração (Nível por Ativo — Base 1 vs. Base 2 vs. Base 3)

| Razão | Faixa de Duração | Base 1: Sem Quarentena, Sem `corte > 0` (`N` ep. / % ep. / % ocorr. / % MWh_pos) | Base 2: Com Quarentena, Sem `corte > 0` (`N` ep. / % ep. / % ocorr. / % MWh_pos) | Base 3: Com Quarentena, Com `corte > 0` (`N` ep. / % ep. / % ocorr. / % MWh_pos) |
| :--- | :--- | :---: | :---: | :---: |
| **`ENE`** | `30 min` (1 int.) | 1 (0,1% / 0,0% / 0,0%) | 478 (21,7% / 2,7% / 0,2%) | 492 (22,2% / 2,8% / 0,2%) |
| **`ENE`** | `1h – 1h30` (2–3 int.) | 27 (2,1% / 0,2% / 0,1%) | 371 (16,9% / 4,9% / 0,8%) | 373 (16,9% / 5,0% / 0,8%) |
| **`ENE`** | `2h – 3h30` (4–7 int.) | 22 (1,7% / 0,4% / 0,1%) | 354 (16,1% / 10,5% / 3,5%) | 365 (16,5% / 11,1% / 3,6%) |
| **`ENE`** | `4h – 7h30` (8–15 int.) | 395 (31,2% / 23,5% / 24,1%) | 610 (27,8% / 40,8% / 40,6%) | 634 (28,6% / 43,0% / 42,7%) |
| **`ENE`** | `8h – 23h30` (16–47 int.) | **821 (64,8% / 75,8% / 75,7%)** | 385 (17,5% / 41,1% / 54,9%) | 349 (15,8% / 38,0% / 52,7%) |
| **`ENE`** | `>= 24h` ($\ge 48$ int.) | 0 (0,0% / 0,0% / 0,0%) | 0 (0,0% / 0,0% / 0,0%) | 0 (0,0% / 0,0% / 0,0%) |
| **`REL`** | `30 min` (1 int.) | 5 (0,7% / 0,0% / 0,0%) | 417 (32,9% / 5,2% / 3,3%) | 468 (42,6% / 11,0% / 5,0%) |
| **`REL`** | `1h – 1h30` (2–3 int.) | 47 (6,7% / 0,8% / 0,8%) | 288 (22,7% / 8,3% / 12,2%) | 311 (28,3% / 16,9% / 17,9%) |
| **`REL`** | `2h – 3h30` (4–7 int.) | 99 (14,2% / 3,8% / 9,4%) | 224 (17,7% / 14,2% / 16,7%) | 185 (16,8% / 22,3% / 16,4%) |
| **`REL`** | `4h – 7h30` (8–15 int.) | 208 (29,8% / 15,8% / 22,2%) | 205 (16,2% / 28,0% / 24,4%) | 81 (7,4% / 20,2% / 19,2%) |
| **`REL`** | `8h – 23h30` (16–47 int.) | **281 (40,3% / 52,1% / 34,7%)** | 122 (9,6% / 35,8% / 37,5%) | 53 (4,8% / 28,3% / 37,4%) |
| **`REL`** | `>= 24h` ($\ge 48$ int.) | **57 (8,2% / 27,5% / 32,9%)** | 10 (0,8% / 8,4% / 5,8%) | 1 (0,1% / 1,2% / 4,0%) |
| **`CNF`** | `30 min` (1 int.) | 10 (2,3% / 0,2% / 0,0%) | 114 (20,3% / 3,5% / 0,6%) | 114 (20,4% / 3,5% / 0,6%) |
| **`CNF`** | `1h – 1h30` (2–3 int.) | 39 (9,0% / 2,1% / 0,9%) | 91 (16,2% / 6,8% / 2,9%) | 90 (16,1% / 6,7% / 2,9%) |
| **`CNF`** | `2h – 3h30` (4–7 int.) | 150 (34,5% / 19,7% / 12,6%) | 193 (34,4% / 31,2% / 27,2%) | 193 (34,5% / 31,4% / 27,2%) |
| **`CNF`** | `4h – 7h30` (8–15 int.) | **170 (39,1% / 45,9% / 51,0%)** | 141 (25,1% / 46,2% / 56,4%) | 140 (25,0% / 46,1% / 56,4%) |
| **`CNF`** | `8h – 23h30` (16–47 int.) | **66 (15,2% / 32,1% / 35,6%)** | 22 (3,9% / 12,3% / 12,9%) | 22 (3,9% / 12,3% / 12,9%) |
| **`CNF`** | `>= 24h` ($\ge 48$ int.) | 0 (0,0% / 0,0% / 0,0%) | 0 (0,0% / 0,0% / 0,0%) | 0 (0,0% / 0,0% / 0,0%) |

> **Mecanismo da distorção identificada no Nível 1 (Por Ativo):**
> Quando `gate31_persistencia.py` descartava intervalos em quarentena (`val_geracaolimitada < val_geracao`) e intervalos com `corte_mw == 0` **antes** de verificar a adjacência temporal (`din_instante.diff().ne(PASSO)`), qualquer patamar intermediário em que a geração verificada igualasse ou superasse o limite comandado **partia um episódio contínuo de restrição declarada em dois ou mais pedaços menores**.
> - Em **`ENE`**, remover `corte_mw > 0` mantendo a quarentena (Base 2 vs. Base 3) altera pouco a mediana (`3,00 h` $\rightarrow$ `3,00 h`; média `3,94 h` $\rightarrow$ `4,05 h`), porque há apenas `348` registros `ENE` com `corte_mw == 0`. Porém, ao remover também o descarte da quarentena (Base 1, `22.583` ocorrências declaradas), **`947` quebras artificiais desaparecem** (`2.213` $\rightarrow$ `1.266` episódios), a duração mediana por conjunto salta de **`3,00 h` para `9,50 h`**, e **`491` dos `492` supostos "pulsos de 30 minutos" revelam ser apenas fragmentos isolados entre intervalos em quarentena**!
> - Em **`REL`**, tanto os `3.852` registros com `corte_mw == 0` quanto os `6.569` registros em quarentena fragmentavam severamente os episódios: só remover `corte_mw > 0` mantendo a quarentena (Base 2) já eleva a mediana de **`1,00 h` para `1,50 h`** e a média de **`1,93 h` para `3,20 h`** (máximo de `26,5 h` para `45,0 h`); na ocorrência declarada sem quarentena (Base 1), a mediana de `REL` atinge **`7,50 h`** e a média **`10,52 h`** (máximo de **`61,50 h`** contínuas em um mesmo conjunto!).

---

### 3.2 Nível 2: Blocos Sistêmicos (Simultaneidade por `din_instante` no SIN)

#### Resumo Comparativo dos Blocos Sistêmicos por Razão e Denominador

| Base / Denominador | Razão | Ocorrências (`N`) | Patamares no Mês | Nº de Blocos Sistêmicos | Duração Mín. (h) | Duração Mediana (h) | Duração Média (h) | Duração Máx. (h) | Blocos entre `9h` e `11,5h` | Blocos entre `7,5h` e `11,5h` | Pico de Conjuntos Simultâneos (`ativos_max`) | Mediana de Conjuntos Simultâneos por Patamar | Blocos com Pico `> 130` Conjuntos | Patamares com `> 130` (`>= 130`) Conjuntos Simultâneos |
| :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | :---: | ---: | ---: | :---: | :---: |
| **Base 1: Sem Quarentena, Sem `corte > 0`** | **`ENE`** | 22.583 | **164** | **9** | 1,00 | **10,00** | **9,11** | **11,50** | **7 de 9** | **8 de 9** | **156** | **149,5** | **8 de 9** | **136 / 164 (82,9%)** (136 $\ge 130$) |
| **Base 1: Sem Quarentena, Sem `corte > 0`** | **`REL`** | 14.666 | **298** | **10** | 1,00 | **10,00** | **14,90** | **74,50** | 2 de 10 | 2 de 10 | **110** | **47,0** | 0 de 10 | 0 / 298 (0,0%) |
| **Base 1: Sem Quarentena, Sem `corte > 0`** | **`CNF`** | 4.234 | **242** | **26** | 1,00 | **3,50** | **4,65** | **15,00** | 0 de 26 | 3 de 26 | **43** | **8,0** | 0 de 26 | 0 / 242 (0,0%) |
| **Base 1: Sem Quarentena, Sem `corte > 0`** | **`PAR`** | 0 | **0** | **0** | — | — | — | — | 0 | 0 | **0** | — | 0 | 0 |
| **Base 1: Sem Quarentena, Sem `corte > 0`** | **`TODAS`** | 41.483 | **592** | **26** | 1,00 | **8,25** | **11,38** | **84,00** | 4 de 26 | 5 de 26 | **156** | **50,0** | 8 de 26 | **151 / 592 (25,5%)** (151 $\ge 130$) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`ENE`** | 17.787 | **164** | **9** | 1,00 | **10,00** | **9,11** | **11,50** | **7 de 9** | **8 de 9** | **147** | **118,0** | **8 de 9** | **49 / 164 (29,9%)** (53 $\ge 130$) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`REL`** | 8.097 | **291** | **11** | 0,50 | **9,00** | **13,23** | **74,50** | 3 de 11 | 3 de 11 | **72** | **24,0** | 0 de 11 | 0 / 291 (0,0%) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`CNF`** | 3.267 | **232** | **26** | 0,50 | **3,50** | **4,46** | **14,50** | 0 de 26 | 3 de 26 | **39** | **6,0** | 0 de 26 | 0 / 232 (0,0%) |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`PAR`** | 0 | **0** | **0** | — | — | — | — | 0 | 0 | **0** | — | 0 | 0 |
| **Base 2: Com Quarentena (`corte >= 0`), Sem `corte > 0`** | **`TODAS`** | 29.151 | **584** | **27** | 0,50 | **7,50** | **10,81** | **84,00** | 5 de 27 | 6 de 27 | **147** | **31,0** | 8 de 27 | **52 / 584 (8,9%)** (57 $\ge 130$) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original)* | **`ENE`** | 17.439 | **164** | **9** | 1,00 | **10,00** | **9,11** | **11,50** | **7 de 9** | **8 de 9** | **146** | **116,0** | **8 de 9** | **49 / 164 (29,9%)** (50 $\ge 130$) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original)* | **`REL`** | 4.245 | **279** | **13** | 0,50 | **2,50** | **10,73** | **74,50** | 4 de 13 | 4 de 13 | **63** | **12,0** | 0 de 13 | 0 / 279 (0,0%) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original)* | **`CNF`** | 3.253 | **232** | **26** | 0,50 | **3,50** | **4,46** | **14,50** | 0 de 26 | 3 de 26 | **39** | **6,0** | 0 de 26 | 0 / 232 (0,0%) |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original)* | **`PAR`** | 0 | **0** | **0** | — | — | — | — | 0 | 0 | **0** | — | 0 | 0 |
| **Base 3: Com Quarentena e Com `corte > 0`** *(Original)* | **`TODAS`** | 24.937 | **574** | **29** | 0,50 | **4,00** | **9,90** | **84,00** | 6 de 29 | 7 de 29 | **146** | **23,0** | 8 de 29 | **52 / 574 (9,1%)** (54 $\ge 130$) |

#### Detalhamento dos 9 Blocos Sistêmicos de `ENE` (Comparação Direta entre as 3 Bases)

Todos os 9 blocos sistêmicos de `ENE` possuem **exatamente os mesmos instantes de início e fim (`164` patamares)** nas três bases, mudando apenas o número de conjuntos simultaneamente restritos por patamar:

| # | Início | Fim | Intervalos | Duração (h) |Energia Positiva (`MWh_pos`) | Conjuntos Simultâneos **Sem Quarentena, Sem `corte > 0`** (Mín / Med / Máx \| Patamares `> 130`) | Conjuntos Simultâneos **Com Quarentena, Sem `corte > 0`** (Mín / Med / Máx \| Patamares `> 130`) | Conjuntos Simultâneos **Com Quarentena, Com `corte > 0`** (Mín / Med / Máx \| Patamares `> 130`) |
| :-: | :--- | :--- | ---: | ---: | ---: | :---: | :---: | :---: |
| **1** | `2025-01-01 05:30` | `2025-01-01 16:30` | 23 | **11,5 h** | 16.732,9 | 141 / **156,0** / **156** \| **23/23** | 39 / 92,0 / **143** \| 6/23 | 38 / 91,0 / **143** \| 6/23 |
| **2** | `2025-01-02 06:30` | `2025-01-02 17:30` | 23 | **11,5 h** | 56.302,2 | 118 / **142,0** / **156** \| **19/23** | 83 / 117,0 / **133** \| 3/23 | 82 / 116,0 / **133** \| 3/23 |
| **3** | `2025-01-03 05:30` | `2025-01-03 15:30` | 21 | **10,5 h** | 54.570,3 | 41 / **150,0** / **156** \| **17/21** | 12 / 118,0 / **141** \| 7/21 | 12 / 115,0 / **141** \| 7/21 |
| **4** | `2025-01-04 09:00` | `2025-01-04 17:30` | 18 | **9,0 h** | 51.867,5 | 111 / **142,0** / **156** \| **11/18** | 77 / 127,5 / **139** \| 6/18 | 76 / 123,5 / **139** \| 6/18 |
| **5** | `2025-01-05 07:00` | `2025-01-05 18:00` | 23 | **11,5 h** | 27.804,3 | 141 / **155,0** / **155** \| **23/23** | 55 / 119,0 / **141** \| 6/23 | 51 / 119,0 / **141** \| 6/23 |
| **6** | `2025-01-12 08:30` | `2025-01-12 17:30` | 19 | **9,5 h** | 28.451,2 | 2 / **140,0** / **154** \| **14/19** | 2 / 119,0 / **140** \| 7/19 | 2 / 119,0 / **140** \| 7/19 |
| **7** | `2025-01-13 09:00` | `2025-01-13 16:00` | 15 | **7,5 h** | 40.060,2 | 1 / **142,0** / **155** \| **14/15** | 1 / 137,0 / **142** \| 11/15 | 1 / 137,0 / **142** \| 11/15 |
| **8** | `2025-01-19 12:00` | `2025-01-19 12:30` | 2 | **1,0 h** | 32,4 | 13 / **13,0** / **13** \| **0/2** | 8 / 8,5 / **9** \| 0/2 | 8 / 8,5 / **9** \| 0/2 |
| **9** | `2025-01-26 07:00` | `2025-01-26 16:30` | 20 | **10,0 h** | 27.530,8 | 98 / **154,0** / **155** \| **15/20** | 64 / 111,0 / **147** \| 3/20 | 63 / 98,0 / **146** \| 3/20 |

---

### 3.3 Confronto Ponto a Ponto com as Afirmações do `README.md`

| Afirmação no `README.md` (linhas 36–40) | Verificação na Base Original do Gate 3.1 (Com Quarentena e `corte_mw > 0`) | Verificação pelo Recálculo sem `corte_mw > 0` (Com Quarentena vs. Sem Quarentena) | Diagnóstico e Precisão Metodológica |
| :--- | :--- | :--- | :--- |
| **1. *"Episódios de restrição por razão energética formam blocos sistêmicos de 9 a 11,5 horas"*** | Nos **9 blocos sistêmicos de `ENE`**, **7 blocos** duram entre **`9,0 h` e `11,5 h`** (`9,0 h`, `9,5 h`, `10,0 h`, `10,5 h`, `11,5 h`), mas o **bloco de `2025-01-13` (40,1 GWh, 4º maior em energia e justamente o evento do Gate 3.1A) dura `7,5 horas` (`15` intervalos, `09:00–16:00`)**, e há um 9º bloco em `19/jan` de **`1,0 hora`**. Já no nível **por ativo**, a mediana era de apenas **`3,0 h`** (média `3,94 h`). | • **No nível de blocos sistêmicos de `ENE`:** A duração dos 9 blocos é **idêntica** sem `corte_mw > 0` (tanto com quarentena quanto sem quarentena): mediana de **`10,0 h`**, média de **`9,11 h`**, máximo de **`11,5 h`** (`7` blocos de `9,0 h` a `11,5 h`, `1` bloco de `7,5 h` em `13/jan` e `1` bloco de `1,0 h` em `19/jan`).<br>• **No nível por ativo individual de `ENE`:** Ao remover `corte_mw > 0` e a quarentena (`22.583` ocorr.), **os próprios episódios individuais por conjunto passam a ter mediana de `9,5 h` (média `8,92 h`, P75 `11,5 h`, máx `11,5 h`)**, convergindo para a faixa de `9 a 11,5 h`!<br>• **Nas demais razões (`REL` e `CNF`):** Em `REL`, remover `corte_mw > 0` e quarentena unifica `13` blocos (`mediana 2,5 h`) em **`10` blocos com mediana de `10,0 h`, média de `14,90 h` e máximo de `74,5 h`** (ou `11` blocos com mediana de `9,0 h` pós-quarentena sem `corte > 0`). Em `CNF`, são `26` blocos com mediana de **`3,5 h`** e máximo de **`15,0 h`** (`14,5 h` pós-quarentena). | A faixa de **"9 a 11,5 horas"** para `ENE` descreve com exatidão **7 dos 8 grandes blocos sistêmicos** (exceto `13/jan`, que dura **`7,5 h`**, razão pela qual a Limitação 3 de `docs/GATE_3_1A.md` é imprecisa para o próprio dia `13/jan`), e passa a descrever **também a duração mediana por ativo individual (`9,5 h` a `11,5 h`)** quando medida pela ocorrência declarada sem quarentena e sem `corte_mw > 0`. |
| **2. *"...com mais de 130 conjuntos cortados simultaneamente"*** | Nos **8 blocos principais de `ENE`**, o pico de conjuntos simultâneos (`ativos_max`) varia de **`133` a `146` conjuntos**. Contudo, dentro desses blocos, a mediana por patamar varia de `91,0` a `137,0` conjuntos, e apenas **`49` dos `164` patamares (`29,9%`)** têm `> 130` conjuntos simultâneos com `corte_mw > 0`. | • **Com quarentena, sem `corte_mw > 0` (`ENE`):** Pico nos 8 blocos principais varia de **`133` a `147` conjuntos** (`49` de `164` patamares com `> 130` conjuntos; mediana global de `118,0` conjuntos/patamar).<br>• **Sem quarentena, sem `corte_mw > 0` (`ENE`):** O pico nos 8 blocos principais salta para **`154` a `156` conjuntos** (de `156` conjuntos totais do dataset!), a mediana global sobe para **`149,5` conjuntos/patamar**, e **`136` dos `164` patamares (`82,9%`)** — ou `136` dos `162` patamares dos 8 blocos principais (**`84,0%`**) — têm **`> 130` conjuntos simultaneamente restritos**!<br>• **`REL`, `CNF` e `PAR`:** Nenhum bloco atinge 130 conjuntos simultâneos (`REL` tem pico de `110` sem quarentena, `72` pós-quarentena sem `corte > 0` e `63` com `corte > 0`; `CNF` tem pico de `43` sem quarentena e `39` com quarentena; `PAR` tem `0`). | Com `corte_mw > 0`, `> 130 conjuntos` era uma métrica de **pico do bloco (`ativos_max`)** (ocorrendo em `29,9%` dos patamares `ENE`). Pela ocorrência declarada sem quarentena e sem `corte_mw > 0`, **`> 130 conjuntos simultâneos` torna-se o regime típico de quase todos os patamares `ENE` (`82,9%` dos patamares, mediana de `149,5` conjuntos)**, chegando a `156` de `156` conjuntos simultâneos. |
| **3. *"95,4% da energia cortada por essa razão está em episódios de 4 horas ou mais; pulsos de 30 minutos somam 0,2%"*** | Reproduz exato na Base 3 (`ENE`, com quarentena e `corte_mw > 0`): episódios $\ge 4\text{ h}$ concentram **`95,4%` da energia** (`42,7%` em `4h–7h30` + `52,7%` em `8h–23h30`), mas representam apenas `44,4%` do número de episódios (`983` de `2.213`), enquanto os pulsos de 30 min são `492` episódios (`22,2%` dos episódios, **`0,20%` da energia**). | • **Com quarentena, sem `corte_mw > 0` (`ENE`):** Episódios $\ge 4\text{ h}$ são `45,3%` dos episódios (`995` de `2.198`), `81,9%` das ocorrências e **`95,5%` da energia**; pulsos de 30 min são `478` episódios (`21,7%` dos episódios, **`0,19%` da energia**).<br>• **Sem quarentena, sem `corte_mw > 0` (`ENE`):** Episódios $\ge 4\text{ h}$ sobem para **`96,1%` dos episódios (`1.216` de `1.266`)**, **`99,3%` das ocorrências (`22.434` de `22.583`)** e **`99,8%` da energia positiva**; pulsos de 30 min caem para **`1` único episódio (`0,08%` dos episódios, `0,004%` das ocorrências, `0,00%` da energia)**! | A conclusão qualitativa do `README.md` (predominância absoluta de janelas longas sobre pulsos de 30 min em `ENE`) fica **ainda mais forte** sem quarentena e sem `corte_mw > 0`: a concentração em episódios $\ge 4\text{ h}$ sobe de `95,4%` para **`99,8%` da energia** (e de `44,4%` para **`96,1%` dos episódios**), demonstrando que quase todos os pulsos de 30 min eram artefatos de quebra pela quarentena. |

---

## 4. Reprodutibilidade

Todo o processamento numérico desta análise está implementado de forma determinística em [`analises/gate31a_razao_01.py`](../../analises/gate31a_razao_01.py) e pode ser reproduzido com:

```bash
.venv/bin/python analises/gate31a_razao_01.py
```
