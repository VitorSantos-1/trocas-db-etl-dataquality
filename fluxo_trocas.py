
# ==============================================================================
#### ---  Limitando os threads do OpenBLAS/numpy ANTES de qualquer import --- ####

from sqlalchemy import create_engine, text
import pandas as pd
import hashlib
import sys
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# ==============================================================================
#### --- CONFIGURACOES PARA SE CONECTAR AO BANCO DE DADOS --- ####

# Coloque aqui as suas credenciais
usuario = 'root'
senha = ''
servidor = '127.0.0.1'
banco = 'trocas'

# informamos o nome da planilha principal
planilha_dados = 'extrato_dados.xlsx'
# informamos o nome da planilha de balanço
planilha_balanco = 'balanco.xlsx'

# ===============================================================================
#### --- APLICANDO E TESTANDO SE A CONEXAO COM O BANCO DE DADOS FUNCIONA --- ####

print("Conectando ao banco MySQL...")
# criando a variavel motor é uma variável que vai fazer/receber a conexão com o banco de dados
motor = create_engine(
    # f string serve para concatenar strings
    # Colocamos as variáveis que definimos acima
    # pymysql é um driver que conecta o python com o mysql
    f"mysql+pymysql://{usuario}:{senha}@{servidor}/{banco}",
    # connect_args é um dicionário que passa argumentos para a conexão
    # charset: utf8mb4 serve para conectar com o banco de dados
    connect_args={"charset": "utf8mb4"}
)
# Iniciando a conexão com o banco de dados e verificando se a conexão funciona
# faça o teste de conexão com o banco de dados antes de continuar
try:
    # com(with) o motor.connect(), nos conectamos com o banco de dados e recebemos uma conexao
    # a variável 'conexao' agora é uma conexão válida com o banco de dados
    with motor.connect() as conexao:
        # executamos um comando no banco de dados para verificar se a conexão funciona
        conexao.execute(text("SELECT 1"))
        # se der certo, printamos a mensagem de sucesso
        print("   [OK] Conexao estabelecida!\n")
# se der erro, printamos a mensagem de erro e saimos do programa
except Exception as erro:
    # se der erro, printamos a mensagem de erro
    print(f"   [ERRO] {erro}")
    # sys.exit(1) é para sair do programa
    sys.exit(1)

# ==============================================================================================
#### ---  LEITURA DA ABA 'dados' DO ARQUIVO EXCEL (EXTRATO) - INICIANDO PROCESSO DE ETL --- ####

print(f"Carregando '{planilha_dados}' aba 'dados'...")
# 1. Lemos a primeira aba 'dados' do arquivo excel e guardamos na variavel dados
dados = pd.read_excel(planilha_dados,
                      # aqui passamos o nome da primeira aba 'dados' do arquivo excel
                      sheet_name='dados')
# transformamos as colunas da variavel dados para minusculo e tiramos os espaços
dados.columns = [coluna.lower().strip() for coluna in dados.columns]
# informamos quantas linhas foram carregadas
print(f"   [OK] {len(dados)} linhas.\n")
# coluna_descricao é a coluna que contém a descrição do produto
coluna_descricao = next(
    # aqui passamos o nome da coluna que queremos encontrar
    (coluna for coluna in dados.columns if 'escri' in coluna.lower()), None)
# Determina o mes de referencia (primeiro dia do mes do extrato)
# transformamos a coluna 'data/hora' para datetime
dados['_dt_temp'] = pd.to_datetime(
    # aqui informamos o formato da coluna 'data/hora'
    dados['data/hora'], format='%d/%m/%Y %H:%M:%S',
    # se der erro, transforma para 'coerce'
    errors='coerce')
# pegamos o mes de referencia
mes_referencia = dados['_dt_temp'].dropna().dt.to_period('M').mode()[
    # aqui informamos a posição do mes de referencia
    0].to_timestamp()
# mostra o mes de referencia no formato %B/%Y
print(f"   Mes de referencia: {mes_referencia.strftime('%B/%Y')}\n")

# ==============================================================================
#### --- Sincronizando dim_comprador --- ####

print("Sincronizando dim_comprador...")
# Normaliza nomes: remove espaços e padroniza capitalização (ex: 'BRUNO' e 'bruno' -> 'Bruno')
compradores_planilha = (
    dados['comprador'].dropna().str.strip().str.title().unique()
)
# Busca compradores já existentes no banco (também normalizados)
with motor.connect() as conexao:
    compradores_banco = pd.read_sql(
        "SELECT comprador FROM dim_comprador", con=conexao  # type: ignore
    )['comprador'].str.strip().str.title().tolist()
