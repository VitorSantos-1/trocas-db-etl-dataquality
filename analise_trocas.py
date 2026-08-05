import pandas as pd
import plotly.express as px
import numpy as np

df = pd.read_excel(r"C:\Users\Usuário\Documents\minha_pasta\Projetos\projeto_trocas\extrato_dados.xlsx", sheet_name=None)
pd.set_option("display.max_columns", None)

#### DATAS ####
# transformando a coluna "data/hora" para datetime64[ns]
for data in ["data/hora"]:
    if df["dados"][data].dtype != "datetime64[ns]":
        df["dados"][data] = df["dados"][data].astype("datetime64[ns]")
# criando coluna de datas
df["dados"]["ano"] = df["dados"]["data/hora"].dt.year
df["dados"]["mes"] = df["dados"]["data/hora"].dt.month
df["dados"]["dia da semana"] = df["dados"]["data/hora"].dt.day_name()
df["dados"]["ano-mes"] = df["dados"]["ano"].astype(str)+"-"+df["dados"]["mes"].astype(str)
df["dados"]["dia"] = df["dados"]["data/hora"].dt.day
df["dados"]["hora"] = df["dados"]["data/hora"].dt.strftime("%H:%M")

df["dados"].head()
df["dados"].info()
df["dados"].dtypes

#### NUMEROS ####
# lista dos setores que é float
setores_peso = ["Acougue", "Peixaria", "Hortifruti", "PadariaPropria", "PadariaTerceirizada", "FriosLaticinios", "PetShop"]
df_peso = df["dados"][df["dados"]["mercadologico"].isin(setores_peso)].copy()
df_unidade = df["dados"][~df["dados"]["mercadologico"].isin(setores_peso)].copy()

for numero in ["est. anterior", "est. atual", "qtd. entrada", "qtd. saída"]:
    if numero in df_peso.columns:
        df_peso[numero] = pd.to_numeric(df_peso[numero], errors="coerce").fillna(0).astype("float64")
    if numero in df_unidade.columns:
        df_unidade[numero] = pd.to_numeric(df_unidade[numero], errors="coerce").fillna(0).round().astype("int64")
df["dados"].head()

# Testando:
print(df_peso[["est. anterior", "est. atual", "qtd. entrada", "qtd. saída"]].dtypes)
print(df_unidade[["est. anterior", "est. atual", "qtd. entrada", "qtd. saída"]].dtypes)
print(df_peso["mercadologico"].unique())
print(df_unidade["mercadologico"].unique())

# analisando os custos por motivo de troca
motivo_por_custo = df["dados"].groupby("motivo", as_index=False)["total custo"].sum()
# em grafico
figura_1 = px.bar(motivo_por_custo,
             x="motivo",
             y="total custo",
             title="Motivo de trocas",
             text_auto=".2s"
            )
figura_1.update_traces(textposition="outside")
figura_1.show()