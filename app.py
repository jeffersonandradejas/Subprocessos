import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# ---------------------------
# CONFIGURAÇÕES INICIAIS
# ---------------------------
st.set_page_config(page_title="Subprocessos Inteligentes", layout="wide")

# ---------------------------
# LOGIN DE USUÁRIO
# ---------------------------
if "usuarios" not in st.session_state:
    st.session_state.usuarios = {"admin": {"senha": "admin123", "admin": True}}

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if st.session_state.usuario_logado is None:
    st.subheader("👤 Nome do usuário")
    usuario_input = st.text_input("Usuário")
    senha_input = st.text_input("Senha", type="password")
    if st.button("Login"):
        user = st.session_state.usuarios.get(usuario_input)
        if user and user["senha"] == senha_input:
            st.session_state.usuario_logado = usuario_input
            st.success(f"Olá {usuario_input}! {'(Administrador)' if user['admin'] else ''}")
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha incorretos")
    st.stop()

# ---------------------------
# HISTÓRICO E STATUS GLOBAL
# ---------------------------
if "historico" not in st.session_state:
    st.session_state.historico = []

if "status_global" not in st.session_state:
    st.session_state.status_global = {}

# ---------------------------
# IMPORTAÇÃO DE DADOS
# ---------------------------
st.subheader("📥 Importar dados da planilha")

metodo_importacao = st.radio("Escolha o método de importação:", ["📋 Colar dados", "📁 Importar CSV"])

df = pd.DataFrame()  # Inicialização vazia

if metodo_importacao == "📋 Colar dados":
    dados_colados = st.text_area("Cole os dados da planilha aqui (separados por tabulação)", height=500)
    if dados_colados:
        try:
            linhas_split = [linha.strip().split("\t") for linha in dados_colados.strip().split("\n")]
            num_cols = max(len(linha) for linha in linhas_split)
            linhas_corrigidas = [
                linha + [""]*(num_cols - len(linha)) if len(linha) < num_cols else linha[:num_cols]
                for linha in linhas_split
            ]
            df = pd.DataFrame(linhas_corrigidas[1:], columns=linhas_corrigidas[0])
            st.success("✅ Dados processados com sucesso!")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Erro ao processar os dados: {e}")

elif metodo_importacao == "📁 Importar CSV":
    arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
    if arquivo is not None:
        try:
            df = pd.read_csv(arquivo)
            st.success("✅ CSV importado com sucesso!")
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Erro ao processar o CSV: {e}")

# ---------------------------
# CONFIGURAÇÃO DE BLOCOS
# ---------------------------
if not df.empty:
    # Inicializa status global
    for idx, row in df.iterrows():
        id_bloco = str(row.get("ID", idx))
        if id_bloco not in st.session_state.status_global:
            st.session_state.status_global[id_bloco] = row.get("STATUS", "")

    # Destacar linhas de acordo com status
    def destacar_linhas_em_execucao(df):
        def cor_linha(row):
            id_linha = str(row.get("ID"))
            status = st.session_state.status_global.get(id_linha, "")
            if status == "em execução":
                return ["background-color: #FFF3CD"] * len(row)
            elif status == "executado":
                return ["background-color: #E0E0E0"] * len(row)
            else:
                return [""] * len(row)
        return df.style.apply(cor_linha, axis=1)

    # Agrupamento por FORNECEDOR e PAG
    agrupamentos = []
    for _, grupo in df.groupby(["FORNECEDOR", "PAG"]):
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

    # Exibir blocos
    sugestoes_visiveis = 0
    for i, bloco in enumerate(agrupamentos_pagina):
        indice_global = inicio + i
        id_bloco = str(bloco["ID"].iloc[0])

        if st.session_state.status_global.get(id_bloco) == "executado":
            continue

        sugestoes_visiveis += 1
        st.subheader(f"Subprocesso sugerido {indice_global + 1}")
        st.dataframe(destacar_linhas_em_execucao(bloco))

        col1, col2 = st.columns(2)
        with col1:
            status_atual = st.session_state.status_global.get(id_bloco)
            texto_botao = "🔓 Liberar execução" if status_atual == "em execução" else "❌ Marcar como em execução"
            if st.button(texto_botao, key=f"execucao_{indice_global}"):
                novo_status = "" if status_atual == "em execução" else "em execução"
                st.session_state.status_global[id_bloco] = novo_status
                st.experimental_rerun()

        with col2:
            if st.button("✔ Marcar como executado", key=f"finalizar_{indice_global}"):
                fornecedor = bloco["FORNECEDOR"].iloc[0]
                pag = bloco["PAG"].iloc[0]
                valor = bloco.get("VALOR", pd.Series([0])).apply(lambda x: float(str(x).replace("R$", "").replace(".", "").replace(",", "."))).sum()

                st.session_state.status_global[id_bloco] = "executado"
                st.session_state.historico.append({
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "fornecedor": fornecedor,
                    "pag": pag,
                    "ids": id_bloco,
                    "valor_total": valor
                })
                st.experimental_rerun()

    if sugestoes_visiveis == 0:
        st.info("✅ Nenhuma sugestão restante nesta página.")

    # Navegação
    st.write(f"📄 Página {st.session_state.pagina_atual + 1} de {total_paginas}")
    col_nav1, col_nav2 = st.columns([1, 1])
    if col_nav1.button("⬅ Página anterior") and st.session_state.pagina_atual > 0:
        st.session_state.pagina_atual -= 1
        st.experimental_rerun()
    if col_nav2.button("➡ Próxima página") and st.session_state.pagina_atual < total_paginas - 1:
        st.session_state.pagina_atual += 1
        st.experimental_rerun()

# ---------------------------
# HISTÓRICO LATERAL
# ---------------------------
st.sidebar.title("📋 Histórico de Subprocessos")
if st.session_state.historico:
    historico_df = pd.DataFrame(st.session_state.historico)
    st.sidebar.dataframe(historico_df)
else:
    st.sidebar.info("Nenhum subprocesso registrado ainda.")