# Apenas compradores que realmente não existem (comparação case-insensitive via title)
novos_compradores = [
    comprador for comprador in compradores_planilha
    if comprador not in compradores_banco
]
if novos_compradores:
    with motor.begin() as conexao:
        pk_inicio = int(conexao.execute(
            text("SELECT COALESCE(MAX(pk_comprador),0) FROM dim_comprador")
        ).scalar() or 0) + 1
        for i, nome_comprador in enumerate(novos_compradores):
            # INSERT IGNORE garante que, mesmo em execução concorrente, não duplica
            conexao.execute(text(
                "INSERT IGNORE INTO dim_comprador (pk_comprador, comprador) VALUES (:pk, :nome)"
            ), {'pk': pk_inicio + i, 'nome': nome_comprador})
    print(f"   [OK] {len(novos_compradores)} novo(s): {novos_compradores}")
else:
    print("   [OK] Ja atualizado.")
with motor.connect() as conexao:
    tabela_compradores = pd.read_sql(
        "SELECT pk_comprador, comprador FROM dim_comprador", con=conexao  # type: ignore
    )
mapa_compradores = dict(
    zip(tabela_compradores['comprador'], tabela_compradores['pk_comprador'])
)
print(f"   Compradores: {mapa_compradores}\n")

# ==============================================================================
#### --- Sincronizando dim_mercadologico --- ####

print("Sincronizando dim_mercadologico...")
# Normaliza: strip + title para evitar duplicatas por case (ex: 'bebidas' vs 'Bebidas')
ref_mercadologico = (
    dados[['mercadologico', 'comprador']]
    .dropna(subset=['mercadologico'])
    .drop_duplicates(subset=['mercadologico'])
    .copy()
)
ref_mercadologico['mercadologico'] = ref_mercadologico['mercadologico'].str.strip(
).str.title()
ref_mercadologico['comprador'] = (
    ref_mercadologico['comprador'].fillna(
        'Nao Definido').str.strip().str.title()
)
# Busca mercadológicos existentes no banco (normalizados para comparação)
with motor.connect() as conexao:
    mercadologicos_banco = pd.read_sql(
        "SELECT mercadologico FROM dim_mercadologico", con=conexao  # type: ignore
    )['mercadologico'].str.strip().str.title().tolist()
    mercadologicos_novos = ref_mercadologico[
        ~ref_mercadologico['mercadologico'].isin(mercadologicos_banco)
    ].copy()

if not mercadologicos_novos.empty:
    with motor.begin() as conexao:
        pk_inicio = int(conexao.execute(text(
            "SELECT COALESCE(MAX(pk_mercadologico),0) FROM dim_mercadologico"
        )).scalar() or 0) + 1
        mercadologicos_novos = mercadologicos_novos.reset_index(drop=True)
        mercadologicos_novos['pk_mercadologico'] = range(
            pk_inicio, pk_inicio + len(mercadologicos_novos)
        )
        mercadologicos_novos['fk_comprador'] = mercadologicos_novos['comprador'].map(
            mapa_compradores
        )
        for _, row in mercadologicos_novos.iterrows():
            # INSERT IGNORE evita duplicata mesmo em execução concorrente
            conexao.execute(text(
                "INSERT IGNORE INTO dim_mercadologico "
                "(pk_mercadologico, mercadologico, fk_comprador) VALUES (:pk, :nome, :fk)"
            ), {
                'pk': int(row['pk_mercadologico']),
                'nome': row['mercadologico'],
                'fk': None if pd.isna(row['fk_comprador']) else int(row['fk_comprador'])
            })
    print(f"   [OK] {len(mercadologicos_novos)} novo(s).")
else:
    print("   [OK] Ja atualizado.")

with motor.connect() as conexao:
    tabela_mercadologico = pd.read_sql(
        "SELECT pk_mercadologico, mercadologico FROM dim_mercadologico", con=conexao  # type: ignore
    )
mapa_mercadologico = dict(zip(
    tabela_mercadologico['mercadologico'], tabela_mercadologico['pk_mercadologico']
))
print(f"   {len(mapa_mercadologico)} mercadologicos no banco.\n")

# ==============================================================================
#### --- Sincronizando dim_lojas --- ####

print("Sincronizando dim_lojas...")

# Normaliza nomes de loja: strip + title (evita 'lj04-loja oeste opcao' vs 'Lj04-Loja Oeste Opcao')
lojas_dos_dados = set(
    dados['loja'].dropna().str.strip().str.title().unique()
)

