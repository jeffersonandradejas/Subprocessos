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

# 📄 Abrir planilha e abas usando o ID da planilha
sheet = client.open_by_key("1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ")
historico = sheet.worksheet("Histórico")
reservas = sheet.worksheet("Reservas")

# 📋 Mostrar histórico na barra lateral
dados = historico.get_all_records()
historico_df = pd.DataFrame(dados)
st.sidebar.title("📋 Histórico de Subprocessos")
st.sidebar.dataframe(historico_df.tail(10))

# 📦 Sugestões simuladas (substitua por seu DataFrame real se quiser)
sugestoes = pd.DataFrame([
    {"SOL": "123", "APOIADA": "Sim", "IL": "IL001", "EMPENHO": "EMP001", "ID": "A1", "STATUS": "Pendente", "FORNECEDOR": "Fornecedor X", "PAG": "Sim", "PREGÃO": "Pregão 1", "VALOR": 1000, "DATA": "2025-10-17"},
    {"SOL": "124", "APOIADA": "Não", "IL": "IL002", "EMPENHO": "EMP002", "ID": "A2", "STATUS": "Pendente", "FORNECEDOR": "Fornecedor Y", "PAG": "Não", "PREGÃO": "Pregão 2", "VALOR": 2000, "DATA": "2025-10-17"},
])

st.subheader("🔎 Sugestões de Subprocessos")
for i, row in sugestoes.iterrows():
    with st.expander(f"Subprocesso {row['ID']}"):
        st.write(f"**SOL:** {row['SOL']}")
        st.write(f"**APOIADA:** {row['APOIADA']}")
        st.write(f"**IL:** {row['IL']}")
        st.write(f"**EMPENHO:** {row['EMPENHO']}")
        st.write(f"**STATUS:** {row['STATUS']}")
        st.write(f"**FORNECEDOR:** {row['FORNECEDOR']}")
        st.write(f"**PAG:** {row['PAG']}")
        st.write(f"**PREGÃO:** {row['PREGÃO']}")
        st.write(f"**VALOR:** R$ {row['VALOR']}")
        st.write(f"**DATA:** {row['DATA']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Executar {row['ID']}", key=f"exec_{i}"):
                historico.append_row([
                    row["SOL"], row["APOIADA"], row["IL"], row["EMPENHO"], row["ID"],
                    row["STATUS"], row["FORNECEDOR"], row["PAG"], row["PREGÃO"],
                    row["VALOR"], row["DATA"], st.session_state.usuario
                ])
                st.success(f"Subprocesso {row['ID']} registrado no histórico.")
        with col2:
            if st.button(f"📌 Reservar {row['ID']}", key=f"res_{i}"):
                reservas.append_row([row["ID"], st.session_state.usuario])
                st.info(f"Subprocesso {row['ID']} reservado por {st.session_state.usuario}.")
