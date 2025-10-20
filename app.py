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

# 📄 Paginação
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
    if st.button("⬅ Página anterior") and st.session_state.p
