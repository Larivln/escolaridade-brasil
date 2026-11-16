from pathlib import Path

import pandas as pd

# Caminho para o CSV (relativo à pasta do projeto, funciona em qualquer computador)
caminho = Path(__file__).resolve().parent.parent / "dados" / "pnad_exemplo.csv"

# Lê os dados
df = pd.read_csv(caminho)

# Visualiza os dados
print("Dados carregados:")
print(df)

# Quantidade por escolaridade
print("\nDistribuição por escolaridade:")
print(df['escolaridade'].value_counts())

# Média de idade por cor/raça
print("\nMédia de idade por cor/raça:")
print(df.groupby('cor_raca')['idade'].mean())
