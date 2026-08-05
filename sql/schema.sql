-- Banco de Trocas/Devoluções (modelo dimensional)
CREATE TABLE dim_lojas (
  pk_loja INT AUTO_INCREMENT PRIMARY KEY,
  loja    VARCHAR(60) NOT NULL,
  UNIQUE KEY uq_loja (loja)
);
CREATE TABLE dim_fornecedor (
  pk_fornecedor INT AUTO_INCREMENT PRIMARY KEY,
  fornecedor    VARCHAR(120) NOT NULL,
  UNIQUE KEY uq_fornecedor (fornecedor)
);
CREATE TABLE fato_trocas (
  pk          BIGINT AUTO_INCREMENT PRIMARY KEY,
  hash_chave  CHAR(64) NOT NULL,            -- chave idempotente (hashlib)
  fk_loja     INT REFERENCES dim_lojas(pk_loja),
  fk_forn     INT REFERENCES dim_fornecedor(pk_fornecedor),
  produto     VARCHAR(120),
  quantidade  DECIMAL(14,3),
  valor       DECIMAL(14,2),
  data        DATE,
  UNIQUE KEY uq_hash (hash_chave)           -- impede duplicatas
);
