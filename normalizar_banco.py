"""
Normaliza os nomes existentes no banco para coincidir com o padrao title-case
que o novo codigo vai usar ao comparar/inserir.
Executa uma unica vez. Seguro de re-executar.
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

print("Normalizando nomes para title-case no banco...\n")

with motor.begin() as con:
    # dim_lojas
    lojas = con.execute(text("SELECT pk_loja, loja FROM dim_lojas")).fetchall()
    for pk, nome in lojas:
        novo_nome = nome.strip().title()
        if novo_nome != nome:
            con.execute(text("UPDATE dim_lojas SET loja = :novo WHERE pk_loja = :pk"),
                        {'novo': novo_nome, 'pk': pk})
            print(f"  dim_lojas pk={pk}: [{nome}] -> [{novo_nome}]")

    # dim_comprador
    compradores = con.execute(text("SELECT pk_comprador, comprador FROM dim_comprador")).fetchall()
    for pk, nome in compradores:
        novo_nome = nome.strip().title()
        if novo_nome != nome:
            con.execute(text("UPDATE dim_comprador SET comprador = :novo WHERE pk_comprador = :pk"),
                        {'novo': novo_nome, 'pk': pk})
            print(f"  dim_comprador pk={pk}: [{nome}] -> [{novo_nome}]")

    # dim_mercadologico
    mercs = con.execute(text("SELECT pk_mercadologico, mercadologico FROM dim_mercadologico")).fetchall()
    for pk, nome in mercs:
        novo_nome = nome.strip().title()
        if novo_nome != nome:
            con.execute(text(
                "UPDATE dim_mercadologico SET mercadologico = :novo WHERE pk_mercadologico = :pk"),
                        {'novo': novo_nome, 'pk': pk})
            print(f"  dim_mercadologico pk={pk}: [{nome}] -> [{novo_nome}]")

print("\nVerificacao final:")
with motor.connect() as con:
    r = con.execute(text("SELECT pk_loja, loja FROM dim_lojas ORDER BY pk_loja"))
    print("  Lojas:")
    for row in r.fetchall():
        print(f"    pk={row[0]}: {row[1]}")
    r = con.execute(text("SELECT pk_comprador, comprador FROM dim_comprador ORDER BY pk_comprador"))
    print("  Compradores:")
    for row in r.fetchall():
        print(f"    pk={row[0]}: {row[1]}")

print("\n[CONCLUIDO] Banco padronizado!")
