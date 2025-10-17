import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# 🔐 Login simples
st.title("🔐 Login")
usuario = st.text_input("Usuário")
senha = st.text_input("Senha", type="password")

if usuario and senha:
    if senha != "1234":
        st.error("Senha incorreta.")
        st.stop()
else:
    st.stop()

# ✅ Autenticação com Google Sheets via Secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["gcp_credentials"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 📄 Abrir planilha e abas
sheet = client.open("2024 - SOLICITAÇÃO DE EMPENHO")
historico = sheet.worksheet("Histórico")
reservas = sheet.worksheet("Reservas")

# 📋 Mostrar histórico na barra lateral
dados = historico.get_all_records()
historico_df = pd.DataFrame(dados)
st.sidebar.title("📋 Histórico de Subprocessos")
st.sidebar.dataframe(historico_df.tail(10))

# 📦 Simulação de sugestões (você pode trocar por seu DataFrame real)
sugestoes = pd.DataFrame([
    {"SOL": "123", "APOIADA": "Sim", "IL": "IL001", "EMPENHO": "EMP001", "ID": "A1", "STATUS": "Pendente", "FORNECEDOR": "Fornecedor X", "PAG": "Sim", "PREGÃO": "Pregão 1", "VALOR": 1000, "DATA": "2025-10-17"},
    {"SOL": "124", "APOIADA": "Não", "IL": "IL002", "EMPENHO": "EMP002", "ID": "A2", "STATUS": "Pendente", "FORNECEDOR": "Fornecedor Y", "PAG": "Não", "PREGÃO": "Pregão 2", "VALOR": 2000, "DATA": "2025-10-17"},
])

st.subheader("🔎 Sugestões de Subprocessos")
for i, row in sugestoes.iterrows():
    with st.expander(f"Subprocesso {row['ID']}"):
        st.write(row.to_dict())

        if st.button(f"✅ Executar {row['ID']}", key=f"exec_{i}"):
            historico.append_row([
                row["SOL"], row["APOIADA"], row["IL"], row["EMPENHO"], row["ID"],
                row["STATUS"], row["FORNECEDOR"], row["PAG"], row["PREGÃO"],
                row["VALOR"], row["DATA"], usuario
            ])
            st.success(f"Subprocesso {row['ID']} registrado no histórico.")

        if st.button(f"📌 Reservar {row['ID']}", key=f"res_{i}"):
            reservas.append_row([row["ID"], usuario])
            st.info(f"Subprocesso {row['ID']} reservado por {usuario}.")
