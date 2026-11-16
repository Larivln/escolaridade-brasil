# Análise de Escolaridade no Brasil

Este projeto analisa os níveis de escolaridade da população brasileira com base nos microdados da PNAD Contínua trimestral (IBGE), cruzando com gênero, classe social, cor/raça, faixa etária e UF.

## 1. Limpeza dos dados

```bash
python src/limpar_pnad.py
```

O script lê os arquivos `PNADC_*.zip` baixados do IBGE (procura em `dados/` e em `Downloads`, sem precisar extrair) e grava `dados/escolaridade_powerbi.csv`.

O que ele faz:

- Fica só com as colunas necessárias (o arquivo original tem mais de 400).
- Troca os códigos por texto (ex.: `V2007 = 2` vira `Feminino`, `VD3004 = 7` vira `Superior completo`).
- Calcula a classe social de cada domicílio.
- Resume tudo em uma tabela pequena (cerca de 51 mil linhas), já com o peso amostral aplicado.

### Colunas do CSV

| Coluna | O que é |
|---|---|
| `ano`, `trimestre`, `periodo` | Período da pesquisa (ex.: `2023 T4`) |
| `uf`, `regiao` | Estado e região |
| `genero` | Masculino / Feminino |
| `cor_raca` | Branca, Preta, Parda, Amarela, Indígena |
| `faixa_etaria` (+ `_ordem`) | Faixa de idade |
| `escolaridade` (+ `_ordem`) | Nível mais alto concluído, em 10 níveis (ver abaixo) |
| `etapa_ensino` | Agrupamento: Sem instrução, Educação básica, Ensino superior, Pós-graduação |
| `classe_social` (+ `_ordem`) | Classe pela renda do domicílio (ver abaixo) |
| `populacao` | **Número de pessoas que a linha representa** (use esta para contar) |
| `amostra` | Quantas pessoas foram de fato entrevistadas |
| `soma_anos_estudo`, `populacao_anos_estudo` | Para calcular a média de anos de estudo |
| `soma_renda`, `populacao_com_renda` | Para calcular a renda média do trabalho |

### Níveis de escolaridade

| Ordem | Nível | Etapa |
|---|---|---|
| 1 | Sem instrução | Sem instrução |
| 2 | Fundamental incompleto | Educação básica |
| 3 | Fundamental completo | Educação básica |
| 4 | Médio incompleto | Educação básica |
| 5 | Médio completo | Educação básica |
| 6 | Superior incompleto | Ensino superior |
| 7 | Superior completo (graduação) | Ensino superior |
| 8 | Especialização | Pós-graduação |
| 9 | Mestrado | Pós-graduação |
| 10 | Doutorado | Pós-graduação |

Crianças com menos de 5 anos aparecem como `Não se aplica (menor de 5 anos)`, ordem 0.

**Limitação da pós-graduação:** só conta quem já concluiu o curso e não está estudando no momento. Quem está cursando uma pós (ou parou sem concluir) fica em "Superior completo (graduação)", porque a PNAD não pergunta qual curso essa pessoa concluiu antes. Os números de mestrado e doutorado ficam, portanto, um pouco subestimados. Pós-doutorado não é um nível de ensino e não existe na pesquisa.

### Como a classe social foi definida

A PNAD não tem uma variável de classe social. Foi usada a soma do rendimento habitual do trabalho de todos os moradores do domicílio, em salários mínimos (SM) do ano:

| Classe | Renda do domicílio |
|---|---|
| A | mais de 20 SM |
| B | 10 a 20 SM |
| C | 4 a 10 SM |
| D | 2 a 4 SM |
| E | até 2 SM |
| Sem renda do trabalho | ninguém no domicílio tem renda de trabalho |

**Limitação:** o arquivo trimestral só traz renda do trabalho. Aposentadoria, pensão, aluguel e Bolsa Família não entram, então domicílios de aposentados aparecem como "Sem renda do trabalho". Por isso essa categoria fica separada da classe E.

## 2. Dashboard no Power BI

### Jeito rápido: abrir o projeto pronto

O dashboard já está montado em `powerbi/Escolaridade.pbip` (formato de projeto do Power BI, em texto):

