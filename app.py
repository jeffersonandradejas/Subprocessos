import pandas as pd
import streamlit as st
from datetime import datetime

# URL da planilha pública no formato CSV
url = "https://docs.google.com/spreadsheets/d/1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ/export?format=csv"

# Carregar os dados
@st.cache_data
def carregar_planilha():
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()  # remove espaços extras nos nomes das colunas
    return df

df = carregar_planilha()

st.title("📄 Subprocessos Inteligentes")
st.write("Planilha carregada com sucesso!")

# Filtrar registros com status pendente
status_invalidos = ["ENVIADO ACI", "ASSINAR OD CANCELADO", "ASSINAR CH"]
df_filtrado = df[~df["STATUS"].isin(status_invalidos)]

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

    # Montar texto para copiar
    texto = ""
    for _, row in bloco.iterrows():
        linha = f'{row["SOL"]}\t{row["APOIADA"]}\t{row["IL"]}\t{row["EMPENHO"]}\t{row["ID"]}\t{row["STATUS"]}\t{row["FORNECEDOR"]}\t{row["PAG"]}\t{row["PREGÃO"]}\t{row["VALOR"]}\t{row["DATA"]}'
        texto += linha + "\n"

    # Controle de execução por sessão
    exec_key = f"em_execucao_{i}"
    if exec_key not in st.session_state:
        st.session_state[exec_key] = False

    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_area("Copiar para o Intraer", texto, height=250, key=f"texto_{i}", disabled=st.session_state[exec_key])
    with col2:
        if not st.session_state[exec_key]:
            if st.button(f"❌ Marcar como em execução", key=f"bloquear_{i}"):
                st.session_state[exec_key] = True
                st.warning("Este subprocesso foi marcado como em execução.")
        else:
            if st.button(f"🔓 Liberar execução", key=f"desbloquear_{i}"):
                st.session_state[exec_key] = False
                st.info("Subprocesso liberado para edição.")

    # Botão de execução
    if st.button(f"✅ Marcar como executado - Sugestão {i+1}", key=f"executar_{i}"):
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
