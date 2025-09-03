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



# Converte colunas para string

colunas_receita = ["ID_ANO","ID_UO","CO_UO","CO_NATUREZA_RECEITA2","CO_FONTE_SOF","ID_GRUPO_FONTE","ID_FONTE_RECURSO","CO_FONTE_RECURSO","ID_ESFERA_ORCAMENTARIA","CO_RESULTADO_PRIMARIO"]
df_receita = converter_colunas_para_string(df_receita, colunas_receita)

colunas_despesa = ["ID_ANO","CO_FONTE_SOF","CO_UO","CO_FUNCAO","CO_SUBFUNCAO","CO_PROGRAMA","CO_ACAO","CO_PO","CO_ESFERA","CO_RESULTADO_PRIMARIO","CO_ELEMENTO_DESPESA","ID_FONTE","CO_FONTE_RECURSO"]
df_despesa = converter_colunas_para_string(df_despesa, colunas_despesa)


# Remove as colunas em que todos os valores são nulos para a receita
df_receita = df_receita.dropna(axis=1, how='all')
# Remove as colunas em que todos os valores são nulos para a despesa
df_despesa = df_despesa.dropna(axis=1, how='all')

# Colunas numericas do df_receita
colunas_receita = ["VA_PREV_INI_RECEITA_SALDO","VA_PREV_ATU_RECEITA_SALDO","VA_RECEITA_ORC_BRUTA_SALDO","VA_DEDUCOES_RECEITA_SALDO","VA_RECEITA_ORC_LIQ_SALDO"]
df_receita = formatar_colunas_para_decimal(df_receita, colunas_receita)

# Colunas de numericas do df_despesa
colunas_despesa = ["VLR_DOTACAO_INICIAL","VLR_AUTORIZADO","VLR_EMPENHADO","VLR_LIQUIDADO","VLR_PAGO_CONTROLE_EMPENHO","VLR_RP_INSCRITO","VLR_RP_NAO_PROC_CANCELADO","VLR_RP_PROC_CANCELADO","VLR_RP_PAGO",
"VLR_RP_NAO_PROC_A_PAGAR", "VLR_RP_PROC_A_PAGAR","VLR_PAGAMENTOS_TOTAIS"  ]
df_despesa = formatar_colunas_para_decimal(df_despesa, colunas_despesa)

receita = df_receita
despesa = df_despesa

# Obtém o ano corrente
ano_corrente = datetime.now().year


# ----------------------------------
# Dados anuais - Série histórica
# ----------------------------------

############################ RECEITAS FAT ############################################################


# Filtra as receitas do FAT PIS por fonte de recurso
# Uilizando CO_FONTE_SOF ao invés de CO_FONTE_RECURSO
# De->Para
# 040 -> 0140
# 40 -> 1040
# 041 -> 1041  
fat_pis_temp = receita[receita['CO_FONTE_RECURSO'].isin(["040", "40", "041"])].copy()

# Cria a função auxiliar para ser usada no .apply()
def calcular_fat_pis(g):
    if g.name != ano_corrente:
        # Lógica para anos anteriores
        return g['VA_RECEITA_ORC_LIQ_SALDO'].sum(skipna=True)
    else:
        # Lógica para o ano corrente
        return g['VA_PREV_ATU_RECEITA_SALDO'].sum(skipna=True)

# Agrupa por ano e aplica a função para calcular o PIS/PASEP
fat_pis = fat_pis_temp.groupby('ID_ANO').apply(calcular_fat_pis).reset_index(name='pis')

# O resultado final é o DataFrame com a coluna 'pis'
fat_pis = fat_pis[['ID_ANO', 'pis']]



# ---- Receitas financeiras ----
# Filtra os dados de interesse para evitar processar o DataFrame inteiro
df_filtrado = receita[receita['CO_UO'].isin(["25915", "38901", "40901"])].copy()

# 1. Agrega a receita para anos anteriores ao ano corrente
receita_antigo = df_filtrado[
    (df_filtrado['ID_ANO'] != str(ano_corrente)) & 
    (df_filtrado['CO_RESULTADO_PRIMARIO'] == "0")
].groupby('ID_ANO').agg(
    financeira=('VA_RECEITA_ORC_LIQ_SALDO', 'sum')
).reset_index()

# 2. Agrega a receita para o ano corrente
# Uilizando CO_FONTE_SOF ao invés de CO_FONTE_RECURSO
# De->Para
# 000 -> 1000

receita_corrente = df_filtrado[
    (df_filtrado['ID_ANO'] == str(ano_corrente)) & 
    (df_filtrado['CO_FONTE_RECURSO'] != "000") & 
    (df_filtrado['CO_NATUREZA_RECEITA2'].str.startswith(("1321", "164")))
].groupby('ID_ANO').agg(
    financeira=('VA_PREV_ATU_RECEITA_SALDO', 'sum')
).reset_index()

# 3. Combina os dois DataFrames
fat_financeira = pd.concat([receita_antigo, receita_corrente], ignore_index=True)


