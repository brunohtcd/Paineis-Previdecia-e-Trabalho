# 'dataset' tem os dados de entrada para este script
# ----------------------------------------------------
# Processamento para o Exercício 2025 - LOA
# ----------------------------------------------------


import pandas as pd
import numpy as np
from datetime import datetime
import locale


# 1. Cria o dicionário de mapeamento reverso (Número -> Nome)
meses_mapa_reverso = {
    1: "JANEIRO", 2: "FEVEREIRO", 3: "MARCO", 4: "ABRIL", 5: "MAIO", 6: "JUNHO",
    7: "JULHO", 8: "AGOSTO", 9: "SETEMBRO", 10: "OUTUBRO", 11: "NOVEMBRO", 12: "DEZEMBRO"
}
    
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
df_receita = df[df["Origem"] == "Receita_mensal"].drop(columns=["Origem"])
df_despesa = df[df["Origem"] == "Despesa_mensal"].drop(columns=["Origem"])




# Converte colunas para string

colunas_receita = ["ID_ANO","ID_MES","ID_UO","CO_UO","CO_NATUREZA_RECEITA2","CO_FONTE_SOF","ID_GRUPO_FONTE","ID_FONTE_RECURSO","CO_FONTE_RECURSO","ID_ESFERA_ORCAMENTARIA","CO_RESULTADO_PRIMARIO"]
df_receita = converter_colunas_para_string(df_receita, colunas_receita)

colunas_despesa = ["ID_ANO","ID_MES","CO_FONTE_SOF","CO_UO","CO_FUNCAO","CO_SUBFUNCAO","CO_PROGRAMA","CO_ACAO","CO_PO","CO_ESFERA","CO_RESULTADO_PRIMARIO","CO_ELEMENTO_DESPESA","ID_FONTE","CO_FONTE_RECURSO"]
df_despesa = converter_colunas_para_string(df_despesa, colunas_despesa)


# Remove as colunas em que todos os valores são nulos para a receita
df_receita = df_receita.dropna(axis=1, how='all')
# Remove as colunas em que todos os valores são nulos para a despesa
df_despesa = df_despesa.dropna(axis=1, how='all')


# Colunas numericas do df_receita
colunas_receita = ["VA_PREV_INI_RECEITA_MOV_LIQ_ACUMULADO","VA_PREV_ATU_RECEITA_MOV_LIQ_ACUMULADO","VA_RECEITA_ORC_BRUTA_MOV_LIQ_ACUMULADO","VA_DEDUCOES_RECEITA_MOV_LIQ_ACUMULADO","VA_RECEITA_ORC_LIQ_MOV_LIQ_ACUMULADO"]
df_receita = formatar_colunas_para_decimal(df_receita, colunas_receita)

# Colunas de numericas do df_despesa
colunas_despesa = ["VLR_DOTACAO_INICIAL_ACUMULADO","VLR_AUTORIZADO_ACUMULADO","VLR_EMPENHADO_ACUMULADO","VLR_LIQUIDADO_ACUMULADO","VLR_PAGO_CONTROLE_EMPENHO_ACUMULADO","VLR_RP_INSCRITO_ACUMULADO","VLR_RP_NAO_PROC_CANCELADO_ACUMULADO","VLR_RP_PROC_CANCELADO_ACUMULADO","VLR_RP_PAGO_ACUMULADO",
"VLR_RP_NAO_PROC_A_PAGAR_ACUMULADO", "VLR_RP_PROC_A_PAGAR_ACUMULADO","VLR_PAGAMENTOS_TOTAIS_ACUMULADO"  ]
df_despesa = formatar_colunas_para_decimal(df_despesa, colunas_despesa)



receita = df_receita
despesa = df_despesa


# Obtém o ano corrente
ano_corrente = str(datetime.now().year)



# --- Processamento de dados mensais do RGPS (LOA) ---