# Extrai lojas das colunas da aba metas_tendencias e normaliza
cabecalho_metas = pd.read_excel(
    planilha_dados, sheet_name='metas_tendencias', nrows=0
)
lojas_das_metas = set()
for nome_coluna in cabecalho_metas.columns:
    if nome_coluna.lower().startswith('meta_') or nome_coluna.lower().startswith('tendencia_'):
        # Normaliza o nome da loja extraído do cabeçalho
        nome_loja_raw = nome_coluna.split('_', 2)[-1]
        lojas_das_metas.add(nome_loja_raw.strip().title())

todas_lojas = lojas_dos_dados | lojas_das_metas
with motor.connect() as conexao:
    # Busca lojas existentes normalizadas para comparar sem diferenciar case
    lojas_banco = pd.read_sql(
        "SELECT loja FROM dim_lojas", con=conexao  # type: ignore
    )['loja'].str.strip().str.title().tolist()

novas_lojas = [
    nome_loja for nome_loja in todas_lojas if nome_loja not in lojas_banco
]

if novas_lojas:
    with motor.begin() as conexao:
        pk_inicio = int(conexao.execute(
            text("SELECT COALESCE(MAX(pk_loja),0) FROM dim_lojas")
        ).scalar() or 0) + 1
        for i, nome_loja in enumerate(novas_lojas):
            # INSERT IGNORE protege contra corrida concorrente ou re-execução
            conexao.execute(text(
                "INSERT IGNORE INTO dim_lojas (pk_loja, loja) VALUES (:pk, :nome)"
            ), {'pk': pk_inicio + i, 'nome': nome_loja})
    print(f"   [OK] {len(novas_lojas)} nova(s): {novas_lojas}")
else:
    print("   [OK] Ja atualizado.")

with motor.connect() as conexao:
    tabela_lojas = pd.read_sql(
        "SELECT pk_loja, loja FROM dim_lojas", con=conexao  # type: ignore
    )
mapa_lojas = dict(zip(tabela_lojas['loja'], tabela_lojas['pk_loja']))
print(f"   Lojas: {mapa_lojas}\n")

# ==============================================================================
#### --- Sincronizando dim_produtos --- ####

print("Sincronizando dim_produtos...")

colunas_produto = ['produto', 'mercadologico'] + \
    ([coluna_descricao] if coluna_descricao else [])
ref_produtos = (
    dados[colunas_produto]
    .dropna(subset=['produto'])
    .drop_duplicates(subset=['produto'])
    .copy()
)
ref_produtos['produto'] = pd.to_numeric(
    ref_produtos['produto'], errors='coerce')
ref_produtos = ref_produtos.dropna(subset=['produto'])
ref_produtos['produto'] = ref_produtos['produto'].astype(int)
# Usa .title() para casar com os nomes normalizados no mapa
ref_produtos['fk_mercadologico'] = ref_produtos['mercadologico'].str.strip().str.title().map(
    mapa_mercadologico)

produtos_inserir = ref_produtos[['produto', 'fk_mercadologico']].rename(
    columns={'produto': 'pk_produto'})
if coluna_descricao:
    produtos_inserir.insert(
        1, 'produto', ref_produtos[coluna_descricao].str.strip().tolist())

with motor.connect() as conexao:
    pks_banco = pd.read_sql("SELECT pk_produto FROM dim_produtos", con=conexao)[  # type: ignore
        'pk_produto'].tolist()
produtos_novos = produtos_inserir[~produtos_inserir['pk_produto'].isin(
    pks_banco)]

if not produtos_novos.empty:
    with motor.begin() as conexao:
        produtos_novos.to_sql('dim_produtos', con=conexao,  # type: ignore
                              if_exists='append', index=False)
    print(f"   [OK] {len(produtos_novos)} produto(s) inserido(s).")
else:
    print("   [OK] Ja atualizado.")
print()

# ==============================================================================
#### --- Sincronizando fato_mensal --- ####

print("Carregando 'metas e tendencias' -> fato_mensal...")

tabela_metas = pd.read_excel(planilha_dados, sheet_name='metas_tendencias')
tabela_metas.columns = [nome_coluna.strip()
                        for nome_coluna in tabela_metas.columns]