#Demais Receitas
# ---- Filtra UOs relevantes ----
demais_receitas_temp = receita[receita['CO_UO'].isin(["25915", "38901", "40901"])].copy()

# ---- Cria a coluna 'demais' conforme condições ----
# Uilizando CO_FONTE_SOF ao invés de CO_FONTE_RECURSO
# De->Para
# 040 -> 0140
# 40 -> 1040
# 041 -> 1041 
# 000 -> 1000 
def calcular_demais(g):
    if g.name != ano_corrente:
        mask = (g['CO_RESULTADO_PRIMARIO'] != "0") & (~g['CO_FONTE_RECURSO'].isin(["040", "40", "041"]))
        return g.loc[mask, 'VA_RECEITA_ORC_LIQ_SALDO'].sum(skipna=True)
    else:
        mask = (~g['CO_FONTE_RECURSO'].isin(["040", "40", "041", "000"])) & \
               (~g['CO_NATUREZA_RECEITA2'].astype(str).str.startswith(("1321", "164")))
        return g.loc[mask, 'VA_PREV_ATU_RECEITA_SALDO'].sum(skipna=True)

# ---- Agrupa por ano e aplica a função ----
demais_receitas = demais_receitas_temp.groupby('ID_ANO').apply(calcular_demais).reset_index(name='demais')


# Junta aportes do Tesouro
# FUNÇÃO: get_valor_coluna
# Esta função aplica a lógica condicional para selecionar a coluna correta
# Uilizando CO_FONTE_SOF ao invés de CO_FONTE_RECURSO
# De->Para
# 000 -> 1000 
def get_valor_coluna(df, coluna_antigo, coluna_novo):
    return np.where(df['ID_ANO'].astype(int) != ano_corrente, df[coluna_antigo], df[coluna_novo])

fter_excluir = set(receita[receita['CO_UO'].isin(["25915", "38901", "40901"]) & (receita['CO_FONTE_RECURSO'] != "000")]['CO_FONTE_RECURSO'].unique())
fter_incluir = set(despesa[despesa['CO_UO'].isin(["25915", "38901", "40901"])]['CO_FONTE_RECURSO'].unique()) - fter_excluir

# Transformar fter_excluir em DataFrame
df_fter_excluir = pd.DataFrame(sorted(fter_excluir), columns=["CO_FONTE_RECURSO"])

# Transformar fter_incluir em DataFrame
df_fter_incluir = pd.DataFrame(sorted(fter_incluir), columns=["CO_FONTE_RECURSO"])

aportes_tesouro_temp = despesa[
    despesa['CO_UO'].isin(["25915", "38901", "40901"]) & despesa['CO_FONTE_RECURSO'].isin(fter_incluir)
].copy()
aportes_tesouro_temp['tesouro'] = get_valor_coluna(aportes_tesouro_temp, 'VLR_PAGAMENTOS_TOTAIS', 'VLR_AUTORIZADO')
aportes_tesouro = aportes_tesouro_temp.groupby('ID_ANO')['tesouro'].sum().reset_index()

# Mescla todos os DataFrames em um único DataFrame
fat = fat_pis.merge(fat_financeira, on='ID_ANO', how='left')
fat = fat.merge(demais_receitas, on='ID_ANO', how='left')
fat = fat.merge(aportes_tesouro, on='ID_ANO', how='left')

# Preenche os valores NaN com 0
fat = fat.fillna(0)

# Calcula a receita total do FAT
fat["receita"] = fat['pis'] + fat['financeira'] + fat['demais'] + fat['tesouro']

############################ FIM RECEITAS FAT ########################################################

############################ DESPESAS FAT ############################################################

# --- Processamento das despesas do RGPS ---

# 1. Filtra as despesas do RGPS por UO e fonte de recurso
# Uilizando CO_FONTE_SOF ao invés de CO_FONTE_RECURSO
# De->Para
# 040 -> 0140
# 40 -> 1040
# 041 -> 1041 

fat_despesa_rgps = despesa[
    (despesa['CO_UO'].isin(["25917", "33904", "40904", "55902", "93102"])) &
    (despesa['CO_FONTE_RECURSO'].isin(["040", "40", "041"]))
].copy()

