# Csv Nota Salvador

> Projeto de portfólio de **Victória Pedrosa** (Automação, Processos e Dados). Automação desenvolvida para um escritório de contabilidade; **esta é uma versão com dados fictícios** — nomes, CNPJs, e-mails e IDs internos foram substituídos.

## Problema de negócio
Baixar o CSV de notas de Salvador para cada empresa de saúde exigia acesso individual.

## Antes x depois
| | Antes | Depois |
|---|---|---|
| Como é feito | Download manual no portal. | Robô baixa os CSVs e registra as empresas sem arquivo. |

## Ganho
- Base de notas atualizada em lote.

## Tecnologias
OCR de captcha, Python, SQLite, Selenium, openpyxl, pandas

## Arquivos
- `automacao-csv_salvador.py`
- `requirements.txt`

## Como rodar
1. `pip install -r requirements.txt`
2. Copie `.env.exemplo` para `.env` e preencha os caminhos.
3. Execute o script principal.

## Autora
Victória Pedrosa — Product Owner do Time de IA, automação de processos contábeis e fiscais.