# Calcula a previsão inicial da receita do RGPS por mês
rgps_loa = receita[
    (receita['CO_UO'] == "33904") &
    (~receita['CO_FONTE_RECURSO'].isin(["000", "444"]))
].copy() # Usa .copy() para evitar warnings de SettingWithCopyWarning

rgps_loa = rgps_loa.groupby('ID_MES').agg(
    prv_inicial=('VA_PREV_INI_RECEITA_MOV_LIQ_ACUMULADO', 'sum')
).reset_index()

# Junta a previsão atual da receita do RGPS por mês
prv_atual_receita = receita[
    (receita['CO_UO'] == "33904") &
    (~receita['CO_FONTE_RECURSO'].isin(["000", "444"]))
].groupby('ID_MES').agg(
    prv_atual=('VA_PREV_ATU_RECEITA_MOV_LIQ_ACUMULADO', 'sum')
).reset_index()

rgps_loa = pd.merge(rgps_loa, prv_atual_receita[['ID_MES', 'prv_atual']], on='ID_MES', how='left')

# Junta a receita realizada líquida por mês
receita_realizada = receita[
    (receita['CO_UO'] == "33904") &
    (receita['CO_RESULTADO_PRIMARIO'] == "1") &
    (~receita['CO_FONTE_RECURSO'].isin(["000", "444"]))
].groupby('ID_MES').agg(
    receita=('VA_RECEITA_ORC_LIQ_MOV_LIQ_ACUMULADO', 'sum')
).reset_index()

rgps_loa = pd.merge(rgps_loa, receita_realizada[['ID_MES', 'receita']], on='ID_MES', how='left')

# Junta os pagamentos totais por mês
pagamentos_totais = despesa[
    (despesa['CO_UO'] == "33904") &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    despesa=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO','sum')
).reset_index()

rgps_loa = pd.merge(rgps_loa, pagamentos_totais[['ID_MES', 'despesa']], on='ID_MES', how='left')

# Calcula o déficit
rgps_loa["deficit"] = rgps_loa["despesa"] - rgps_loa["receita"]

# Junta a dotação inicial por mês
dotacao_inicial = despesa[
    (despesa['CO_UO'] == "33904") &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    lei=('VLR_DOTACAO_INICIAL_ACUMULADO', 'sum')
).reset_index()

rgps_loa = pd.merge(rgps_loa, dotacao_inicial[['ID_MES', 'lei']], on='ID_MES', how='left')

