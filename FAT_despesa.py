import pandas as pd
import numpy as np


ano_corrente = "2025"
despesa_df = dataset


# Garante que a coluna COD_ACAO seja do tipo string
despesa_df['COD_ACAO'] = despesa_df['COD_ACAO'].astype(str)
despesa_df['COD_UO'] = despesa_df['COD_UO'].astype(str)


# Junta as transferências para o BNDES e inicializa o DataFrame final
bndes = despesa_df[despesa_df['COD_ACAO'] == "0158"].groupby('NUM_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
bndes['bndes'] = bndes.apply(
    lambda x: x['pagamentos_totais'] if x['NUM_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_p = bndes[['NUM_ANO', 'bndes']]


# Junta as despesas com Seguro-Desemprego
sd = despesa_df[despesa_df['COD_ACAO'].isin(["00H4", "0583", "0585", "0653"])].groupby('NUM_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
sd['sd'] = sd.apply(
    lambda x: x['pagamentos_totais'] if x['NUM_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_p = pd.merge(fat_p, sd[['NUM_ANO', 'sd']], on='NUM_ANO', how='outer')


# Junta as despesas com Abono Salarial
abono = despesa_df[despesa_df['COD_ACAO'] == "0581"].groupby('NUM_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
abono['abono'] = abono.apply(
    lambda x: x['pagamentos_totais'] if x['NUM_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_p = pd.merge(fat_p, abono[['NUM_ANO', 'abono']], on='NUM_ANO', how='outer')


# Junta as demais despesas do FAT
outras_desp = despesa_df[
    despesa_df['COD_UO'].isin(["25915", "38901", "40901"]) &
    ~despesa_df['COD_ACAO'].isin(["0158", "00H4", "0581", "0583", "0585", "0653"])
].groupby('NUM_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
outras_desp['outras'] = outras_desp.apply(
    lambda x: x['pagamentos_totais'] if x['NUM_ANO'] != ano_corrente else x['autorizado'], axis=1
)


fat_p = pd.merge(fat_p, outras_desp[['NUM_ANO', 'outras']], on='NUM_ANO', how='outer')


# Junta o total de despesas do FAT
total_desp = despesa_df[despesa_df['COD_UO'].isin(["25915", "38901", "40901"])].groupby('NUM_ANO').agg(
    pagamentos_totais=('VLR_PAGAMENTOS_TOTAIS', 'sum'),
    autorizado=('VLR_AUTORIZADO', 'sum')
).reset_index()
total_desp['despesa'] = total_desp.apply(
    lambda x: x['pagamentos_totais'] if x['NUM_ANO'] != ano_corrente else x['autorizado'], axis=1
)

fat_p = pd.merge(fat_p, total_desp[['NUM_ANO', 'despesa']], on='NUM_ANO', how='outer')

# Lista de colunas numéricas que você quer formatar
colunas_para_formatar = [
    'bndes', 'sd', 'abono', 'outras', 'despesa', 
    ]

# Itera sobre a lista e converte cada coluna para string, substituindo o ponto pela vírgula
for coluna in colunas_para_formatar:
    if coluna in fat_p.columns:
        # Arredonda e converte para string para garantir o formato
        fat_p[coluna] = fat_p[coluna].round(2).astype(str).str.replace('.', ',')

# Agora, renomeie as colunas de forma segura, pois o número de colunas é previsível
fat_p.columns = ["Ano", "Transferência BNDES", "Seguro-desemprego", "Abono salarial", "Outras despesas", "Total de despesas FAT"]