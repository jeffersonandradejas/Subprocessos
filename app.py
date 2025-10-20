import pandas as pd
import streamlit as st
from datetime import datetime

# URL da planilha pública no formato CSV
url = "https://docs.google.com/spreadsheets/d/1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ/export?format=csv"

@st.cache_data
def carregar_planilha():
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()
    return df

df = carregar_planilha()

st.title("📄 Subprocessos Inteligentes")
st.write("Planilha carregada com sucesso!")

# Filtrar registros com status inválido
status_invalidos = ["cancelado", "enviado ACI"]
df_filtrado = df[~df["STATUS"].str.lower().str.contains("|".join(status_invalidos), na=False)]

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

st.write(f"📄 Página {st.session_state.pagina_atual + 1} de {total_paginas}")
col_nav1, col_nav2 = st.columns([1, 1])
with col_nav1:
    if st.button("⬅ Página anterior") and st.session_state.pagina_atual > 0:
        st.session_state.pagina_atual -= 1
with col_nav2:
    if st.button("➡ Próxima página") and st.session_state.pagina_atual < total_paginas - 1:
        st.session_state.pagina_atual += 1

# Histórico local
if "historico" not in st.session_state:
    st.session_state.historico = []

# Subprocessos em execução (visível para todos enquanto o app roda)
if "execucoes_globais" not in st.session_state:
    st.session_state.execucoes_globais = set()

# Função para destacar linhas
def destacar_linhas_em_execucao(df):
    def cor_linha(row):
        if str(row["ID"]) in st.session_state.execucoes_globais:
            return ["background-color: #FFF3CD"] * len(row)
        else:
            return [""] * len(row)
    return df.style.apply(cor_linha, axis=1)

# Exibir sugestões
for i, bloco in enumerate(agrupamentos_pagina):
    indice_global = inicio + i
    st.subheader(f"Subprocesso sugerido {indice_global + 1}")
    st.dataframe(destacar_linhas_em_execucao(bloco))

    id_bloco = str(bloco["ID"].iloc[0])

    col1, col2 = st.columns(2)
    with col1:
        if id_bloco not in st.session_state.execucoes_globais:
            if st.button("❌ Marcar como em execução", key=f"executar_{indice_global}"):
                st.session_state.execucoes_globais.add(id_bloco)
                st.warning("Subprocesso marcado como em execução.")
        else:
            if st.button("🔓 Liberar execução", key=f"liberar_{indice_global}"):
                st.session_state.execucoes_globais.remove(id_bloco)
                st.info("Subprocesso liberado.")

    with col2:
        if st.button("✅ Marcar como executado", key=f"finalizar_{indice_global}"):
            registro = {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "fornecedor": bloco["FORNECEDOR"].iloc[0],
                "pag": bloco["PAG"].iloc[0],
                "ids": ", ".join(bloco["ID"].astype(str)),
                "valor_total": bloco["VALOR"].sum()
            }
            st.session_state.historico.append(registro)
            st.success("Subprocesso registrado no histórico!")
            if id_bloco in st.session_state.execucoes_globais:
                st.session_state.execucoes_globais.remove(id_bloco)

# Histórico lateral
st.sidebar.title("📋 Histórico de Subprocessos")
if st.session_state.historico:
    historico_df = pd.DataFrame(st.session_state.historico)
    st.sidebar.dataframe(historico_df)
else:
    st.sidebar.info("Nenhum subprocesso registrado ainda.")
