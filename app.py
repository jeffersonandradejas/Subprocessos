import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- Função para carregar dados persistentes ---
def carregar_dados():
    dados_iniciais = {
        "usuarios": {
            "admin": {"senha": "123", "tipo": "admin"},
            "sabrina": {"senha": "ladybinacs", "tipo": "usuario"}
        },
        "dados_planilha": [],
        "status_blocos": {},
        "historico": []
    }

    if not os.path.exists("dados.json"):
        with open("dados.json", "w", encoding="utf-8") as f:
            json.dump(dados_iniciais, f, ensure_ascii=False, indent=2)

    with open("dados.json", "r", encoding="utf-8") as f:
        return json.load(f)

# --- Função para salvar dados ---
def salvar_dados(dados):
    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# --- Inicialização ---
st.set_page_config(page_title="Subprocessos Inteligentes", layout="wide")

if "dados" not in st.session_state:
    st.session_state.dados = carregar_dados()

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = 1

# --- Tela de login ---
if st.session_state.usuario_logado is None:
    st.title("🔒 Login")
    usuario = st.text_input("Nome do usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        dados = st.session_state.dados
        if usuario in dados["usuarios"]:
            if dados["usuarios"][usuario]["senha"] == senha:
                st.session_state.usuario_logado = usuario
                st.success(f"Olá {usuario}!")
            else:
                st.error("Senha incorreta")
        else:
            st.error("Usuário não encontrado")
    st.stop()

# --- Tela principal ---
st.sidebar.title(f"👤 Usuário: {st.session_state.usuario_logado}")
st.sidebar.button("Sair e salvar", on_click=lambda: salvar_dados(st.session_state.dados))

st.title("📌 Subprocessos Inteligentes Offline/Online")

# --- Upload CSV ---
arquivo_csv = st.file_uploader("📥 Carregar planilha CSV", type=["csv"])
if arquivo_csv:
    df = pd.read_csv(arquivo_csv)
    df.columns = df.columns.str.strip()
    # Filtra apenas ASSINAR OD e ASSINAR CH
    df = df[df["STATUS"].isin(["ASSINAR OD", "ASSINAR CH"])]
    st.session_state.dados["dados_planilha"] = df.to_dict(orient="records")
    salvar_dados(st.session_state.dados)
else:
    # Se já temos dados carregados, usa eles
    if st.session_state.dados["dados_planilha"]:
        df = pd.DataFrame(st.session_state.dados["dados_planilha"])
    else:
        st.info("📄 Carregue uma planilha CSV para começar")
        st.stop()

# --- Agrupamento por fornecedor ou PAG ---
blocos = []
for _, grupo in df.groupby(["FORNECEDOR", "PAG"]):
    blocos.extend([grupo.iloc[i:i+9] for i in range(0, len(grupo), 9)])

total_paginas = len(blocos)
pagina_atual = st.session_state.pagina_atual

# --- Função para renderizar cores por status ---
def cor_linha(row):
    bloco_id = str(row.name)
    status = st.session_state.dados["status_blocos"].get(bloco_id, "")
    if status == "executado":
        return ["background-color: #E0E0E0"] * len(row)
    elif status == "em execução":
        return ["background-color: #FFF3CD"] * len(row)
    else:
        return [""] * len(row)

# --- Paginação numerada ---
st.write("📄 Páginas:")
col_pag = st.columns(total_paginas)
for i, col in enumerate(col_pag, start=1):
    status_pagina = all(
        st.session_state.dados["status_blocos"].get(str(blocos[i-1].index[0]), "") == "executado"
        for idx in range(len(blocos[i-1]))
    )
    cor_botao = "green" if status_pagina else None
    if col.button(f"{i}", key=f"pagina_{i}", help="Clique para ir para a página", use_container_width=True):
        st.session_state.pagina_atual = i
        st.experimental_rerun()

# --- Bloco atual ---
bloco = blocos[pagina_atual - 1]
st.subheader(f"Bloco {pagina_atual}")

st.dataframe(bloco.style.apply(cor_linha, axis=1), use_container_width=True)

# --- Botões de execução ---
col1, col2 = st.columns(2)
bloco_id = str(bloco.index[0])

with col1:
    if st.button("❌ Marcar em execução"):
        st.session_state.dados["status_blocos"][bloco_id] = "em execução"
        salvar_dados(st.session_state.dados)
        st.experimental_rerun()

with col2:
    if st.button("✔ Marcar como executado"):
        st.session_state.dados["status_blocos"][bloco_id] = "executado"
        # Salva histórico
        st.session_state.dados["historico"].append({
            "usuario": st.session_state.usuario_logado,
            "bloco": bloco_id,
            "fornecedor": bloco["FORNECEDOR"].iloc[0],
            "pag": bloco["PAG"].iloc[0],
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        })
        salvar_dados(st.session_state.dados)
        st.experimental_rerun()

# --- Histórico lateral ---
st.sidebar.title("🗓 Histórico de Subprocessos")
if st.session_state.dados["historico"]:
    st.sidebar.dataframe(pd.DataFrame(st.session_state.dados["historico"]))
else:
    st.sidebar.info("Nenhum subprocesso registrado ainda.")
