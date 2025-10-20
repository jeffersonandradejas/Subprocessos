import pandas as pd
import streamlit as st
from datetime import datetime

# URLs da planilha principal e da aba Executados
url_dados = "https://docs.google.com/spreadsheets/d/1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ/export?format=csv"
url_executados = "https://docs.google.com/spreadsheets/d/1o2Z-9t0zVCklB5rkeIOo5gCaSO1BwlrxKXTZv2sR4OQ/export?format=csv&gid=123456789"  # substitua pelo GID da aba Executados

# Carregar dados principais
@st.cache_data
def carregar_planilha():
    df = pd.read_csv(url_dados)
    df.columns = df.columns.str.strip()
    return df

# Carregar subprocessos já executados
@st.cache_data
def carregar_executados():
    try:
        df_exec = pd.read_csv(url_executados)
        df_exec.columns = df_exec.columns.str.strip()
        return set(df_exec["ID"].astype(str).tolist())
    except:
        return set()

df = carregar_planilha()
ids_executados = carregar_executados()

st.title("📄 Subprocessos Inteligentes")
st.write("Planilha carregada com sucesso!")

# ✅ Filtro robusto: ignora cancelado e enviado ACI sem alterar os dados originais
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

# Subprocessos em execução (visível para todos enquanto o app estiver rodando)
if "execucoes_globais" not in st.session_state:
    st.session_state.execucoes_globais = set()

# Função para destacar linhas
def destacar_linhas_em_execucao(df):
    def cor_linha(row):
        id_linha = str(row["ID"])
        if id_linha in st.session_state.execucoes_globais:
            return ["background-color: #FFF3CD"] * len(row)
        elif id_linha in ids_executados:
            return ["background-color: #E0E0E0"] * len(row)  # cinza para executados
        else:
            return [""] * len(row)
    return df.style.apply(cor_linha, axis=1)

# Exibir sugestões da página atual
sugestoes_visiveis = 0
for i, bloco in enumerate(agrupamentos_pagina):
    indice_global = inicio + i
    id_bloco = str(bloco["ID"].iloc[0])

    # Pular se já foi executado
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
            registro = {
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "fornecedor": bloco["FORNECEDOR"].iloc[0],
                "pag": bloco["PAG"].iloc[0],
                "ids": ", ".join(bloco["ID"].astype(str)),
                "valor_total": bloco["VALOR"].sum()
            }
            st.session_state.historico.append(registro)
            st.success("Subprocesso registrado como executado!")
            st.info("⚠️ Para que esse registro seja visível para todos, ele precisa ser salvo na aba 'Executados'.")

# ✅ Navegação de página no final com clique único
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
