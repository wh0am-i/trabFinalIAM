# Desafio final IAM

Primeira etapa: obter e visualizar os dados. Estrutura de dados compatível com a futura organização Kedro. Ainda não há pipeline de modelagem.

## Fontes oficiais

- [Occupancy Detection — UCI 357](https://archive.ics.uci.edu/dataset/357/occupancy+detection), Candanedo (2016), DOI 10.24432/C5X01N, CC BY 4.0.
- [Combined Cycle Power Plant — UCI 294](https://archive.ics.uci.edu/dataset/294/combined+cycle+power+plant), Tüfekci e Kaya (2014), DOI 10.24432/C5002N, CC BY 4.0.

Occupancy possui 8.143 registros de treino e dois arquivos de teste, totalizando 20.560 registros. A data e o identificador não são sensores. Preservamos os arquivos separados; a visualização usa somente o treino original.

CCPP possui 9.568 registros e cinco abas com diferentes embaralhamentos das mesmas observações. Usamos somente a primeira aba, sem concatenar. A inspeção global é descritiva; a EDA que orientar decisões de modelagem deverá usar o treino após a divisão.

## Baixar e visualizar

Execute em um terminal com acesso à internet:

```bash
cd ~/meus_projetos_IA/desafio_final_iam
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-visualizacao.txt
.venv/bin/python scripts/visualizar_dados.py
xdg-open reports/primeira_visualizacao.html
```

O relatório inclui primeiras linhas, tipos, valores ausentes, duplicatas, estatísticas, histogramas, correlações e dispersões. Os CSVs ficam em `data/02_intermediate/`. Os ZIPs oficiais e seus arquivos extraídos ficam em `data/01_raw/`, com URLs e hashes SHA-256 em `fontes.json` após o download.

Caso prefira baixar pelo navegador, use os botões Download nas páginas oficiais e coloque os ZIPs em:

- `data/01_raw/occupancy/occupancy_detection.zip`
- `data/01_raw/ccpp/combined_cycle_power_plant.zip`

Depois execute o mesmo script: ele reutiliza os ZIPs existentes.

## Dashboard local

Abra `reports/dashboard.html` no navegador. A interface funciona sem servidor e sem internet; inclui os dados reais dos quatro arquivos, `head()`, `describe()`, tipos, mínimos, máximos, NaN, desvio padrão, variância, covariância, correlação, tabela com busca/ordenação/paginação, exportação CSV e gráficos interativos. Os filtros afetam a tabela e a exportação; as estatísticas e os gráficos usam o arquivo inteiro selecionado.

Para regenerar no ambiente principal existente:

```bash
../.venv/bin/python scripts/visualizar_dados.py --sem-download
../.venv/bin/python scripts/gerar_dashboard.py
xdg-open reports/dashboard.html
```

Os downloads estão completos, com hashes SHA-256 conferidos. O CCPP foi convertido da primeira aba para CSV usando a instalação de `openpyxl` disponível em `~/projetos_ssd/venvs/projeto_gerador_documento_venv`; esse CSV permite usar a visualização no ambiente principal mesmo sem `openpyxl`. Para ler novamente a planilha diretamente, instale `requirements-visualizacao.txt` no ambiente escolhido.

Não há valores ausentes nos quatro arquivos. O CCPP contém 41 linhas duplicadas completas, preservadas nesta etapa. Antes da divisão de treino/teste, definir como evitar que duplicatas atravessem os conjuntos. Occupancy mantém as datas para analisarmos a dependência temporal.