# Filtra e agrega a dotação atual da despesa por mês
autorizado = despesa[
    (despesa['CO_UO'] == "33904") &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    atual=('VLR_AUTORIZADO_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, autorizado[['ID_MES', 'atual']], on='ID_MES', how='left')


# Filtra e agrega os valores liquidados da despesa por mês
liquidado = despesa[
    (despesa['CO_UO'] == "33904") &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    liquidado=('VLR_LIQUIDADO_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, liquidado[['ID_MES', 'liquidado']], on='ID_MES', how='left')


# Filtra e agrega os valores pagos da despesa por mês
pago = despesa[
    (despesa['CO_UO'] == "33904") &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    pago=('VLR_PAGO_CONTROLE_EMPENHO_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, pago[['ID_MES', 'pago']], on='ID_MES', how='left')


# Filtra e agrega os valores de RAP inscrito por UO e mês
rap_insc = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902"])) &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    rap_inscrito=('VLR_RP_INSCRITO_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, rap_insc[['ID_MES', 'rap_inscrito']], on='ID_MES', how='left')

# Filtra e agrega os valores de RAP pago por UO e mês
rap_pago = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902"])) &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    rap_pago=('VLR_RP_PAGO_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, rap_pago[['ID_MES', 'rap_pago']], on='ID_MES', how='left')


# Filtra e agrega os valores de RAP cancelado por UO e mês
rap_cancelado = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902"])) &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    rap_cancelado=('VLR_RP_CANCELADO_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, rap_cancelado[['ID_MES', 'rap_cancelado']], on='ID_MES', how='left')

# Filtra e agrega os valores de RAP a pagar por UO e mês
rap_a_pagar = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902"])) &
    (despesa['CO_RESULTADO_PRIMARIO'] != "0")
].groupby('ID_MES').agg(
    rap_a_pagar=('VLR_RP_A_PAGAR_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, rap_a_pagar[['ID_MES', 'rap_a_pagar']], on='ID_MES', how='left')


# Filtra e agrega os valores de aposentadorias urbanas por mês
# Filtra a despesa por código de ação e código de especificação de despesa
aposentadorias_urbanas = despesa[
    (despesa['CO_ACAO'].isin(["0E81", "00SJ"])) &
    (despesa['CO_ELEMENTO_DESPESA'].isin(["54", "56"]))
].groupby('ID_MES').agg(
    aposentadorias_urbanas=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO', 'sum')
).reset_index()


# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, aposentadorias_urbanas[['ID_MES', 'aposentadorias_urbanas']], on='ID_MES', how='left')



# Filtra e agrega os valores de aposentadorias rurais por mês
# Filtra a despesa por código de ação e código de especificação de despesa
aposentadorias_rurais = despesa[
    (despesa['CO_ACAO'].isin(["0E82", "00SJ"])) &
    (despesa['CO_ELEMENTO_DESPESA'].isin(["53", "55"]))
].groupby('ID_MES').agg(
    aposentadorias_rurais=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, aposentadorias_rurais[['ID_MES', 'aposentadorias_rurais']], on='ID_MES', how='left')



#Filtra, Agrega e Junta Demais Benefícios Urbanos (Acumulados) ---
condicao_urb_demais = (
    (despesa['CO_ACAO'] == "0E81") & 
    (~despesa['CO_ELEMENTO_DESPESA'].isin(["54", "56"]))
) | (
    (despesa['CO_ACAO'] == "00SJ") & 
    (~despesa['CO_ELEMENTO_DESPESA'].isin(["53", "54", "55", "56"])) &
    (despesa['CO_PO'] == "0001")
)

# Filtra e agrega os valores de demais benefícios urbanos por mês
demais_beneficios_urbanos = despesa[condicao_urb_demais].groupby('ID_MES').agg(
    urb_demais=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, demais_beneficios_urbanos[['ID_MES', 'urb_demais']], on='ID_MES', how='left')


# Junta Demais Benefícios Rurais (Acumulados)

# Define as condições de filtro complexas para demais benefícios rurais
condicao_rur_demais = (
    (despesa['CO_ACAO'] == "0E82") &
    (~despesa['CO_ELEMENTO_DESPESA'].isin(["53", "55"]))
) | (
    (despesa['CO_ACAO'] == "00SJ") &
    (~despesa['CO_ELEMENTO_DESPESA'].isin(["53", "54", "55", "56"])) &
    (despesa['CO_PO'] == "0002")
)

# Filtra e agrega os valores de demais benefícios rurais por mês
demais_beneficios_rurais = despesa[condicao_rur_demais].groupby('ID_MES').agg(
    rur_demais=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, demais_beneficios_rurais[['ID_MES', 'rur_demais']], on='ID_MES', how='left')


# Junta a Compensação Previdenciária (Acumulada) 
# Filtra a despesa pelo código de ação 009W (Compensação Previdenciária)
comprev_acum = despesa[
    (despesa['CO_ACAO'] == "009W")
].groupby('ID_MES').agg(
    comprev=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, comprev_acum[['ID_MES', 'comprev']], on='ID_MES', how='left')



# Junta Despesas com Sentenças Judiciais (Acumuladas)
# Define as condições de filtro para UOs e Ações específicas
condicao_sentencas = (
    despesa['CO_UO'].isin(["25917", "33904", "40904", "55902"]) &
    despesa['CO_ACAO'].isin(["0005", "00WU", "0482", "0486", "0625"])
)

# Filtra e agrega os valores das sentenças por mês
sentencas_acum = despesa[condicao_sentencas].groupby('ID_MES').agg(
    sentencas=('VLR_PAGAMENTOS_TOTAIS_ACUMULADO', 'sum')
).reset_index()

# Junta o resultado ao dataframe rgps_loa
rgps_loa = pd.merge(rgps_loa, sentencas_acum[['ID_MES', 'sentencas']], on='ID_MES', how='left')



# --- Ordenação e Criação do Mês Numérico ---

# Converte a coluna 'ID_MES' para inteiro para garantir a ordenação numérica correta
rgps_loa["ID_MES"] = rgps_loa["ID_MES"].astype(int)

# Cria a nova coluna 'MES_NOME' aplicando o mapeamento
rgps_loa['MES_NOME'] = rgps_loa['ID_MES'].map(meses_mapa_reverso)

# Ordena o DataFrame pelo mês e reseta o índice
rgps_loa = rgps_loa.sort_values("ID_MES").reset_index(drop=True)

# --- Cálculo da Variação Mensal (Aposentadorias Urbanas) ---

# Calcula a variação mensal (incremental)
rgps_loa["apmurb"] = rgps_loa["aposentadorias_urbanas"].diff()
# Ajusta a primeira linha, atribuindo o valor total do primeiro mês (conforme lógica R)
rgps_loa.loc[0, "apmurb"] = rgps_loa.loc[0, "aposentadorias_urbanas"]


# --- Cálculo da Variação Mensal (Aposentadorias Rurais) ---

# Calcula a variação mensal (incremental)
rgps_loa['apmrur'] = rgps_loa['aposentadorias_rurais'].diff()
# Ajusta a primeira linha, atribuindo o valor total do primeiro mês (conforme lógica R)
rgps_loa.loc[0, 'apmrur'] = rgps_loa.loc[0, 'aposentadorias_rurais']

# --- Cálculo da Variação Mensal (Demais Benefícios Urbanos) ---

# Cria a coluna 'dmurb' calculando a diferença em relação ao mês anterior (diff)
rgps_loa['dmurb'] = rgps_loa['urb_demais'].diff()

# Ajusta a primeira linha, atribuindo o valor total do primeiro mês (conforme lógica R)
rgps_loa.loc[0, 'dmurb'] = rgps_loa.loc[0, 'urb_demais']

# Calcula a Variação Mensal (Demais Benefícios Rurais)

# Cria a coluna 'dmrur' calculando a diferença em relação ao mês anterior (diff)
rgps_loa['dmrur'] = rgps_loa['rur_demais'].diff()

# Ajusta a primeira linha, atribuindo o valor total do primeiro mês (conforme lógica R)
rgps_loa.loc[0, 'dmrur'] = rgps_loa.loc[0, 'rur_demais']

# Calcula a Variação Mensal Compensação Previdenciária

# Cria a coluna 'comprevm' calculando a diferença em relação ao mês anterior (diff)
rgps_loa['comprevm'] = rgps_loa['comprev'].diff()

# Ajusta a primeira linha, atribuindo o valor total do primeiro mês (conforme lógica R)
rgps_loa.loc[0, 'comprevm'] = rgps_loa.loc[0, 'comprev']


# Calcula a Variação Mensal Despesas com Sentenças Judiciais
# Cria a coluna 'sentencasm' calculando a diferença em relação ao mês anterior (diff)
rgps_loa['sentencasm'] = rgps_loa['sentencas'].diff()

# Ajusta a primeira linha, atribuindo o valor total do primeiro mês (conforme lógica R)
rgps_loa.loc[0, 'sentencasm'] = rgps_loa.loc[0, 'sentencas']


# Cria a nova coluna 'MES_NOME' aplicando o mapeamento
# Assume-se que sua coluna numérica se chama 'ID_MES'
rgps_loa['MES_NOME'] = rgps_loa['ID_MES'].map(meses_mapa_reverso)

# Para ordenação correta em relatórios, converta para tipo Categórico
meses_ordem = list(meses_mapa_reverso.values())
rgps_loa['MES_NOME'] = pd.Categorical(rgps_loa['MES_NOME'], categories=meses_ordem, ordered=True)

# Renomeia as colunas do dataframe final do RGPS (LOA)
# Note: A lista original de colunas do R era muito extensa e incluía campos
# que não foram explicitamente processados no código fornecido. Ajustei para
# renomear as colunas que foram calculadas ou trazidas para o DataFrame.
# Se houver mais colunas a renomear, expanda esta lista.
colunas_renomeadas = {
    "ID_MES": "Mês",
    "prv_inicial": "Previsão Inicial da Receita",
    "prv_atual": "Previsão Atual da Receita",
    "receita": "Receita Realizada Líquida",
    "despesa": "Pagamentos Totais",
    "deficit": "Déficit", 
    "lei": "Dotação Inicial",
    "atual": "Dotação Atual",
    "liquidado": "Liquidado",
    "pago": "Pago",
    "rap_inscrito": "RAP Inscrito",
    "rap_pago": "RAP Pago",
    "rap_cancelado": "RAP Cancelado",
    "rap_a_pagar": "RAP a Pagar",
    "aposentadorias_urbanas":  "Aposentadorias e Pensões - Urbano (acum.)",
    "apmurb" :"Aposentadorias e Pensões - Urbano (mensal)",
    "aposentadorias_rurais" : "Aposentadorias e Pensões - Rural (acum.)",
    "apmrur" : "Aposentadorias e Pensões - Rural (mensal)",
    "urb_demais" : "Demais Benefícios do RGPS - Urbano (acum.)",
    "dmurb": "Demais Benefícios do RGPS - Urbano (mensal)",
    "rur_demais": "Demais Benefícios do RGPS - Rural (acum.)",
    "dmrur": "Demais Benefícios do RGPS - Rural (mensal)",
    "comprev" : "Compensação Previdenciária (acum.)",
    "comprevm" : "Compensação Previdenciária (mensal)",
    "sentencas" : "Despesas com Sentenças Judiciais (acum.)",
    "sentencasm" : "Despesas com Sentenças Judiciais (mensal)"
    # "Aposentadorias e Pensões - Urbano (mensal)", "Aposentadorias e Pensões - Rural (acum.)",
    # "Aposentadorias e Pensões - Rural (mensal)", "Demais Benefícios do RGPS - Urbano (acum.)",
    # "Demais Benefícios do RGPS - Urbano (mensal)", "Demais Benefícios do RGPS - Rural (acum.)",
    # "Demais Benefícios do RGPS - Rural (mensal)", "Compensação Previdenciária (acum.)",
    # "Compensação Previdenciária (mensal)", "Despesas com Sentenças Judiciais (acum.)",
    # "Despesas com Sentenças Judiciais (mensal)", "NumMês"
}
rgps_loa = rgps_loa.rename(columns=colunas_renomeadas)


# Lista de colunas numéricas que você quer formatar
colunas_para_formatar = ["Previsão Inicial da Receita", "Previsão Atual da Receita", "Receita Realizada Líquida", "Pagamentos Totais", "Déficit", "Dotação Inicial","Dotação Atual","Liquidado", "Pago", "RAP Inscrito","RAP Pago","RAP Cancelado",
                         "RAP a Pagar", "Aposentadorias e Pensões - Urbano (acum.)","Aposentadorias e Pensões - Urbano (mensal)","Aposentadorias e Pensões - Rural (acum.)","Aposentadorias e Pensões - Rural (mensal)"]


# Itera sobre a lista e converte cada coluna para string, substituindo o ponto pela vírgula
for coluna in colunas_para_formatar:
    if coluna in rgps_loa.columns:
        # Arredonda e converte para string para garantir o formato
        rgps_loa[coluna] = rgps_loa[coluna].round(2).astype(str).str.replace('.', ',')