# 2. Agrega as despesas por ano, separando as colunas de valor
fat_despesa_rgps_agregado = fat_despesa_rgps.groupby('ID_ANO').agg(
    pagto_total=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()

# 3. Aplica a lógica condicional para determinar o valor final da despesa do RGPS
fat_despesa_rgps_agregado['desp_rgps'] = fat_despesa_rgps_agregado.apply(
    lambda x: x['pagto_total'] if x['ID_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_despesa_rgps = fat_despesa_rgps_agregado[['ID_ANO', 'desp_rgps']]

fat = fat.merge(fat_despesa_rgps, on='ID_ANO', how='left')

fat['desp_rgps'] = fat['desp_rgps'].fillna(0)
fat['rec_fat'] = fat['receita'] - fat['desp_rgps']


# Junta as transferências para o BNDES e inicializa o DataFrame final
fat_bndes = despesa[despesa['CO_ACAO'] == "0158"].groupby('ID_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
fat_bndes['bndes'] = fat_bndes.apply(
    lambda x: x['pagamentos_totais'] if x['ID_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_bndes = fat_bndes[['ID_ANO', 'bndes']]
fat = fat.merge(fat_bndes, on='ID_ANO', how='left')


# Junta as despesas com Seguro-Desemprego
fat_sd = despesa[despesa['CO_ACAO'].isin(["00H4", "0583", "0585", "0653"])].groupby('ID_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
fat_sd['sd'] = fat_sd.apply(
    lambda x: x['pagamentos_totais'] if x['ID_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_sd = fat_sd[['ID_ANO', 'sd']]
fat = fat.merge(fat_sd, on='ID_ANO', how='left')


# Junta as despesas com Abono Salarial
fat_abono = despesa[despesa['CO_ACAO'] == "0581"].groupby('ID_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
fat_abono['abono'] = fat_abono.apply(
    lambda x: x['pagamentos_totais'] if x['ID_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_abono = fat_abono[['ID_ANO', 'abono']]
fat = fat.merge(fat_abono, on='ID_ANO', how='left')



# Junta as demais despesas do FAT
fat_outras_desp = despesa[
    despesa['CO_UO'].isin(["25915", "38901", "40901"]) &
    ~despesa['CO_ACAO'].isin(["0158", "00H4", "0581", "0583", "0585", "0653"])
].groupby('ID_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
fat_outras_desp['outras'] = fat_outras_desp.apply(
    lambda x: x['pagamentos_totais'] if x['ID_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_outras_desp = fat_outras_desp[['ID_ANO', 'outras']]
fat = fat.merge(fat_outras_desp, on='ID_ANO', how='left')



# Junta o total de despesas do FAT
fat_total_desp = despesa[despesa['CO_UO'].isin(["25915", "38901", "40901"])].groupby('ID_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
fat_total_desp['despesa'] = fat_total_desp.apply(
    lambda x: x['pagamentos_totais'] if x['ID_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_total_desp = fat_total_desp[['ID_ANO', 'pagamentos_totais']]
fat = fat.merge(fat_total_desp, on='ID_ANO', how='left')


# Calcula os resultados econômico e nominal do FAT
fat["economico"] = fat["rec_fat"] - fat["pagamentos_totais"] + fat["bndes"]
fat["nominal"] = fat["rec_fat"] - fat["pagamentos_totais"]

############################ FIM DESPESAS FAT ############################################################


# Agora, renomeie as colunas de forma segura, pois o número de colunas é previsível
fat.columns = ["Ano", "Receita PIS/PASEP", "Receitas financeiras", "Demais receitas", "Aportes do Tesouro","Receita Total","Despesas com RGPS","Recursos FAT", "Transferência BNDES", "Seguro-desemprego", "Abono salarial", "Outras despesas", "Total de despesas FAT","Resultado econômico","Resultado nominal"]



# ----------------------------------
# Processamento de dados anuais do RGPS
# ----------------------------------

# Início do processamento para o RGPS
# Calcula a receita do RGPS, com lógica diferente para ano corrente

receita_rgps_temp = receita[
    receita['CO_UO'].isin(["25917", "33904", "40904", "55902", "93102"])
].copy()

# Cria a função para ser usada no .apply()
# Uilizando CO_FONTE_SOF ao invés de CO_FONTE_RECURSO
# De->Para
# 444 -> 1444
# 444 -> 9444 (Qual dos dois???)
 
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

# Calcula o déficit do RGPS como percentual do PIB
rgps["deficit"] = ((rgps["despesa"] - rgps["receita"]) / 1) * 100


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
    "receita": "RGPS - Receitas",
    "despesa": "RGPS - Despesas",
    "deficit": "RGPS - Déficit (% PIB)",
    "beneficios": "RGPS - Benefícios previdenciários",
    "comprev": "RGPS - Compensação Previdenciária",
    "sentencas": "RGPS - Despesas com Sentenças Judiciais"
}, inplace=True)

df_resultado = pd.merge(fat, rgps, on='Ano', how='left')


# Lista de colunas numéricas que você quer formatar
colunas_para_formatar = ["Receita PIS/PASEP", "Receitas financeiras", "Demais receitas", "Aportes do Tesouro","Receita Total","Despesas com RGPS","Recursos FAT", "Transferência BNDES", "Seguro-desemprego", "Abono salarial", "Outras despesas", "Total de despesas FAT","Resultado econômico","Resultado nominal", "RGPS - Receitas", "RGPS - Despesas", "RGPS - Déficit (% PIB)", "RGPS - Benefícios previdenciários", "RGPS - Compensação Previdenciária","RGPS - Despesas com Sentenças Judiciais"]


# Itera sobre a lista e converte cada coluna para string, substituindo o ponto pela vírgula
for coluna in colunas_para_formatar:
    if coluna in df_resultado.columns:
        # Arredonda e converte para string para garantir o formato
        df_resultado[coluna] = df_resultado[coluna].round(2).astype(str).str.replace('.', ',')