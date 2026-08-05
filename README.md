# 🔁 Banco de Dados de Trocas — ETL + Qualidade de Dados

Banco de dados **MySQL** para controle de **trocas/devoluções a fornecedores**, com carga via **Python/SQLAlchemy**,
**chaves idempotentes por hash** e uma suíte de **scripts de qualidade de dados** (normalização, deduplicação e constraints).

> ⚠️ **Aviso sobre os dados**
> Todos os dados presentes neste repositório (planilhas, seeds, exemplos) são **fictícios** e foram
> **gerados aleatoriamente apenas para demonstração**. Os dados reais da operação em que o projeto
> foi utilizado são **confidenciais e estão protegidos** — nenhum dado real, credencial ou informação
> de terceiros foi incluído aqui.

## 🎯 Destaques de engenharia
- **Modelo dimensional**: `dim_lojas`, `dim_fornecedor` e `fato_trocas` (veja `sql/schema.sql`).
- **Idempotência**: cada registro recebe um `hash_chave` (via `hashlib`) — reexecutar a carga **não** duplica dados.
- **Qualidade de dados**:
  - `normalizar_banco.py` — padroniza nomes para *title-case*.
  - `corrigir_banco.py` — corrige duplicatas e adiciona **UNIQUE constraints**.
  - `fix_duplicatas.py` — deduplicação adicional.
- **ETL**: `fluxo_trocas.py` carrega e concilia os dados; `analise_trocas.py` gera as análises.

## 🧑‍💻 Stack
`Python` · `SQLAlchemy` · `MySQL` · `Pandas` · `hashlib` · `Modelagem Dimensional` · `Data Quality` · `SQL`

## ▶️ Como rodar
```bash
pip install pandas sqlalchemy pymysql
mysql -u root -e "CREATE DATABASE trocas CHARACTER SET utf8mb4;"
mysql -u root trocas < sql/schema.sql
mysql -u root trocas < sql/seed_exemplo.sql
python fluxo_trocas.py       # carga (ETL)
python normalizar_banco.py   # qualidade de dados
python corrigir_banco.py     # dedup + constraints
```

---

### 🧰 Competências demonstradas
`Engenharia de Dados` · `Qualidade de Dados` · `Modelagem Dimensional` · `SQL` · `Idempotência (hashing)`

### 👤 Autor
**José Vitor Santos Pinheiro** — Analista de Dados / BI / Ciência de Dados
· vytorsantt@gmail.com
