library(readxl)
library(dplyr)
library("openxlsx")
library("stringr")

##################################
# Dados anuais - Série histórica #
##################################

pib<-read_excel("H:/Usuários/Túlio/Orçamento/Execução/PIB.xlsx")
pib$ano<-as.character(pib$ano)
receita<-read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos.xlsx", sheet = 2)
despesa<-read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos.xlsx", sheet = 5)

###############
# FAT - Anual #
###############

fat<-receita %>% filter(fter_cod %in% c("40","040","041")) %>% group_by(ano) %>% summarise(pis = if_else(unique(ano!="2025"), sum(rol, na.rm = TRUE), sum(prev_atual, na.rm = TRUE))) %>% as.data.frame()
fat<-fat %>% left_join(select(receita %>% group_by(ano) %>% summarise(financeira = case_when(unique(ano!="2025") ~ sum(rol[uo_cod %in% c("25915","38901","40901") & rp_cod=="0"],na.rm = TRUE), unique(ano=="2025") ~ sum(prev_atual[uo_cod %in% c("25915","38901","40901") & fter_cod!="000" & (str_starts(nr_cod,"1321")|str_starts(nr_cod,"164"))],na.rm = TRUE))) %>% as.data.frame(), ano, financeira), by = "ano")
fat<-fat %>% left_join(select(receita %>% group_by(ano) %>% summarise(demais = case_when(unique(ano!="2025") ~ sum(rol[uo_cod %in% c("25915","38901","40901") & rp_cod!="0"  & !fter_cod %in% c("40","040","041")],na.rm = TRUE), unique(ano=="2025") ~ sum(prev_atual[uo_cod %in% c("25915","38901","40901") & !fter_cod %in% c("40","040","041","000") & !(str_starts(nr_cod,"1321")|str_starts(nr_cod,"164"))],na.rm = TRUE))) %>% as.data.frame(), ano, demais), by = "ano")
fat<-fat %>% left_join(select(despesa %>% filter(uo_cod %in% c("25915","38901","40901") & fter_cod %in% setdiff(unique(despesa$fter_cod[despesa$uo_cod %in% c("25915","38901","40901")]), unique(receita$fter_cod[receita$uo_cod %in% c("25915","38901","40901") & receita$fter_cod!="000"]))) %>% group_by(ano) %>% summarise(tesouro = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, tesouro), by = "ano")
fat["receita"]<-fat$pis+fat$financeira+fat$demais+fat$tesouro
fat<-fat %>% left_join(select(despesa %>% filter(uo_cod %in% c("25917","33904","40904","55902","93102") & fter_cod %in% c("40","040","041")) %>% group_by(ano) %>% summarise(desp_rgps = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, desp_rgps), by = "ano")
fat$desp_rgps[is.na(fat$desp_rgps)]<-0
fat["rec_fat"]<-fat$receita-fat$desp_rgps

fat<-fat %>% left_join(select(despesa %>% filter(acao_cod=="0158") %>% group_by(ano) %>% summarise(bndes = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, bndes), by = "ano")
fat<-fat %>% left_join(select(despesa %>% filter(acao_cod %in% c("00H4","0583","0585","0653")) %>% group_by(ano) %>% summarise(sd = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, sd), by = "ano")
fat<-fat %>% left_join(select(despesa %>% filter(acao_cod=="0581") %>% group_by(ano) %>% summarise(abono = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, abono), by = "ano")
fat<-fat %>% left_join(select(despesa %>% filter(uo_cod %in% c("25915","38901","40901") & !acao_cod %in% c("0158","00H4","0581","0583","0585","0653")) %>% group_by(ano) %>% summarise(outras = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, outras), by = "ano")
fat<-fat %>% left_join(select(despesa %>% filter(uo_cod %in% c("25915","38901","40901")) %>% group_by(ano) %>% summarise(despesa = if_else(unique(ano!="2025"), sum(pagto_total,na.rm = TRUE), sum(autorizado,na.rm = TRUE))) %>% as.data.frame(), ano, despesa), by = "ano")

fat["economico"]<-fat$rec_fat-fat$despesa+fat$bndes
fat["nominal"]<-fat$rec_fat-fat$despesa

colnames(fat)<-c("Ano",
                 "Receita PIS/PASEP",
                 "Receitas financeiras",
                 "Demais receitas",
                 "Aportes do Tesouro",
                 "Receita Total",
                 "Despesas com RGPS",
                 "Recursos FAT",
                 "Transferência BNDES",
                 "Seguro-desemprego",
                 "Abono salarial",
                 "Outras despesas",
                 "Total de despesas FAT",
                 "Resultado econômico",
                 "Resultado nominal")

################
# RGPS - Anual #
################

rgps<-receita %>% group_by(ano) %>% summarise(receita = case_when(unique(ano!="2025") ~ sum(rol[uo_cod %in% c("25917","33904","40904","55902","93102") & rp_cod=="1"], na.rm = TRUE), unique(ano=="2025") ~ sum(prev_atual[uo_cod %in% c("25917","33904","40904","55902","93102") & !str_starts(nr_cod,"1321") & fter_cod!="444"], na.rm = TRUE))) %>% as.data.frame()
rgps<-rgps %>% left_join(select(despesa %>% filter(uo_cod %in% c("25917","33904","40904","55902","93102") & acao_cod!="0Z00") %>% group_by(ano) %>% summarise(despesa = if_else(unique(ano!="2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>% as.data.frame(), ano, despesa),by = "ano")
rgps["deficit"]<-(rgps$despesa-rgps$receita)/pib$pib*100
rgps<-rgps %>% left_join(select(despesa %>% filter(acao_cod %in% c("0E81","0E82","00SJ")) %>% group_by(ano) %>% summarise(beneficios = if_else(unique(ano!="2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>% as.data.frame(), ano, beneficios),by = "ano")
#rgps<-rgps %>% left_join(select(despesa %>% filter(acao_cod %in% c("0E81","00SJ") & ed_cod %in% c("54","56")) %>% group_by(ano) %>% summarise(urb_perm = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), ano, urb_perm),by = "ano")
#rgps<-rgps %>% left_join(select(despesa %>% filter(acao_cod %in% c("0E82","00SJ") & ed_cod %in% c("53","55")) %>% group_by(ano) %>% summarise(rur_perm = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), ano, rur_perm),by = "ano")
#rgps<-rgps %>% left_join(select(despesa %>% filter((acao_cod=="0E81" & !ed_cod %in% c("54","56"))|(acao_cod=="00SJ" & !ed_cod %in% c("53","54","55","56") & po_cod=="0001")) %>% group_by(ano) %>% summarise(urb_demais = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), ano, urb_demais),by = "ano")
#rgps<-rgps %>% left_join(select(despesa %>% filter((acao_cod=="0E82" & !ed_cod %in% c("53","55"))|(acao_cod=="00SJ" & !ed_cod %in% c("53","54","55","56") & po_cod=="0002")) %>% group_by(ano) %>% summarise(rur_demais = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), ano, rur_demais),by = "ano")
rgps<-rgps %>% left_join(select(despesa %>% filter(acao_cod=="009W") %>% group_by(ano) %>% summarise(comprev = if_else(unique(ano!="2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>% as.data.frame(), ano, comprev),by = "ano")
rgps<-rgps %>% left_join(select(despesa %>% filter(uo_cod %in% c("25917","33904","40904","55902","93102") & acao_cod %in% c("0005","00WU","0482","0486","0625")) %>% group_by(ano) %>% summarise(sentencas = if_else(unique(ano!="2025"), sum(pagto_total, na.rm = TRUE), sum(autorizado, na.rm = TRUE))) %>% as.data.frame(), ano, sentencas),by = "ano")
colnames(rgps)<-c("Ano",
                  "Receitas","Despesas",
                  "Déficit (% PIB)",
                  "Benefícios previdenciários",
                  "Compensação Previdenciária",
                  "Despesas com Sentenças Judiciais")

################################################
# Exercício 2025 - Execução orçamentária anual #
################################################

##############
# RGPS - LOA #
##############

receita_loa<-read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos_LOA.xlsx", sheet = 1)
despesa_loa<-read_excel("H:/Usuários/Túlio/Orçamento/Execução/Fundos_LOA.xlsx", sheet = 6)

rgps_loa<-receita_loa %>% filter(uo_cod=="33904" & !fter_cod %in% c("000","444")) %>% group_by(mes) %>% summarise(prv_inicial = sum(prev_inicial, na.rm = TRUE)) %>% as.data.frame()
rgps_loa<-rgps_loa %>% left_join(select(receita_loa %>% filter(uo_cod=="33904" & !fter_cod %in% c("000","444")) %>% group_by(mes) %>% summarise(prv_atual = sum(prev_atual, na.rm = TRUE)) %>% as.data.frame(), mes, prv_atual), by = "mes")

meses<-c("JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO","JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO")
rgps_loa$mes<-factor(rgps_loa$mes,levels = meses)
rgps_loa<-rgps_loa %>% arrange(mes)

rgps_loa<-rgps_loa %>% left_join(select(receita_loa %>% filter(uo_cod=="33904" & rp_cod=="1" & !fter_cod %in% c("000","444")) %>% group_by(mes) %>% summarise(receita = sum(rol, na.rm = TRUE)) %>% as.data.frame(), mes, receita), by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="33904" & rp_cod!="0") %>% group_by(mes) %>% summarise(despesa = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, despesa),by = "mes")
rgps_loa["deficit"]<-(rgps_loa$despesa-rgps_loa$receita)
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="33904" & rp_cod!="0") %>% group_by(mes) %>% summarise(lei = sum(dot_inicial, na.rm = TRUE)) %>% as.data.frame(), mes, lei),by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="33904" & rp_cod!="0") %>% group_by(mes) %>% summarise(atual = sum(autorizado, na.rm = TRUE)) %>% as.data.frame(), mes, atual),by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="33904" & rp_cod!="0") %>% group_by(mes) %>% summarise(liquid = sum(liquidado, na.rm = TRUE)) %>% as.data.frame(), mes, liquid),by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="33904" & rp_cod!="0") %>% group_by(mes) %>% summarise(pago = sum(pago, na.rm = TRUE)) %>% as.data.frame(), mes, pago),by = "mes")

rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25917","33904","40904","55902") & rp_cod!="0") %>% group_by(mes) %>% summarise(rp_insc = sum(rap_insc, na.rm = TRUE)) %>% as.data.frame(), mes, rp_insc),by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25917","33904","40904","55902") & rp_cod!="0") %>% group_by(mes) %>% summarise(rp_pago = sum(rap_pago, na.rm = TRUE)) %>% as.data.frame(), mes, rp_pago),by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25917","33904","40904","55902") & rp_cod!="0") %>% group_by(mes) %>% summarise(rp_canc = sum(rap_canc, na.rm = TRUE)) %>% as.data.frame(), mes, rp_canc),by = "mes")
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25917","33904","40904","55902") & rp_cod!="0") %>% group_by(mes) %>% summarise(rp_a_pagar = sum(rap_a_pagar, na.rm = TRUE)) %>% as.data.frame(), mes, rp_a_pagar),by = "mes")

rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(acao_cod %in% c("0E81","00SJ") & ed_cod %in% c("54","56")) %>% group_by(mes) %>% summarise(urb_perm = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, urb_perm),by = "mes")
rgps_loa<-rgps_loa %>% mutate(apmurb = urb_perm - lag(urb_perm, default = first(urb_perm)))
rgps_loa$apmurb[1]<-rgps_loa$urb_perm[1]
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(acao_cod %in% c("0E82","00SJ") & ed_cod %in% c("53","55")) %>% group_by(mes) %>% summarise(rur_perm = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, rur_perm),by = "mes")
rgps_loa<-rgps_loa %>% mutate(apmrur = rur_perm - lag(rur_perm, default = first(rur_perm)))
rgps_loa$apmrur[1]<-rgps_loa$rur_perm[1]
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter((acao_cod=="0E81" & !ed_cod %in% c("54","56"))|(acao_cod=="00SJ" & !ed_cod %in% c("53","54","55","56") & po_cod=="0001")) %>% group_by(mes) %>% summarise(urb_demais = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, urb_demais),by = "mes")
rgps_loa<-rgps_loa %>% mutate(dmurb = urb_demais - lag(urb_demais, default = first(urb_demais)))
rgps_loa$dmurb[1]<-rgps_loa$urb_demais[1]
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter((acao_cod=="0E82" & !ed_cod %in% c("53","55"))|(acao_cod=="00SJ" & !ed_cod %in% c("53","54","55","56") & po_cod=="0002")) %>% group_by(mes) %>% summarise(rur_demais = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, rur_demais),by = "mes")
rgps_loa<-rgps_loa %>% mutate(dmrur = rur_demais - lag(rur_demais, default = first(rur_demais)))
rgps_loa$dmrur[1]<-rgps_loa$rur_demais[1]
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(acao_cod=="009W") %>% group_by(mes) %>% summarise(comprev = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, comprev),by = "mes")
rgps_loa<-rgps_loa %>% mutate(comprevm = comprev - lag(comprev, default = first(comprev)))
rgps_loa$comprevm[1]<-rgps_loa$comprev[1]
rgps_loa<-rgps_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25917","33904","40904","55902") & acao_cod %in% c("0005","00WU","0482","0486","0625")) %>% group_by(mes) %>% summarise(sentencas = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, sentencas),by = "mes")
rgps_loa<-rgps_loa %>% mutate(sentencasm = sentencas - lag(sentencas, default = first(sentencas)))
rgps_loa$sentencasm[1]<-rgps_loa$sentencas[1]
rgps_loa["mesnum"]<-match(rgps_loa$mes,meses)

colnames(rgps_loa)<-c("Mês",
                      "Previsão Inicial da Receita",
                      "Previsão Atual da Receita",
                      "Receita Realizada Líquida",
                      "Pagamentos Totais",
                      "Déficit",
                      "Dotação Inicial",
                      "Dotação Atual",
                      "Liquidado",
                      "Pago",
                      "RAP Inscrito",
                      "RAP Pago",
                      "RAP Cancelado",
                      "RAP a Pagar",
                      "Aposentadorias e Pensões - Urbano (acum.)",
                      "Aposentadorias e Pensões - Urbano (mensal)",
                      "Aposentadorias e Pensões - Rural (acum.)",
                      "Aposentadorias e Pensões - Rural (mensal)",
                      "Demais Benefícios do RGPS - Urbano (acum.)",
                      "Demais Benefícios do RGPS - Urbano (mensal)",
                      "Demais Benefícios do RGPS - Rural (acum.)",
                      "Demais Benefícios do RGPS - Rural (mensal)",
                      "Compensação Previdenciária (acum.)",
                      "Compensação Previdenciária (mensal)",
                      "Despesas com Sentenças Judiciais (acum.)",
                      "Despesas com Sentenças Judiciais (mensal)",
                      "NumMês")

#############
# FAT - LOA #
#############

fat_loa<-receita_loa %>% filter(uo_cod=="40901" & !fter_cod %in% c("000","444")) %>% group_by(mes) %>% summarise(prv_inicial = sum(prev_inicial, na.rm = TRUE)) %>% as.data.frame()
fat_loa<-fat_loa %>% left_join(select(receita_loa %>% filter(uo_cod=="40901" & !fter_cod %in% c("000","444")) %>% group_by(mes) %>% summarise(prv_atual = sum(prev_atual, na.rm = TRUE)) %>% as.data.frame(), mes, prv_atual), by = "mes")

meses<-c("JANEIRO","FEVEREIRO","MARCO","ABRIL","MAIO","JUNHO","JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO")
fat_loa$mes<-factor(fat_loa$mes,levels = meses)
fat_loa<-fat_loa %>% arrange(mes)

fat_loa<-fat_loa %>% left_join(select(receita_loa %>% filter(uo_cod=="40901" & !fter_cod %in% c("000","444")) %>% group_by(mes) %>% summarise(receita = sum(rol, na.rm = TRUE)) %>% as.data.frame(), mes, receita), by = "mes")

fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="40901") %>% group_by(mes) %>% summarise(lei = sum(dot_inicial, na.rm = TRUE)) %>% as.data.frame(), mes, lei),by = "mes")
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="40901") %>% group_by(mes) %>% summarise(atual = sum(autorizado, na.rm = TRUE)) %>% as.data.frame(), mes, atual),by = "mes")
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="40901") %>% group_by(mes) %>% summarise(liquid = sum(liquidado, na.rm = TRUE)) %>% as.data.frame(), mes, liquid),by = "mes")
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod=="40901") %>% group_by(mes) %>% summarise(pago = sum(pago, na.rm = TRUE)) %>% as.data.frame(), mes, pago),by = "mes")

fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25915","38901","40901")) %>% group_by(mes) %>% summarise(rp_insc = sum(rap_insc, na.rm = TRUE)) %>% as.data.frame(), mes, rp_insc),by = "mes")
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25915","38901","40901")) %>% group_by(mes) %>% summarise(rp_pago = sum(rap_pago, na.rm = TRUE)) %>% as.data.frame(), mes, rp_pago),by = "mes")
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25915","38901","40901")) %>% group_by(mes) %>% summarise(rp_canc = sum(rap_canc, na.rm = TRUE)) %>% as.data.frame(), mes, rp_canc),by = "mes")
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25915","38901","40901")) %>% group_by(mes) %>% summarise(rp_a_pagar = sum(rap_a_pagar, na.rm = TRUE)) %>% as.data.frame(), mes, rp_a_pagar),by = "mes")

fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(acao_cod=="0158") %>% group_by(mes) %>% summarise(bndes = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, bndes),by = "mes")
fat_loa<-fat_loa %>% mutate(bndesm = bndes - lag(bndes, default = first(bndes)))
fat_loa$bndesm[1]<-fat_loa$bndes[1]
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(acao_cod=="00H4") %>% group_by(mes) %>% summarise(sd = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, sd),by = "mes")
fat_loa<-fat_loa %>% mutate(sdm = sd - lag(bndes, default = first(sd)))
fat_loa$sdm[1]<-fat_loa$sd[1]
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(acao_cod=="0581") %>% group_by(mes) %>% summarise(abono = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, abono),by = "mes")
fat_loa<-fat_loa %>% mutate(abonom = bndes - lag(abono, default = first(abono)))
fat_loa$abonom[1]<-fat_loa$abono[1]
fat_loa<-fat_loa %>% left_join(select(despesa_loa %>% filter(uo_cod %in% c("25915","38901","40901") & !acao_cod %in% c("00H4","0158","0581")) %>% group_by(mes) %>% summarise(demais = sum(pagto_total, na.rm = TRUE)) %>% as.data.frame(), mes, demais),by = "mes")
fat_loa<-fat_loa %>% mutate(demaism = demais - lag(demais, default = first(demais)))
fat_loa$demaism[1]<-fat_loa$demais[1]
fat_loa["mesnum"]<-match(fat_loa$mes,meses)

