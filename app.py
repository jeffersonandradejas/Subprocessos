import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# 🔐 Controle de sessão para login
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""

# 🔐 Tela de login
if not st.session_state.autenticado:
    st.title("🔐 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == "1234":
            st.session_state.autenticado = True
            st.session_state.usuario = usuario
        else:
            st.error("Senha incorreta.")
    st.stop()

# ✅ Autenticação com Google Sheets via Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_credentials"], scope)
client = gspread.authorize(creds)

# 📄 Abrir planilha e abas
sheet = client.open_by_key("1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ")
historico = sheet.worksheet("Histórico")
reservas = sheet.worksheet("Reservas")
dados = sheet.worksheet("Dados")  # aba principal com os subprocessos

# 📋 Carregar dados da aba "Dados"
df = pd.DataFrame(dados.get_all_records())

# 🔎 Agrupar por FORNECEDOR ou PAG (máximo 9 linhas por grupo)
agrupamentos = []

# Agrupar por FORNECEDOR
for fornecedor, grupo in df.groupby("FORNECEDOR"):
    for i in range(0, len(grupo), 9):
        agrupamentos.append(grupo.iloc[i:i+9])

# Agrupar por PAG (caso queira usar isso como alternativa)
# for pag, grupo in df.groupby("PAG"):
#     for i in range(0, len(grupo), 9):
#         agrupamentos.append(grupo.iloc[i:i+9])

# 📦 Exibir cada agrupamento como um subprocesso
st.subheader("🔎 Sugestões de Subprocessos")
for i, grupo in enumerate(agrupamentos):
    with st.expander(f"Subprocesso {i+1} — {grupo.iloc[0]['FORNECEDOR']}"):
        st.dataframe(grupo)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Executar Subprocesso {i+1}", key=f"exec_{i}"):
                for _, row in grupo.iterrows():
                    historico.append_row([
                        row["SOL"], row["APOIADA"], row["IL"], row["EMPENHO"], row["ID"],
                        row["STATUS"], row["FORNECEDOR"], row["PAG"], row["PREGÃO"],
                        row["VALOR"], row["DATA"], st.session_state.usuario
                    ])
                st.success(f"Subprocesso {i+1} registrado no histórico.")
        with col2:
            if st.button(f"📌 Reservar Subprocesso {i+1}", key=f"res_{i}"):
                reservas.append_row([f"Subprocesso {i+1}", st.session_state.usuario])
                st.info(f"Subprocesso {i+1} reservado por {st.session_state.usuario}.")
