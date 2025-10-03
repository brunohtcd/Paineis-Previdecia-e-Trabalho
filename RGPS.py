# 'dataset' tem os dados de entrada para este script

import pandas as pd
import numpy as np
from datetime import datetime
import locale

    
def formatar_colunas_para_decimal(df, colunas):
    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = (
                pd.to_numeric(df[coluna], errors="coerce")
                .fillna(0.00)
                .astype("float64")
                .round(2)
               )
    return df

def converter_colunas_para_string(df, colunas_para_converter):
    
    # Transformar todas em texto e remover a aspa inicial inserida no Power Query
    
    for col in colunas_para_converter:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lstrip("'")
    
    return df


# 'dataset' é a tabela recebida do Power Query
df = dataset

# Separa de volta cada consulta
df_receita = df[df["Origem"] == "Receita_anual"].drop(columns=["Origem"])
df_despesa = df[df["Origem"] == "Despesa_anual"].drop(columns=["Origem"])
df_pib     = df[df["Origem"] == "PIB_Bacen"].drop(columns=["Origem"])



# Converte colunas para string

colunas_receita = ["ID_ANO","ID_UO","CO_UO","CO_NATUREZA_RECEITA2","CO_FONTE_SOF","ID_GRUPO_FONTE","ID_FONTE_RECURSO","CO_FONTE_RECURSO","ID_ESFERA_ORCAMENTARIA","CO_RESULTADO_PRIMARIO"]
df_receita = converter_colunas_para_string(df_receita, colunas_receita)

colunas_despesa = ["ID_ANO","CO_FONTE_SOF","CO_UO","CO_FUNCAO","CO_SUBFUNCAO","CO_PROGRAMA","CO_ACAO","CO_PO","CO_ESFERA","CO_RESULTADO_PRIMARIO","CO_ELEMENTO_DESPESA","ID_FONTE","CO_FONTE_RECURSO"]
df_despesa = converter_colunas_para_string(df_despesa, colunas_despesa)


# Remove as colunas em que todos os valores são nulos para a receita
df_receita = df_receita.dropna(axis=1, how='all')
# Remove as colunas em que todos os valores são nulos para a despesa
df_despesa = df_despesa.dropna(axis=1, how='all')
# Remove as colunas em que todos os valores são nulos para o pib
df_pib     = df_pib.dropna(axis=1, how='all')

# Colunas numericas do df_receita
colunas_receita = ["VA_PREV_INI_RECEITA_SALDO","VA_PREV_ATU_RECEITA_SALDO","VA_RECEITA_ORC_BRUTA_SALDO","VA_DEDUCOES_RECEITA_SALDO","VA_RECEITA_ORC_LIQ_SALDO"]
df_receita = formatar_colunas_para_decimal(df_receita, colunas_receita)

# Colunas de numericas do df_despesa
colunas_despesa = ["VLR_DOTACAO_INICIAL","VLR_AUTORIZADO","VLR_EMPENHADO","VLR_LIQUIDADO","VLR_PAGO_CONTROLE_EMPENHO","VLR_RP_INSCRITO","VLR_RP_NAO_PROC_CANCELADO","VLR_RP_PROC_CANCELADO","VLR_RP_PAGO",
"VLR_RP_NAO_PROC_A_PAGAR", "VLR_RP_PROC_A_PAGAR","VLR_PAGAMENTOS_TOTAIS"  ]
df_despesa = formatar_colunas_para_decimal(df_despesa, colunas_despesa)

# Colunas numéricas do df_pib
colunas_pib = ["pib"]
df_pib = formatar_colunas_para_decimal(df_pib, colunas_pib)

receita = df_receita
despesa = df_despesa
pib = df_pib

# Obtém o ano corrente
ano_corrente = str(datetime.now().year)

# ----------------------------------
# Processamento de dados anuais do RGPS
# ----------------------------------

# Início do processamento para o RGPS
# Calcula a receita do RGPS, com lógica diferente para ano corrente

receita_rgps_temp = receita[
    receita['CO_UO'].isin(["25917", "33904", "40904", "55902", "93102"])
].copy()

# Cria a função para ser usada no .apply()
 
def calcular_receita_rgps(g):
    if g.name != ano_corrente:
        # Lógica para anos anteriores
        mask = (g['CO_RESULTADO_PRIMARIO'] == "1")
        return g.loc[mask, 'VA_RECEITA_ORC_LIQ_SALDO'].sum(skipna=True)
    else:
        # Lógica para o ano corrente
        mask = (~g['CO_NATUREZA_RECEITA2'].str.startswith("1321")) & (g['CO_FONTE_RECURSO'] != "444")
        return g.loc[mask, 'VA_PREV_ATU_RECEITA_SALDO'].sum(skipna=True)

# Agrupa por ano e aplica a função para calcular a receita do RGPS
rgps = receita_rgps_temp.groupby('ID_ANO').apply(calcular_receita_rgps).reset_index(name='receita')

# --- Processamento das Despesas do RGPS ---

