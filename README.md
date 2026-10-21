# Banco de Dados de Trocas — ETL e Qualidade de Dados

Banco de dados MySQL para controle de trocas e devoluções a fornecedores, com carga via
Python/SQLAlchemy, chaves idempotentes por hash e uma suíte de scripts de qualidade de dados
(normalização, deduplicação e constraints). O projeto demonstra engenharia de dados de ponta a ponta:
da modelagem do banco à garantia de que a base permanece limpa e confiável a cada nova carga.

> **Nota de confidencialidade:** todos os dados presentes neste repositório (planilhas, seeds,
> exemplos) são fictícios, gerados aleatoriamente apenas para demonstração. Os dados reais da operação
> são confidenciais e estão protegidos — nenhum dado real, credencial ou informação de terceiros foi
> incluído aqui.

---

## Visão Geral

Trocas e devoluções a fornecedores movimentam valor e precisam de rastreabilidade. O projeto estrutura
essas ocorrências em um modelo dimensional, carrega os dados de forma idempotente (sem duplicar em
reexecuções) e aplica uma camada de qualidade que padroniza nomes, remove duplicatas e impõe restrições
de unicidade no banco. O foco não é apenas armazenar, é manter o dado confiável.

## Contexto de Negócio

Quando o controle de trocas vive em planilhas, dois problemas aparecem: os dados se duplicam a cada
consolidação e os cadastros divergem (mesma loja ou fornecedor escritos de formas diferentes). Isso
distorce qualquer análise de valor devolvido e de recorrência por fornecedor. Um banco com carga
idempotente e regras de qualidade elimina essa distorção e transforma o controle de trocas em uma fonte
confiável para negociação com fornecedores e prevenção de perdas.

## O Problema que Resolve

- **Duplicação de registros** a cada reexecução/consolidação da base.
- **Cadastros inconsistentes** (nomes de loja e fornecedor sem padrão).
- **Falta de restrições** que impeçam duplicatas na origem.
- **Ausência de um modelo** próprio para analisar trocas por loja e fornecedor.

## Público e Decisões Apoiadas

- **Compras e Fiscal:** acompanham valor de trocas e recorrência por fornecedor.
- **Prevenção de perdas:** identifica padrões críticos de devolução.
- **Gestão:** decide com base em uma base conciliada, não em planilha divergente.

## Impacto e Valor Gerado

- Carga idempotente: reexecutar o ETL não gera registros duplicados.
- Qualidade garantida por normalização, deduplicação e UNIQUE constraints no banco.
- Modelo dimensional pronto para análises de trocas por loja e fornecedor.
- Base confiável para negociar com fornecedores e reduzir perdas.

---

## Arquitetura e Engenharia de Dados

- **Modelo dimensional:** `dim_lojas`, `dim_fornecedor` e `fato_trocas` (definidos em `sql/schema.sql`).
- **Idempotência por hash:** cada registro recebe um `hash_chave` (via `hashlib`); reexecutar a carga
  não duplica dados, pois a chave identifica univocamente a ocorrência.
- **ETL:** `fluxo_trocas.py` carrega e concilia os dados; `analise_trocas.py` gera as análises.
- **Camada de qualidade de dados:**
  - `normalizar_banco.py` — padroniza nomes para title-case.
  - `corrigir_banco.py` — corrige duplicatas e adiciona UNIQUE constraints.
  - `fix_duplicatas.py` — deduplicação adicional.

## Stack

Python - SQLAlchemy - MySQL - Pandas - hashlib - Modelagem Dimensional - Data Quality - SQL.

## Como Rodar

```bash
pip install pandas sqlalchemy pymysql
mysql -u root -e "CREATE DATABASE trocas CHARACTER SET utf8mb4;"
mysql -u root trocas < sql/schema.sql
mysql -u root trocas < sql/seed_exemplo.sql
python fluxo_trocas.py       # carga (ETL)
python normalizar_banco.py   # qualidade de dados
python corrigir_banco.py     # dedup + constraints
```

## Estrutura do Projeto

```text
sql/schema.sql        -> Modelo dimensional (dim_lojas, dim_fornecedor, fato_trocas)
sql/seed_exemplo.sql  -> Dados de exemplo (fictícios)
fluxo_trocas.py       -> ETL: carga e conciliação (chave por hash)
analise_trocas.py     -> Análises sobre a base carregada
normalizar_banco.py   -> Padronização de nomes (title-case)
corrigir_banco.py     -> Correção de duplicatas + UNIQUE constraints
fix_duplicatas.py     -> Deduplicação adicional
```

## Autor

José Vitor Santos Pinheiro — Análise de Dados e Inteligência Comercial (Varejo, Indústria e Distribuição).
Contato: vytorsantt@gmail.com

## 🗺️ Modelo de Dados (DER)

Modelo dimensional de trocas/devoluções (MySQL). Renderizado pelo GitHub via Mermaid. *Dados fictícios de demonstração.*

```mermaid
erDiagram
    dim_lojas ||--o{ fato_trocas : "dimensiona"
    dim_fornecedor ||--o{ fato_trocas : "dimensiona"

    dim_lojas {
        int pk_loja PK
        varchar loja UK
    }
    dim_fornecedor {
        int pk_fornecedor PK
        varchar fornecedor UK
    }
    fato_trocas {
        bigint pk PK
        char hash_chave UK "chave idempotente (hashlib)"
        int fk_loja FK
        int fk_forn FK
        varchar produto
        decimal quantidade
        decimal valor
        date data
    }
```

**Qualidade de dados:** chave por *hash* (`hash_chave`) garante cargas idempotentes e `UNIQUE` impede duplicatas; rotinas de normalização corrigem nomes e inconsistências.