colnames(fat_loa)<-c("Mês",
                     "Previsão inicial da receita",
                     "Previsão atual da receita",
                     "Receita realizada líquida",
                     "Dotação inicial",
                     "Autorizado",
                     "Liquidado",
                     "Pago",
                     "RAP inscritos",
                     "RAP pagos",
                     "RAP cancelados",
                     "RAP a pagar",
                     "Transferência BNDES",
                     "Transferência BNDES - mensal",
                     "Seguro-desemprego",
                     "Seguro-desemprego - mensal",
                     "Abono salarial",
                     "Abono salarial - mensal",
                     "Demais despesas",
                     "Demais despesas - mensal",
                     "NumMês")

wb<-createWorkbook()
addWorksheet(wb,sheetName = "FAT")
addWorksheet(wb,sheetName = "FAT_LOA")
addWorksheet(wb,sheetName = "RGPS")
addWorksheet(wb,sheetName = "RGPS_LOA")
writeData(wb, sheet = "FAT", fat)
writeData(wb, sheet = "FAT_LOA", fat_loa)
writeData(wb, sheet = "RGPS", rgps)
writeData(wb, sheet = "RGPS_LOA", rgps_loa)
saveWorkbook(wb,"H:/Usuários/Túlio/Orçamento/Execução/FundosBI.xlsx",overwrite = TRUE)
