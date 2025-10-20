import pandas as pd
import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Autenticação com Google Sheets
def conectar_planilha():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
    client = gspread.authorize(creds)
    return client

# Função para registrar subprocesso executado
def registrar_executado(id_bloco, fornecedor, pag, valor):
    try:
        client = conectar_planilha()
        planilha = client.open("Subprocessos Inteligentes")  # nome da planilha
        aba = planilha.worksheet("Executados")  # nome da aba
        nova_linha = [id_bloco, "Jefferson", datetime.now().strftime("%d/%m/%Y %H:%M"), fornecedor, pag, valor]
        aba.append_row(nova_linha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar na aba Executados: {e}")
        return False

# Carregar dados principais
@st.cache_data
def carregar_planilha():
    url_dados = "https://docs.google.com/spreadsheets/d/1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ/export?format=csv"
    df = pd.read_csv(url_dados)
    df.columns = df.columns.str.strip()
    return df

# Carregar subprocessos já executados
@st.cache_data
def carregar_executados():
    try:
        client = conectar_planilha()
        planilha = client.open("Subprocessos Inteligentes")
        aba = planilha.worksheet("Executados")
        dados = aba.get_all_records()
        return set(str(item["ID"]) for item in dados if "ID" in item)
    except:
        return set()

df = carregar_planilha()
ids_executados = carregar_executados()

st.title("📄 Subprocessos Inteligentes")
st.write("Planilha carregada com sucesso!")

# Filtro robusto
status_temp = df["STATUS"].astype(str).str.lower().str.strip()
df_filtrado = df[~status_temp.str.contains("cancelado|enviado aci", na=False)]

# Agrupar por FORNECEDOR e PAG
agrupamentos = []
for _, grupo in df_filtrado.groupby(["FORNECEDOR", "PAG"]):
    blocos = [grupo.iloc[i:i+9] for i in range(0, len(grupo), 9)]
    agrupamentos.extend(blocos)

# Paginação
sugestoes_por_pagina = 8
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = 0

total_paginas = (len(agrupamentos) - 1) // sugestoes_por_pagina + 1
inicio = st.session_state.pagina_atual * sugestoes_por_pagina
fim = inicio + sugestoes_por_pagina
agrupamentos_pagina = agrupamentos[inicio:fim]

# Histórico local
if "historico" not in st.session_state:
    st.session_state.historico = []

# Subprocessos em execução
if "execucoes_globais" not in st.session_state:
    st.session_state.execucoes_globais = set()

# Função para destacar linhas
def destacar_linhas_em_execucao(df):
    def cor_linha(row):
        id_linha = str(row["ID"])
        if id_linha in st.session_state.execucoes_globais:
            return ["background-color: #FFF3CD"] * len(row)
        elif id_linha in ids_executados:
            return ["background-color: #E0E0E0"] * len(row)
        else:
            return [""] * len(row)
    return df.style.apply(cor_linha, axis=1)

# Exibir sugestões
sugestoes_visiveis = 0
for i, bloco in enumerate(agrupamentos_pagina):
    indice_global = inicio + i
    id_bloco = str(bloco["ID"].iloc[0])

    if id_bloco in ids_executados:
        continue

    sugestoes_visiveis += 1
    st.subheader(f"Subprocesso sugerido {indice_global + 1}")
    st.dataframe(destacar_linhas_em_execucao(bloco))

    col1, col2 = st.columns(2)
    with col1:
        botao_execucao = st.button(
            "🔓 Liberar execução" if id_bloco in st.session_state.execucoes_globais else "❌ Marcar como em execução",
            key=f"execucao_{indice_global}"
        )
        if botao_execucao:
            if id_bloco in st.session_state.execucoes_globais:
                st.session_state.execucoes_globais.remove(id_bloco)
                st.info("Subprocesso liberado.")
            else:
                st.session_state.execucoes_globais.add(id_bloco)
                st.warning("Subprocesso marcado como em execução.")

    with col2:
        if st.button("✔ Marcar como executado", key=f"finalizar_{indice_global}"):
            fornecedor = bloco["FORNECEDOR"].iloc[0]
            pag = bloco["PAG"].iloc[0]
            valor = bloco["VALOR"].sum()

            sucesso = registrar_executado(id_bloco, fornecedor, pag, valor)
            if sucesso:
                st.success("Subprocesso registrado na aba Executados!")
            else:
                st.warning("Subprocesso marcado, mas não foi salvo na planilha.")

            st.session_state.historico.append({
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "fornecedor": fornecedor,
                "pag": pag,
                "ids": id_bloco,
                "valor_total": valor
            })

# Se não houver mais sugestões visíveis
if sugestoes_visiveis == 0:
    st.info("✅ Nenhuma sugestão restante nesta página.")

# Navegação
st.write(f"📄 Página {st.session_state.pagina_atual + 1} de {total_paginas}")
col_nav1, col_nav2 = st.columns([1, 1])
pagina_anterior = col_nav1.button("⬅ Página anterior")
pagina_proxima = col_nav2.button("➡ Próxima página")

if pagina_anterior and st.session_state.pagina_atual > 0:
    st.session_state.pagina_atual -= 1

if pagina_proxima and st.session_state.pagina_atual < total_paginas - 1:
    st.session_state.pagina_atual += 1

# Histórico lateral
st.sidebar.title("📋 Histórico de Subprocessos")
if st.session_state.historico:
    historico_df = pd.DataFrame(st.session_state.historico)
    st.sidebar.dataframe(historico_df)
else:
    st.sidebar.info("Nenhum subprocesso registrado ainda.")