linhas_mensal = []
for indice, linha_meta in tabela_metas.iterrows():
    # Normaliza para casar com os nomes no mapa_mercadologico
    nome_mercadologico = str(linha_meta['mercadologicos']).strip().title()
    fk_mercadologico = mapa_mercadologico.get(nome_mercadologico)

    for nome_loja in lojas_das_metas:
        coluna_meta = f"meta_{nome_loja}"
        coluna_tendencia = f"tendencia_venda_{nome_loja}"
        fk_loja = mapa_lojas.get(nome_loja)

        valor_meta = linha_meta.get(coluna_meta, None)
        valor_tendencia = linha_meta.get(coluna_tendencia, None)
        valor_meta = None if pd.isna(valor_meta) else float(valor_meta)
        valor_tendencia = None if pd.isna(
            valor_tendencia) else float(valor_tendencia)

        if fk_mercadologico is None or fk_loja is None:
            continue

        comprador_do_merc = ref_mercadologico[ref_mercadologico['mercadologico']
                                              == nome_mercadologico]['comprador'].values
        fk_comprador = mapa_compradores.get(
            comprador_do_merc[0]) if len(comprador_do_merc) else None

        linhas_mensal.append({
            '_data': mes_referencia.date(),
            'id_loja': fk_loja,
            'fk_comprador': fk_comprador,
            'fk_mercadologico': fk_mercadologico,
            'meta_faturamento': valor_meta,
            'tendencia_vendas': valor_tendencia,
        })

mensal = pd.DataFrame(linhas_mensal)
print(f"   {len(mensal)} combinacoes mercadologico x loja geradas.")

with motor.begin() as conexao:
    inseridos = 0
    atualizados = 0
    for indice, registro in mensal.iterrows():
        registro_existe = conexao.execute(text("""
            SELECT pk_meta FROM fato_mensal
            WHERE fk_mercadologico = :mercadologico AND id_loja = :loja AND _data = :data
        """), {
            'mercadologico': registro['fk_mercadologico'],
            'loja': registro['id_loja'],
            'data': registro['_data']
        }).fetchone()

        if registro_existe:
            conexao.execute(text("""
                UPDATE fato_mensal
                SET meta_faturamento = :meta, tendencia_vendas = :tendencia, fk_comprador = :comprador
                WHERE pk_meta = :pk
            """), {
                'meta': registro['meta_faturamento'],
                'tendencia': registro['tendencia_vendas'],
                'comprador': registro['fk_comprador'],
                'pk': registro_existe[0]
            })
            atualizados += 1
        else:
            conexao.execute(text("""
                INSERT INTO fato_mensal (_data, id_loja, fk_comprador, fk_mercadologico,
                                         meta_faturamento, tendencia_vendas)
                VALUES (:data, :loja, :comprador, :mercadologico, :meta, :tendencia)
            """), {
                'data': registro['_data'],
                'loja': registro['id_loja'],
                'comprador': registro['fk_comprador'],
                'mercadologico': registro['fk_mercadologico'],
                'meta': registro['meta_faturamento'],
                'tendencia': registro['tendencia_vendas']
            })
            inseridos += 1

print(
    f"   [OK] {inseridos} inserido(s), {atualizados} atualizado(s) em fato_mensal.\n")

# ==============================================================================
#### --- Sincronizando fato_movimentacao --- ####

print("Carregando arquivos de movimentacao...")
planilhas = []

# Extrato
try:
    extrato = pd.read_excel(planilha_dados, sheet_name='dados')
    extrato.columns = [nome_coluna.lower().strip()
                       for nome_coluna in extrato.columns]
    extrato['_fonte'] = 'Extrato Diario'
    planilhas.append(extrato)
    print(f"   [OK] Extrato Diario: {len(extrato)} linhas")
except Exception as erro:
    print(f"   [ERRO] Extrato: {erro}")

# Balanco
if os.path.exists(planilha_balanco):
    try:
        balanco = pd.read_excel(planilha_balanco, sheet_name=0)
        balanco.columns = [nome_coluna.lower().strip()
                           for nome_coluna in balanco.columns]
        balanco['_fonte'] = 'Balanco Fisico Mensal'
        planilhas.append(balanco)
        print(f"   [OK] Balanco Fisico Mensal: {len(balanco)} linhas")
    except Exception as erro:
        print(f"   [ERRO] Balanco: {erro}")
else:
    print(f"   [AVISO] '{planilha_balanco}' nao encontrado, pulando.")

if not planilhas:
    print("[ERRO] Nenhum dado de movimentacao carregado.")
    sys.exit(1)

bruto = pd.concat(planilhas, ignore_index=True)
print(f"   Total unificado: {len(bruto)} linhas\n")

# ==============================================================================
#### --- Normalizando colunas --- ####

