"""
Script para CORRIGIR duplicatas no banco e adicionar UNIQUE CONSTRAINTS.
Executa uma única vez. Seguro de re-executar.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

from sqlalchemy import create_engine, text

motor = create_engine(
    'mysql+pymysql://root:@127.0.0.1/trocas',
    connect_args={'charset': 'utf8mb4'}
)

print("=" * 60)
print("PASSO 1: Corrigindo duplicata em dim_lojas")
print("=" * 60)

# pk=2 'Lj04-Loja Oeste opcao'  <- vamos manter este (menor pk)
# pk=4 'Lj04-Loja Oeste Opcao'  <- este será removido
# fato_mensal usa pk=2, fato_movimentacao usa pk=4 -> atualizar fato_movimentacao para pk=2

with motor.begin() as con:
    # 1. Encontrar todas as duplicatas (case-insensitive) e resolver
    dup_lojas = con.execute(text("""
        SELECT LOWER(TRIM(loja)) as loja_norm,
               GROUP_CONCAT(pk_loja ORDER BY pk_loja SEPARATOR ',') as pks
        FROM dim_lojas
        GROUP BY LOWER(TRIM(loja))
        HAVING COUNT(*) > 1
    """)).fetchall()

    for row in dup_lojas:
        pks = [int(pk) for pk in row[1].split(',')]
        pk_manter = pks[0]   # menor pk é o canônico
        pks_remover = pks[1:]
        print(f"  Loja [{row[0]}]: manter pk={pk_manter}, remover pks={pks_remover}")

        for pk_remover in pks_remover:
            # Atualizar fato_mensal
            r = con.execute(text("""
                UPDATE fato_mensal SET id_loja = :manter
                WHERE id_loja = :remover
            """), {'manter': pk_manter, 'remover': pk_remover})
            print(f"    fato_mensal: {r.rowcount} linha(s) migrada(s) de pk={pk_remover} -> pk={pk_manter}")

            # Atualizar fato_movimentacao
            r = con.execute(text("""
                UPDATE fato_movimentacao SET fk_loja = :manter
                WHERE fk_loja = :remover
            """), {'manter': pk_manter, 'remover': pk_remover})
            print(f"    fato_movimentacao: {r.rowcount} linha(s) migrada(s) de pk={pk_remover} -> pk={pk_manter}")

            # Deletar a loja duplicada
            con.execute(text("DELETE FROM dim_lojas WHERE pk_loja = :pk"), {'pk': pk_remover})
            print(f"    dim_lojas: pk={pk_remover} deletado.")

    print("  [OK] Duplicatas de lojas corrigidas.")

print()
print("=" * 60)
print("PASSO 2: Adicionando UNIQUE CONSTRAINTS")
print("=" * 60)

with motor.begin() as con:
    # Verifica se já existem as constraints antes de adicionar

    # dim_comprador: UNIQUE(comprador)
    existe = con.execute(text("""
        SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = 'trocas' AND TABLE_NAME = 'dim_comprador'
        AND CONSTRAINT_NAME = 'uq_comprador_nome'
    """)).scalar()
    if not existe:
        con.execute(text("ALTER TABLE dim_comprador ADD CONSTRAINT uq_comprador_nome UNIQUE (comprador)"))
        print("  [OK] UNIQUE adicionado em dim_comprador(comprador)")
    else:
        print("  [JA EXISTE] UNIQUE em dim_comprador(comprador)")

    # dim_mercadologico: UNIQUE(mercadologico)
    existe = con.execute(text("""
        SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = 'trocas' AND TABLE_NAME = 'dim_mercadologico'
        AND CONSTRAINT_NAME = 'uq_mercadologico_nome'
    """)).scalar()
    if not existe:
        con.execute(text("ALTER TABLE dim_mercadologico ADD CONSTRAINT uq_mercadologico_nome UNIQUE (mercadologico)"))
        print("  [OK] UNIQUE adicionado em dim_mercadologico(mercadologico)")
    else:
        print("  [JA EXISTE] UNIQUE em dim_mercadologico(mercadologico)")

    # dim_lojas: UNIQUE(loja)
    existe = con.execute(text("""
        SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
        WHERE TABLE_SCHEMA = 'trocas' AND TABLE_NAME = 'dim_lojas'
        AND CONSTRAINT_NAME = 'uq_lojas_nome'
    """)).scalar()
    if not existe:
        con.execute(text("ALTER TABLE dim_lojas ADD CONSTRAINT uq_lojas_nome UNIQUE (loja)"))
        print("  [OK] UNIQUE adicionado em dim_lojas(loja)")
    else:
        print("  [JA EXISTE] UNIQUE em dim_lojas(loja)")

print()
print("=" * 60)
print("PASSO 3: Verificação final")
print("=" * 60)

with motor.connect() as con:
    for tabela in ['dim_comprador', 'dim_mercadologico', 'dim_lojas']:
        total = con.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
        print(f"  {tabela}: {total} registros")

    r = con.execute(text('SELECT pk_loja, loja FROM dim_lojas ORDER BY pk_loja'))
    print("\n  Lojas no banco:")
    for row in r.fetchall():
        print(f"    pk={row[0]}: {row[1]}")

print()
print("[CONCLUIDO] Banco limpo e protegido contra duplicatas!")
