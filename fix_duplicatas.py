
from sqlalchemy import create_engine, text

motor = create_engine(
    'mysql+pymysql://root:@127.0.0.1/trocas',
    connect_args={'charset': 'utf8mb4'}
)

with motor.connect() as con:
    # --- Lojas duplicadas (case-insensitive)
    query_dup_lojas = text("""
        SELECT LOWER(TRIM(loja)) as loja_norm,
               COUNT(*) as cnt,
               GROUP_CONCAT(pk_loja ORDER BY pk_loja SEPARATOR ',') as pks,
               GROUP_CONCAT(loja ORDER BY pk_loja SEPARATOR ' | ') as nomes
        FROM dim_lojas
        GROUP BY LOWER(TRIM(loja))
        HAVING cnt > 1
    """)
    dup_lojas = con.execute(query_dup_lojas).fetchall()
    print('=== Lojas duplicadas (case-insensitive):')
    for d in dup_lojas:
        print(f'  [{d[0]}] PKs={d[2]} Nomes=[{d[3]}]')
    if not dup_lojas:
        print('  (nenhuma)')

    # --- Compradores duplicados
    query_dup_comp = text("""
        SELECT LOWER(TRIM(comprador)) as norm,
               COUNT(*) as cnt,
               GROUP_CONCAT(pk_comprador ORDER BY pk_comprador SEPARATOR ',') as pks,
               GROUP_CONCAT(comprador ORDER BY pk_comprador SEPARATOR ' | ') as nomes
        FROM dim_comprador
        GROUP BY LOWER(TRIM(comprador))
        HAVING cnt > 1
    """)
    dup_comp = con.execute(query_dup_comp).fetchall()
    print('=== Compradores duplicados (case-insensitive):')
    for d in dup_comp:
        print(f'  [{d[0]}] PKs={d[2]} Nomes=[{d[3]}]')
    if not dup_comp:
        print('  (nenhuma)')

    # --- Mercadologicos duplicados
    query_dup_merc = text("""
        SELECT LOWER(TRIM(mercadologico)) as norm,
               COUNT(*) as cnt,
               GROUP_CONCAT(pk_mercadologico ORDER BY pk_mercadologico SEPARATOR ',') as pks,
               GROUP_CONCAT(mercadologico ORDER BY pk_mercadologico SEPARATOR ' | ') as nomes
        FROM dim_mercadologico
        GROUP BY LOWER(TRIM(mercadologico))
        HAVING cnt > 1
    """)
    dup_merc = con.execute(query_dup_merc).fetchall()
    print('=== Mercadologicos duplicados (case-insensitive):')
    for d in dup_merc:
        print(f'  [{d[0]}] PKs={d[2]} Nomes=[{d[3]}]')
    if not dup_merc:
        print('  (nenhuma)')

    # --- Uso nas tabelas fato
    r2 = con.execute(text('SELECT DISTINCT id_loja FROM fato_mensal ORDER BY id_loja'))
    print('fato_mensal id_loja usados:', [row[0] for row in r2.fetchall()])
    r3 = con.execute(text('SELECT DISTINCT fk_loja FROM fato_movimentacao ORDER BY fk_loja'))
    print('fato_movimentacao fk_loja usados:', [row[0] for row in r3.fetchall()])
