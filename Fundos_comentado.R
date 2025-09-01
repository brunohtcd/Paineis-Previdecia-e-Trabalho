library(readxl)
library(dplyr)
library("openxlsx")
library("stringr")

# =======================================================
# Este script realiza a extração, transformação e análise
# de dados orçamentários a partir de planilhas Excel.
# Os dados são divididos em séries históricas anuais e
# dados de execução orçamentária do ano corrente (2025).
# As saídas são salvas em um novo arquivo Excel.
# =======================================================


# ----------------------------------
# Dados anuais - Série histórica
# ----------------------------------

# Carrega os dados de PIB, receita e despesa
pib <- read_excel("H:/Usuários/Túlio/Orçamento/Execução/PIB.xlsx")
# Converte a coluna 'ano' para o tipo caractere
pib$ano <- as.character(pib$ano)
receita <- read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos.xlsx", sheet = 2)
despesa <- read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos.xlsx", sheet = 5)

# ----------------------------------
# Processamento de dados anuais do FAT
# ----------------------------------

# Início do processamento para o FAT (Fundo de Amparo ao Trabalhador)
# Filtra receitas do FAT e calcula a receita de PIS/PASEP
fat <- receita %>%
  filter(fter_cod %in% c("40", "040", "041")) %>%
  group_by(ano) %>%
  summarise(pis = if_else(unique(ano != "2025"), sum(rol, na.rm = TRUE), sum(prev_atual, na.rm = TRUE))) %>%
  as.data.frame()

# Junta as receitas financeiras, filtrando por UO, tipo de recurso e ano
fat <- fat %>%
  left_join(select(receita %>%
    group_by(ano) %>%
    summarise(financeira = case_when(unique(ano != "2025") ~ sum(rol[uo_cod %in% c("25915", "38901", "40901") & rp_cod == "0"], na.rm = TRUE),
                                     unique(ano == "2025") ~ sum(prev_atual[uo_cod %in% c("25915", "38901", "40901") & fter_cod != "000" & (str_starts(nr_cod, "1321") | str_starts(nr_cod, "164"))], na.rm = TRUE))) %>%
    as.data.frame(), ano, financeira), by = "ano")

# Junta as demais receitas, aplicando filtros semelhantes
fat <- fat %>%
  left_join(select(receita %>%
    group_by(ano) %>%
    summarise(demais = case_when(unique(ano != "2025") ~ sum(rol[uo_cod %in% c("25915", "38901", "40901") & rp_cod != "0" & !fter_cod %in% c("40", "040", "041")], na.rm = TRUE),
                                 unique(ano == "2025") ~ sum(prev_atual[uo_cod %in% c("25915", "38901", "40901") & !fter_cod %in% c("40", "040", "041", "000") & !(str_starts(nr_cod, "1321") | str_starts(nr_cod, "164"))], na.rm = TRUE))) %>%
    as.data.frame(), ano, demais), by = "ano")

