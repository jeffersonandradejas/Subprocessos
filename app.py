import pandas as pd
import streamlit as st
from datetime import datetime

# URL da planilha pública no formato CSV
url = "https://docs.google.com/spreadsheets/d/1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ/export?format=csv"

# Carregar os dados
@st.cache_data
def carregar_planilha():
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

df = carregar_planilha()

st.title("📄 Subprocessos Inteligentes")
st.write("Planilha carregada com sucesso!")

# 🔍 Filtrar registros com status inválido
status_invalidos = ["cancelado", "enviado ACI"]
df_filtrado = df[~df["STATUS"].str.lower().str.contains("|".join(status_invalidos), na=False)]

# Agrupar por FORNECEDOR e PAG
agrupamentos = []
for _, grupo in df_filtrado.groupby(["FORNECEDOR", "PAG"]):
    blocos = [grupo.iloc[i:i+9] for i in range(0, len(grupo), 9)]
    agrupamentos.extend(blocos)

# Histórico de subprocessos
if "historico" not in st.session_state:
    st.session_state.historico = []

# Exibir sugestões
for i, bloco in enumerate(agrupamentos):
    st.subheader(f"Subprocesso sugerido {i+1}")
    st.dataframe(bloco)

    # Controle de execução por sessão
    exec_key = f"em_execucao_{i}"
    if exec_key not in st.session_state:
        st.session_state[exec_key] = False

    # Botões lado a lado
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state[exec_key]:
            if st.button("❌ Marcar como em execução", key=f"bloquear_{i}"):
                st.session_state[exec_key] = True
                st.warning("Este subprocesso foi marcado como em execução.")
        else:
            if st.button("🔓 Liberar execução", key=f"desbloquear_{i}"):
                st.session_state[exec_key] = False
                st.info("Subprocesso liberado para edição.")

    with col2:
        if st.button("✅ Marcar como executado", key=f"executar_{i}"):
            registro = {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "fornecedor": bloco["FORNECEDOR"].iloc[0],
                "pag": bloco["PAG"].iloc[0],
                "ids": ", ".join(bloco["ID"].astype(str)),
                "valor_total": bloco["VALOR"].sum()
            }
            st.session_state.historico.append(registro)
            st.success("Subprocesso registrado no histórico!")
            st.session_state[exec_key] = False  # libera após execução

# Histórico lateral
st.sidebar.title("📋 Histórico de Subprocessos")
if st.session_state.historico:
    historico_df = pd.DataFrame(st.session_state.historico)
    st.sidebar.dataframe(historico_df)
else:
    st.sidebar.info("Nenhum subprocesso registrado ainda.")