print("Normalizando colunas de fato_movimentacao...")

renomear = {
    'produto': 'fk_produto',
    'data/hora': '_data',
    'est. anterior': 'estoque_anterior',
    'qtd. entrada': 'quantidade_entrada',
    'est. atual': 'estoque_atual',
    'custo c/ imposto': 'custo_unitario',
    'total custo': 'custo_total',
    'motivo': 'motivo',
}
for nome_coluna in bruto.columns:
    if 'qtd' in nome_coluna and 'sa' in nome_coluna:
        renomear[nome_coluna] = 'quantidade_saida'
        break

tabela = bruto.rename(columns=renomear)

# Produto
tabela['fk_produto'] = pd.to_numeric(tabela['fk_produto'], errors='coerce')
total_antes = len(tabela)
tabela = tabela.dropna(subset=['fk_produto'])
tabela['fk_produto'] = tabela['fk_produto'].astype(int)
if len(tabela) < total_antes:
    print(
        f"   [AVISO] {total_antes - len(tabela)} linha(s) sem produto descartadas.")

# Loja
# Normaliza nome da loja para casar com os nomes normalizados no mapa_lojas
tabela['fk_loja'] = tabela['loja'].str.strip().str.title().map(mapa_lojas)
tabela = tabela.dropna(subset=['fk_loja'])
tabela['fk_loja'] = tabela['fk_loja'].astype(int)

# Motivo do balanco
mascara_balanco = (tabela['_fonte'] == 'Balanco Fisico Mensal') & (
    tabela['motivo'].isna() | (tabela['motivo'].astype(str).str.strip() == ''))
tabela.loc[mascara_balanco, 'motivo'] = 'Balanco Fisico Mensal'
tabela['motivo'] = tabela['motivo'].fillna('Ajuste').str[:100]

# Data
tabela['_data'] = pd.to_datetime(
    tabela['_data'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
tabela = tabela.dropna(subset=['_data'])

print(f"   [OK] Linhas prontas:")
for origem in tabela['_fonte'].unique():
    print(f"        {origem}: {(tabela['_fonte'] == origem).sum()}")

# ==============================================================================
#### --- Gerando hashes e inserindo em fato_movimentacao --- ####

print("Gerando hashes e inserindo...")


def gerar_hash(linha):
    texto = (f"{linha['fk_produto']}-{linha['_data']}-{linha['fk_loja']}-"
             f"{linha['quantidade_entrada']}-{linha['quantidade_saida']}-{linha['_fonte']}")
    return hashlib.md5(texto.encode()).hexdigest()


tabela['pk_transacao_hash'] = tabela.apply(gerar_hash, axis=1)

colunas_finais = ['pk_transacao_hash', '_data', 'fk_produto', 'fk_loja',
                  'estoque_anterior', 'quantidade_entrada', 'quantidade_saida',
                  'estoque_atual', 'custo_unitario', 'custo_total', 'motivo']

colunas_faltando = [
    nome_coluna for nome_coluna in colunas_finais if nome_coluna not in tabela.columns]
if colunas_faltando:
    print(f"   [ERRO] Colunas ausentes: {colunas_faltando}")
    sys.exit(1)

registros_finais = tabela[colunas_finais]
with motor.connect() as conexao:
    hashes_no_banco = set(pd.read_sql(
        # type: ignore
        "SELECT pk_transacao_hash FROM fato_movimentacao", con=conexao)['pk_transacao_hash'])
registros_novos = registros_finais[~registros_finais['pk_transacao_hash'].isin(
    hashes_no_banco)]

if registros_novos.empty:
    print("   [OK] Nenhuma duplicata. Banco ja atualizado.")
else:
    with motor.begin() as conexao:
        registros_novos.to_sql('fato_movimentacao', con=conexao, if_exists='append',  # type: ignore
                               index=False, method='multi', chunksize=500)
    print(f"   [OK] {len(registros_novos)} linha(s) inserida(s).")

# ==============================================================================
#### --- Relatório final --- ####

print("=" * 55)
print("RELATORIO FINAL")
print("=" * 55)
with motor.connect() as conexao:
    for nome_tabela in ['dim_comprador', 'dim_mercadologico', 'dim_lojas',
                        'dim_produtos', 'fato_mensal', 'fato_movimentacao']:
        total = conexao.execute(
            text(f"SELECT COUNT(*) FROM {nome_tabela}")).scalar()
        print(f"  {nome_tabela:<25}: {total:>6} registros")
print("=" * 55)
print("[FIM] Concluido com sucesso!")