1. Dê dois cliques em `powerbi/Escolaridade.pbip` (abre no Power BI Desktop).
2. Informe onde está a pasta `dados`: **Página Inicial → Transformar dados → Editar parâmetros → PastaDados** (o caminho termina com `\`, ex.: `C:\projetos\escolaridade-brasil\dados\`). Ou rode `python src/gerar_pbip.py` com o Power BI fechado, que já grava a pasta certa.
3. Clique em **Atualizar agora** na faixa amarela para carregar o CSV.
4. Se quiser um arquivo único, use **Arquivo → Salvar como** e escolha `.pbix`.

Ele tem duas páginas:

- **Visão geral:** filtros (período, região, UF, faixa etária, cor/raça), cartões (população, % com superior completo, média de anos de estudo, renda média), etapa de ensino por gênero e por classe, % com superior completo por classe e gênero e por estado.
- **Raça, idade e renda:** escolaridade por cor/raça, anos de estudo por cor/raça e gênero, renda média por escolaridade.

Ele já vem com o período em `2023 T4` (seleção única, para não somar dois trimestres) e a faixa etária em 25 anos ou mais. `% Superior Completo` conta graduação, especialização, mestrado e doutorado (`escolaridade_ordem >= 7`).

A pasta do CSV fica no parâmetro `PastaDados`. Se mudar a pasta de lugar, ou se o CSV ganhar colunas novas, gere o projeto de novo (com o Power BI fechado):

```bash
python src/gerar_pbip.py
```

Para gravar um caminho genérico no lugar do seu (útil antes de publicar), use `python src/gerar_pbip.py --publico`.

### Jeito manual

#### Importar

1. **Obter dados → Texto/CSV** → escolha `dados/escolaridade_powerbi.csv`.
2. Na prévia, confira: Origem do arquivo `65001: Unicode (UTF-8)`, Delimitador `Ponto e vírgula`. Clique em **Carregar**.
3. Na exibição de dados, confira que `populacao`, `soma_anos_estudo`, `soma_renda` etc. estão como **Número decimal**.

#### Ordenar as categorias

Para os gráficos não ficarem em ordem alfabética, selecione a coluna e use **Ferramentas de coluna → Classificar por coluna**:

- `escolaridade` → classificar por `escolaridade_ordem`
- `classe_social` → classificar por `classe_ordem`
- `faixa_etaria` → classificar por `faixa_etaria_ordem`

#### Medidas (Nova medida)

```DAX
População = SUM(escolaridade_powerbi[populacao])

% da População =
DIVIDE([População], CALCULATE([População], ALL(escolaridade_powerbi[escolaridade])))

% Superior Completo =
DIVIDE(
    CALCULATE([População], escolaridade_powerbi[escolaridade_ordem] >= 7),
    [População]
)

% Pós-graduação =
DIVIDE(
    CALCULATE([População], escolaridade_powerbi[escolaridade_ordem] >= 8),
    [População]
)

% Educação Básica Completa =
DIVIDE(
    CALCULATE([População], escolaridade_powerbi[escolaridade_ordem] >= 5),
    [População]
)

Média Anos de Estudo =
DIVIDE(SUM(escolaridade_powerbi[soma_anos_estudo]), SUM(escolaridade_powerbi[populacao_anos_estudo]))

Renda Média do Trabalho =
DIVIDE(SUM(escolaridade_powerbi[soma_renda]), SUM(escolaridade_powerbi[populacao_com_renda]))
```

Formate as medidas de `%` como porcentagem. `% Superior Completo` inclui quem tem pós-graduação.

#### Visuais sugeridos

| Visual | Configuração |
|---|---|
| Segmentações (filtros) | `periodo`, `regiao`, `uf`, `faixa_etaria`, `cor_raca` |
| Cartões | `% Educação Básica Completa`, `% Superior Completo`, `% Pós-graduação`, `Média Anos de Estudo` |
| Barras: todos os níveis | Eixo `escolaridade`, Valores `% da População` |
| Rosca ou barras: visão resumida | Legenda `etapa_ensino`, Valores `População` |
| Barras 100% empilhadas: escolaridade por gênero | Eixo `genero`, Legenda `escolaridade`, Valores `População` |
| Barras 100% empilhadas: escolaridade por classe | Eixo `classe_social`, Legenda `escolaridade`, Valores `População` |
| Colunas agrupadas: superior completo por classe e gênero | Eixo `classe_social`, Legenda `genero`, Valores `% Superior Completo` |
| Mapa ou barras por estado | `uf` com `% Superior Completo` |

**Importante:** deixe a segmentação de `faixa_etaria` marcada em `25 a 39`, `40 a 59` e `60 anos ou mais`. Escolaridade costuma ser analisada para pessoas de 25 anos ou mais, que já tiveram tempo de concluir os estudos; incluir crianças distorce os percentuais.

## Fonte

IBGE, PNAD Contínua trimestral, microdados do 3º trimestre de 2021 e do 4º trimestre de 2023.
