import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# ---------------------------
# Configurações iniciais
# ---------------------------
st.set_page_config(page_title="Subprocessos Inteligentes", layout="wide")
st.title("📌 Subprocessos Inteligentes Offline/Online")

# ---------------------------
# Pasta de dados e usuários
# ---------------------------
if not os.path.exists("dados.json"):
    with open("dados.json", "w") as f:
        json.dump({"usuarios": {"admin": {"senha": "", "tipo": "admin"}}, "subprocessos": []}, f)

with open("dados.json", "r") as f:
    dados = json.load(f)

# ---------------------------
# Login
# ---------------------------
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if st.session_state.usuario is None:
    st.subheader("👤 Login")
    nome = st.text_input("Nome do usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if nome in dados["usuarios"]:
            st.session_state.usuario = nome
            st.success(f"Olá {nome}!")
        else:
            st.error("Usuário não encontrado!")
    st.stop()

# ---------------------------
# Admin: cadastro de usuários
# ---------------------------
if st.session_state.usuario == "admin":
    st.sidebar.subheader("⚙️ Configuração de Usuários")
    novo_usuario = st.sidebar.text_input("Nome do novo usuário")
    if st.sidebar.button("➕ Adicionar usuário"):
        if novo_usuario and novo_usuario not in dados["usuarios"]:
            dados["usuarios"][novo_usuario] = {"senha": "", "tipo": "user"}
            with open("dados.json", "w") as f:
                json.dump(dados, f, indent=4)
            st.sidebar.success(f"Usuário {novo_usuario} criado!")
        elif novo_usuario in dados["usuarios"]:
            st.sidebar.error("Usuário já existe!")

# ---------------------------
# Importação de dados
# ---------------------------
st.subheader("📥 Importar dados da planilha")

# Importar CSV
arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
if arquivo is not None:
    try:
        df = pd.read_csv(arquivo)
        st.session_state.df = df
        st.success("✅ CSV importado com sucesso!")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Erro ao processar o CSV: {e}")

# Colar dados
dados_colados = st.text_area("Ou cole os dados (separados por tabulação)", height=300)
if dados_colados:
    try:
        df = pd.read_csv(pd.io.common.StringIO(dados_colados), sep="\t", engine="python")
        st.session_state.df = df
        st.success("✅ Dados colados com sucesso!")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Erro ao processar os dados colados: {e}")

# ---------------------------
# Processamento dos subprocessos
# ---------------------------
if "df" in st.session_state:
    df = st.session_state.df

    # Histórico local
    if "historico" not in st.session_state:
        st.session_state.historico = []

    # Mostrar histórico
    st.sidebar.title("🗓 Histórico de Subprocessos")
    if st.session_state.historico:
        historico_df = pd.DataFrame(st.session_state.historico)
        st.sidebar.dataframe(historico_df)
    else:
        st.sidebar.info("Nenhum subprocesso registrado ainda.")

    # Paginação simples
    blocos = [df.iloc[i:i+5] for i in range(0, len(df), 5)]
    if "pagina_atual" not in st.session_state:
        st.session_state.pagina_atual = 0

    total_paginas = len(blocos)
    inicio = st.session_state.pagina_atual
    st.write(f"📄 Blocos Página {inicio + 1} / {total_paginas}")

    bloco = blocos[inicio]
    st.dataframe(bloco, use_container_width=True)

    # Marcar como executado
    if st.button("✔ Marcar este bloco como executado"):
        ids_bloco = bloco["ID"].tolist() if "ID" in bloco.columns else list(range(len(bloco)))
        st.session_state.historico.append({
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "usuario": st.session_state.usuario,
            "ids": ids_bloco,
            "valor_total": bloco["VALOR"].sum() if "VALOR" in bloco.columns else 0
        })
        st.success("✅ Bloco registrado no histórico!")

    # Navegação
    col1, col2 = st.columns(2)
    if col1.button("⬅ Página anterior") and st.session_state.pagina_atual > 0:
        st.session_state.pagina_atual -= 1
    if col2.button("➡ Próxima página") and st.session_state.pagina_atual < total_paginas - 1:
        st.session_state.pagina_atual += 1