# 1. Filtra as UOs e a ação para evitar processar o DataFrame inteiro
despesa_rgps_temp = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902", "93102"])) &
    (despesa['CO_ACAO'] != "0Z00")
].copy()

# 2. Cria a função auxiliar para ser usada no .apply()
def calcular_despesa_rgps(g):
    if g.name != ano_corrente:
        # Lógica para anos anteriores
        return g['VLR_PAGAMENTOS_TOTAIS'].sum(skipna=True)
    else:
        # Lógica para o ano corrente
        return g['VLR_AUTORIZADO'].sum(skipna=True)

# 3. Agrupa por ano e aplica a função para calcular a despesa do RGPS
despesa_rgps = despesa_rgps_temp.groupby('ID_ANO').apply(calcular_despesa_rgps).reset_index(name='despesa')


rgps = rgps.merge(despesa_rgps, on='ID_ANO', how='left')

# 4. Junta o PIB ao dataframe rgps
rgps = rgps.merge(pib, on='ID_ANO', how='left')

# Preenche PIB do ano corrente com o último valor conhecido
rgps["pib"] = rgps["pib"].fillna(method="ffill")

# 5. Calcula o déficit do RGPS como percentual do PIB
rgps["deficit"] = ((rgps["despesa"] - rgps["receita"]) / rgps["pib"]) * 100


# --- Processamento das Despesas com Benefícios Previdenciários ---

# 1. Filtra as ações relevantes para evitar processar o DataFrame inteiro
beneficios_temp = despesa[
    despesa['CO_ACAO'].isin(["0E81", "0E82", "00SJ"])
].copy()

# 2. Cria a função auxiliar para ser usada no .apply()
def calcular_beneficios(g):
    if g.name != ano_corrente:
        # Lógica para anos anteriores
        return g['VLR_PAGAMENTOS_TOTAIS'].sum(skipna=True)
    else:
        # Lógica para o ano corrente
        return g['VLR_AUTORIZADO'].sum(skipna=True)

# 3. Agrupa por ano e aplica a função para calcular os benefícios
beneficios = beneficios_temp.groupby('ID_ANO').apply(calcular_beneficios).reset_index(name='beneficios')

# 4. Junta o resultado ao DataFrame 'rgps' principal
rgps = rgps.merge(beneficios, on='ID_ANO', how='left')

# --- Processamento das Despesas com Compensação Previdenciária ---

# 1. Filtra a ação relevante
comprev_temp = despesa[despesa['CO_ACAO'] == "009W"].copy()

# 2. Cria a função auxiliar para ser usada no .apply()
def calcular_comprev(g):
    if g.name != ano_corrente:
        # Lógica para anos anteriores
        return g['VLR_PAGAMENTOS_TOTAIS'].sum(skipna=True)
    else:
        # Lógica para o ano corrente
        return g['VLR_AUTORIZADO'].sum(skipna=True)

# 3. Agrupa por ano e aplica a função para calcular a compensação
comprev = comprev_temp.groupby('ID_ANO').apply(calcular_comprev).reset_index(name='comprev')

# 4. Junta o resultado ao DataFrame 'rgps' principal
rgps = rgps.merge(comprev, on='ID_ANO', how='left')

# --- Processamento das Despesas com Sentenças Judiciais ---

# 1. Filtra as UOs e ações relevantes para evitar processar o DataFrame inteiro
sentencas_temp = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902", "93102"])) &
    (despesa['CO_ACAO'].isin(["0005", "00WU", "0482", "0486", "0625"]))
].copy()

# 2. Cria a função auxiliar para ser usada no .apply()
def calcular_sentencas(g):
    if g.name != ano_corrente:
        # Lógica para anos anteriores
        return g['VLR_PAGAMENTOS_TOTAIS'].sum(skipna=True)
    else:
        # Lógica para o ano corrente
        return g['VLR_AUTORIZADO'].sum(skipna=True)

# 3. Agrupa por ano e aplica a função para calcular as sentenças
sentencas = sentencas_temp.groupby('ID_ANO').apply(calcular_sentencas).reset_index(name='sentencas')

# 4. Junta o resultado ao DataFrame 'rgps' principal
rgps = rgps.merge(sentencas, on='ID_ANO', how='left')

# Renomeia as colunas do dataframe final do RGPS
rgps.rename(columns={
    "ID_ANO": "Ano",
    "receita": "Receitas",
    "despesa": "Despesas",
    "deficit": "Déficit (% PIB)",
    "beneficios": "Benefícios previdenciários",
    "comprev": "Compensação Previdenciária",
    "sentencas": "Despesas com Sentenças Judiciais"
}, inplace=True)

# Lista de colunas numéricas que você quer formatar
colunas_para_formatar = ["Receitas", "Despesas", "Déficit (% PIB)", "Benefícios previdenciários", "Compensação Previdenciária","Despesas com Sentenças Judiciais"]


# Itera sobre a lista e converte cada coluna para string, substituindo o ponto pela vírgula
for coluna in colunas_para_formatar:
    if coluna in rgps.columns:
        # Arredonda e converte para string para garantir o formato
        rgps[coluna] = rgps[coluna].round(2).astype(str).str.replace('.', ',')