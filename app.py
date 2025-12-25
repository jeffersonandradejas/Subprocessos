import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# ------------------ Funções de Persistência ------------------ #
ARQUIVO_DADOS = "dados.json"

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        # Dados iniciais com usuários padrão
        dados_iniciais = {
            "usuarios": {
                "admin": {"senha": "123", "tipo": "admin"},
                "sabrina": {"senha": "ladybinacs", "tipo": "usuario"}
            },
            "status_blocos": {},
            "historico": [],
            "pagina_atual": 0
        }
        salvar_dados(dados_iniciais)
        return dados_iniciais

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# ------------------ Funções Auxiliares ------------------ #
def filtrar_blocos(df):
    return df[df["STATUS"].isin(["ASSINAR OD", "ASSINAR CH"])]

def destacar_linhas(row):
    status = dados["status_blocos"].get(str(row["ID"]), "")
    if status == "em execução":
        return ["background-color: #FFF3CD"] * len(row)
    elif status == "executado":
        return ["background-color: #E0E0E0"] * len(row)
    else:
        return [""] * len(row)

# ------------------ Carregamento e Login ------------------ #
st.title("📌 Subprocessos Inteligentes Offline/Online")

# Carrega dados persistentes
dados = carregar_dados()

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.subheader("👤 Login")
    usuario = st.text_input("Nome do usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario in dados["usuarios"] and dados["usuarios"][usuario]["senha"] == senha:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.success(f"Olá {usuario}! ({dados['usuarios'][usuario]['tipo'].capitalize()})")
        else:
            st.error("Usuário ou senha incorretos.")
else:
    st.sidebar.write(f"👤 Usuário logado: **{st.session_state.usuario}**")
    
    # ------------------ Upload CSV ------------------ #
    uploaded_file = st.file_uploader("📥 Importar CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()
        df = filtrar_blocos(df)
        st.session_state.df = df
        st.success("CSV carregado e filtrado!")

    if "df" in st.session_state:
        df = st.session_state.df
        
        # ------------------ Agrupamento por empresa e PAG ------------------ #
        agrupamentos = []
        for _, grupo in df.groupby(["FORNECEDOR", "PAG"]):
            blocos = [grupo.iloc[i:i+9] for i in range(0, len(grupo), 9)]
            agrupamentos.extend(blocos)
        
        total_paginas = len(agrupamentos)
        
        if "pagina_atual" not in st.session_state:
            st.session_state.pagina_atual = dados.get("pagina_atual", 0)
        
        # ------------------ Paginação com números ------------------ #
        st.subheader("📄 Blocos")
        paginas_col = st.columns(total_paginas)
        for i in range(total_paginas):
            cor_botao = "green" if all(str(bloco["ID"].iloc[0]) in dados["status_blocos"] and
                                       dados["status_blocos"][str(bloco["ID"].iloc[0])] == "executado"
                                       for bloco in [agrupamentos[i]]) else "lightgrey"
            if paginas_col[i].button(f"{i+1}", key=f"pagina_{i}", help="Clique para ir para esta página"):
                st.session_state.pagina_atual = i
                dados["pagina_atual"] = i
                salvar_dados(dados)
        
        # ------------------ Mostrar blocos da página atual ------------------ #
        bloco_atual = agrupamentos[st.session_state.pagina_atual]
        st.dataframe(bloco_atual.style.apply(destacar_linhas, axis=1), use_container_width=True)
        
        # ------------------ Botões de execução ------------------ #
        col1, col2 = st.columns(2)
        id_bloco = str(bloco_atual["ID"].iloc[0])
        with col1:
            if st.button("❌ Marcar como em execução"):
                dados["status_blocos"][id_bloco] = "em execução"
                salvar_dados(dados)
                st.experimental_rerun()
        with col2:
            if st.button("✔ Marcar como executado"):
                dados["status_blocos"][id_bloco] = "executado"
                dados["historico"].append({
                    "usuario": st.session_state.usuario,
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "fornecedor": bloco_atual["FORNECEDOR"].iloc[0],
                    "PAG": bloco_atual["PAG"].iloc[0],
                    "ID": id_bloco
                })
                salvar_dados(dados)
                st.experimental_rerun()
        
        # ------------------ Histórico lateral ------------------ #
        st.sidebar.title("🗓 Histórico de Subprocessos")
        if dados["historico"]:
            historico_df = pd.DataFrame(dados["historico"])
            st.sidebar.dataframe(historico_df)
        else:
            st.sidebar.info("Nenhum subprocesso registrado ainda.")
        
        # ------------------ Botão sair ------------------ #
        if st.sidebar.button("🚪 Sair da sessão"):
            st.session_state.logado = False
            salvar_dados(dados)
            st.experimental_rerun()
