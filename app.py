import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
execucoes = sheet.worksheet("Execuções")
aba_principal = sheet.get_worksheet(0)  # primeira aba da planilha
df = pd.DataFrame(aba_principal.get_all_records())

# 🔎 Agrupamento preferencial por FORNECEDOR, secundário por PAG
agrupamentos = []
usados = set()

# 1️⃣ Agrupar por FORNECEDOR
for fornecedor, grupo in df.groupby("FORNECEDOR"):
    for i in range(0, len(grupo), 9):
        bloco = grupo.iloc[i:i+9]
        agrupamentos.append(bloco)
        usados.update(bloco.index)

# 2️⃣ Agrupar por PAG para linhas não usadas
restantes = df.loc[~df.index.isin(usados)]
for pag, grupo in restantes.groupby("PAG"):
    for i in range(0, len(grupo), 9):
        agrupamentos.append(grupo.iloc[i:i+9])

# 📋 Mostrar histórico na barra lateral
dados_hist = historico.get_all_records()
historico_df = pd.DataFrame(dados_hist)
st.sidebar.title("📋 Histórico de Subprocessos")
st.sidebar.dataframe(historico_df.tail(10))

# 📦 Exibir sugestões com campo de responsável
st.subheader("🔎 Sugestões de Subprocessos")
reservas_data = reservas.get_all_records()
reservas_df = pd.DataFrame(reservas_data)

for i, grupo in enumerate(agrupamentos):
    subprocesso_id = f"Subprocesso {i+1}"
    with st.expander(f"{subprocesso_id} — {grupo.iloc[0]['FORNECEDOR']}"):
        st.dataframe(grupo)

        # Verificar se já foi reservado
        reservado_por = reservas_df[reservas_df["ID"] == subprocesso_id]["Responsável"].values
        if len(reservado_por) > 0:
            st.warning(f"📌 Reservado por: {reservado_por[0]}")
        else:
            st.info("📌 Ainda não reservado")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Executar {subprocesso_id}", key=f"exec_{i}"):
                for _, row in grupo.iterrows():
                    historico.append_row([
                        row["SOL"], row["APOIADA"], row["IL"], row["EMPENHO"], row["ID"],
                        row.get("STATUS", ""), row["FORNECEDOR"], row["PAG"], row["PREGÃO"],
                        row["VALOR"], row["DATA"], st.session_state.usuario
                    ])
                    execucoes.append_row([
                        row["SOL"], row["APOIADA"], row["IL"], row["EMPENHO"], row["ID"],
                        row["FORNECEDOR"], row["PAG"], row["PREGÃO"], row["VALOR"],
                        row["DATA"], st.session_state.usuario
                    ])
                st.success(f"{subprocesso_id} registrado no histórico e na aba Execuções.")
        with col2:
            if st.button(f"📌 Reservar {subprocesso_id}", key=f"res_{i}"):
                reservas.append_row([subprocesso_id, st.session_state.usuario])
                st.info(f"{subprocesso_id} reservado por {st.session_state.usuario}.")