# Junta aportes do Tesouro, filtrando despesas por UO e fonte de recurso
fat <- fat %>%
  left_join(select(despesa %>%
    filter(uo_cod %in% c("25915", "38901", "40901") & fter_cod %in% setdiff(unique(despesa$fter_cod[despesa$uo_cod %in% c("25915", "38901", "40901")]), unique(receita$fter_cod[receita$uo_cod %in% c("25915", "38901", "40901") & receita$fter_cod != "000"]))) %>%
    group_by(ano) %>%
    summarise(tesouro = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, tesouro), by = "ano")

# Calcula a receita total do FAT
fat["receita"] <- fat$pis + fat$financeira + fat$demais + fat$tesouro

# Junta despesas do RGPS (Regime Geral de Previdência Social), filtrando por UO e fonte de recurso
fat <- fat %>%
  left_join(select(despesa %>%
    filter(uo_cod %in% c("25917", "33904", "40904", "55902", "93102") & fter_cod %in% c("40", "040", "041")) %>%
    group_by(ano) %>%
    summarise(desp_rgps = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, desp_rgps), by = "ano")

# Trata valores NA e calcula a receita líquida do FAT
fat$desp_rgps[is.na(fat$desp_rgps)] <- 0
fat["rec_fat"] <- fat$receita - fat$desp_rgps

# Junta as transferências para o BNDES, filtrando por ação
fat <- fat %>%
  left_join(select(despesa %>%
    filter(acao_cod == "0158") %>%
    group_by(ano) %>%
    summarise(bndes = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, bndes), by = "ano")

# Junta as despesas com Seguro-Desemprego, filtrando por ações específicas
fat <- fat %>%
  left_join(select(despesa %>%
    filter(acao_cod %in% c("00H4", "0583", "0585", "0653")) %>%
    group_by(ano) %>%
    summarise(sd = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, sd), by = "ano")

# Junta as despesas com Abono Salarial, filtrando por ação
fat <- fat %>%
  left_join(select(despesa %>%
    filter(acao_cod == "0581") %>%
    group_by(ano) %>%
    summarise(abono = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, abono), by = "ano")

# Junta as demais despesas do FAT, filtrando por UO e excluindo ações já consideradas
fat <- fat %>%
  left_join(select(despesa %>%
    filter(uo_cod %in% c("25915", "38901", "40901") & !acao_cod %in% c("0158", "00H4", "0581", "0583", "0585", "0653")) %>%
    group_by(ano) %>%
    summarise(outras = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, outras), by = "ano")

# Junta o total de despesas do FAT
fat <- fat %>%
  left_join(select(despesa %>%
    filter(uo_cod %in% c("25915", "38901", "40901")) %>%
    group_by(ano) %>%
    summarise(despesa = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, despesa), by = "ano")

# Calcula os resultados econômico e nominal do FAT
fat["economico"] <- fat$rec_fat - fat$despesa + fat$bndes
fat["nominal"] <- fat$rec_fat - fat$despesa

# Renomeia as colunas do dataframe final do FAT para maior clareza
colnames(fat) <- c("Ano", "Receita PIS/PASEP", "Receitas financeiras", "Demais receitas", "Aportes do Tesouro", "Receita Total", "Despesas com RGPS", "Recursos FAT", "Transferência BNDES", "Seguro-desemprego", "Abono salarial", "Outras despesas", "Total de despesas FAT", "Resultado econômico", "Resultado nominal")


# ----------------------------------
# Processamento de dados anuais do RGPS
# ----------------------------------

# Início do processamento para o RGPS
# Calcula a receita do RGPS, com lógica diferente para 2025
rgps <- receita %>%
  group_by(ano) %>%
  summarise(receita = case_when(unique(ano != "2025") ~ sum(rol[uo_cod %in% c("25917", "33904", "40904", "55902", "93102") & rp_cod == "1"], na.rm = TRUE),
                                unique(ano == "2025") ~ sum(prev_atual[uo_cod %in% c("25917", "33904", "40904", "55902", "93102") & !str_starts(nr_cod, "1321") & fter_cod != "444"], na.rm = TRUE))) %>%
  as.data.frame()

# Junta as despesas do RGPS
rgps <- rgps %>%
  left_join(select(despesa %>%
    filter(uo_cod %in% c("25917", "33904", "40904", "55902", "93102") & acao_cod != "0Z00") %>%
    group_by(ano) %>%
    summarise(despesa = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, despesa), by = "ano")

# Calcula o déficit do RGPS como percentual do PIB
rgps["deficit"] <- (rgps$despesa - rgps$receita) / pib$pib * 100

# Junta as despesas com benefícios previdenciários
rgps <- rgps %>%
  left_join(select(despesa %>%
    filter(acao_cod %in% c("0E81", "0E82", "00SJ")) %>%
    group_by(ano) %>%
    summarise(beneficios = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, beneficios), by = "ano")

# Junta as despesas com Compensação Previdenciária
rgps <- rgps %>%
  left_join(select(despesa %>%
    filter(acao_cod == "009W") %>%
    group_by(ano) %>%
    summarise(comprev = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, comprev), by = "ano")

# Junta as despesas com Sentenças Judiciais
rgps <- rgps %>%
  left_join(select(despesa %>%
    filter(uo_cod %in% c("25917", "33904", "40904", "55902", "93102") & acao_cod %in% c("0005", "00WU", "0482", "0486", "0625")) %>%
    group_by(ano) %>%
    summarise(sentencas = if_else(unique(ano != "2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>%
    as.data.frame(), ano, sentencas), by = "ano")

# Renomeia as colunas do dataframe final do RGPS
colnames(rgps) <- c("Ano", "Receitas", "Despesas", "Déficit (% PIB)", "Benefícios previdenciários", "Compensação Previdenciária", "Despesas com Sentenças Judiciais")


# ----------------------------------------------------
# Processamento para o Exercício 2025 - LOA
# ----------------------------------------------------

# Carrega os dados de execução orçamentária de 2025
receita_loa <- read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos_LOA.xlsx", sheet = 1)
despesa_loa <- read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos_LOA.xlsx", sheet = 6)

# ----------------------------------
# Processamento de dados mensais do RGPS (LOA)
# ----------------------------------

# Calcula a previsão inicial e atual da receita do RGPS por mês
rgps_loa <- receita_loa %>%
  filter(uo_cod == "33904" & !fter_cod %in% c("000", "444")) %>%
  group_by(mes) %>%
  summarise(prv_inicial = sum(prev_inicial, na.rm = TRUE)) %>%
  as.data.frame()

rgps_loa <- rgps_loa %>%
  left_join(select(receita_loa %>%
    filter(uo_cod == "33904" & !fter_cod %in% c("000", "444")) %>%
    group_by(mes) %>%
    summarise(prv_atual = sum(prev_atual, na.rm = TRUE)) %>%
    as.data.frame(), mes, prv_atual), by = "mes")

# Define a ordem dos meses e ordena o dataframe
meses <- c("JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO")
rgps_loa$mes <- factor(rgps_loa$mes, levels = meses)
rgps_loa <- rgps_loa %>%
  arrange(mes)

# Junta a receita realizada, pagamentos, dotações e liquidações
rgps_loa <- rgps_loa %>%
  left_join(select(receita_loa %>%
    filter(uo_cod == "33904" & rp_cod == "1" & !fter_cod %in% c("000", "444")) %>%
    group_by(mes) %>%
    summarise(receita = sum(rol, na.rm = TRUE)) %>%
    as.data.frame(), mes, receita), by = "mes")

rgps_loa <- rgps_loa %>%
  left_join(select(despesa_loa %>%
    filter(uo_cod == "33904" & rp_cod != "0") %>%
    group_by(mes) %>%
    summarise(despesa = sum(pagto_total, na.rm = TRUE)) %>%
    as.data.frame(), mes, despesa), by = "mes")

# Calcula o déficit e junta dotações
rgps_loa["deficit"] <- (rgps_loa$despesa - rgps_loa$receita)

rgps_loa <- rgps_loa %>%
  left_join(select(despesa_loa %>%
    filter(uo_cod == "33904" & rp_cod != "0") %>%
    group_by(mes) %>%
    summarise(lei = sum(dot_inicial, na.rm = TRUE)) %>%
    as.data.frame(), mes, lei), by = "mes")

# [...] Omitido para brevidade, mas segue a mesma lógica de juntar e calcular dados mensais.

# Renomeia as colunas do dataframe final do RGPS (LOA)
colnames(rgps_loa) <- c("Mês", "Previsão Inicial da Receita", "Previsão Atual da Receita", "Receita Realizada Líquida", "Pagamentos Totais", "Déficit", "Dotação Inicial", "Dotação Atual", "Liquidado", "Pago", "RAP Inscrito", "RAP Pago", "RAP Cancelado", "RAP a Pagar", "Aposentadorias e Pensões - Urbano (acum.)", "Aposentadorias e Pensões - Urbano (mensal)", "Aposentadorias e Pensões - Rural (acum.)", "Aposentadorias e Pensões - Rural (mensal)", "Demais Benefícios do RGPS - Urbano (acum.)", "Demais Benefícios do RGPS - Urbano (mensal)", "Demais Benefícios do RGPS - Rural (acum.)", "Demais Benefícios do RGPS - Rural (mensal)", "Compensação Previdenciária (acum.)", "Compensação Previdenciária (mensal)", "Despesas com Sentenças Judiciais (acum.)", "Despesas com Sentenças Judiciais (mensal)", "NumMês")

# ----------------------------------
# Processamento de dados mensais do FAT (LOA)
# ----------------------------------

# Início do processamento para o FAT (LOA)
fat_loa <- receita_loa %>%
  filter(uo_cod == "40901" & !fter_cod %in% c("000", "444")) %>%
  group_by(mes) %>%
  summarise(prv_inicial = sum(prev_inicial, na.rm = TRUE)) %>%
  as.data.frame()

# Junta previsões de receita, receita realizada e dotações
fat_loa <- fat_loa %>%
  left_join(select(receita_loa %>%
    filter(uo_cod == "40901" & !fter_cod %in% c("000", "444")) %>%
    group_by(mes) %>%
    summarise(prv_atual = sum(prev_atual, na.rm = TRUE)) %>%
    as.data.frame(), mes, prv_atual), by = "mes")

# Define a ordem dos meses e ordena o dataframe
meses <- c("JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO")
fat_loa$mes <- factor(fat_loa$mes, levels = meses)
fat_loa <- fat_loa %>%
  arrange(mes)

# Junta receita realizada líquida
fat_loa <- fat_loa %>%
  left_join(select(receita_loa %>%
    filter(uo_cod == "40901" & !fter_cod %in% c("000", "444")) %>%
    group_by(mes) %>%
    summarise(receita = sum(rol, na.rm = TRUE)) %>%
    as.data.frame(), mes, receita), by = "mes")

# [...] Omitido para brevidade, mas segue a mesma lógica de juntar e calcular dados mensais.

# Renomeia as colunas do dataframe final do FAT (LOA)
colnames(fat_loa) <- c("Mês", "Previsão inicial da receita", "Previsão atual da receita", "Receita realizada líquida", "Dotação inicial", "Autorizado", "Liquidado", "Pago", "RAP inscritos", "RAP pagos", "RAP cancelados", "RAP a pagar", "Transferência BNDES", "Transferência BNDES - mensal", "Seguro-desemprego", "Seguro-desemprego - mensal", "Abono salarial", "Abono salarial - mensal", "Demais despesas", "Demais despesas - mensal", "NumMês")


# ----------------------------------
# Salvamento dos dados em um novo arquivo Excel
# ----------------------------------

# Cria um novo arquivo Excel e adiciona as planilhas processadas
wb <- createWorkbook()
addWorksheet(wb, sheetName = "FAT")
addWorksheet(wb, sheetName = "FAT_LOA")
addWorksheet(wb, sheetName = "RGPS")
addWorksheet(wb, sheetName = "RGPS_LOA")

# Escreve os dataframes processados nas respectivas planilhas
writeData(wb, sheet = "FAT", fat)
writeData(wb, sheet = "FAT_LOA", fat_loa)
writeData(wb, sheet = "RGPS", rgps)
writeData(wb, sheet = "RGPS_LOA", rgps_loa)

# Salva o arquivo final
saveWorkbook(wb, "H:/Usuários/Túlio/Orçamento/Execução/FundosBI.xlsx", overwrite = TRUE)