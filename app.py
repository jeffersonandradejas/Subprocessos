import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ===============================
# CONFIG
# ===============================
st.set_page_config("Subprocessos Inteligentes", layout="wide")

ARQUIVO_DADOS = "dados.json"
ITENS_POR_PAGINA = 8
ACOES_VALIDAS = ["ASSINAR OD", "ASSINAR CH"]

# ===============================
# PERSISTÊNCIA
# ===============================
def carregar_dados():
    if not os.path.exists(ARQUIVO_DADOS):
        dados_iniciais = {
            "usuarios": {
                "admin": {"senha": "", "tipo": "admin"}
            },
            "dados_planilha": [],
            "status_blocos": {},
            "historico": []
        }
        salvar_dados(dados_iniciais)
    with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

dados = carregar_dados()

# ===============================
# LOGIN
# ===============================
st.sidebar.title("👤 Login")

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if not st.session_state.usuario_logado:
    usuario = st.sidebar.text_input("Nome do usuário")
    senha = st.sidebar.text_input("Senha", type="password")
    entrar = st.sidebar.button("🔐 Entrar")

    if entrar:
        if usuario not in dados["usuarios"]:
            st.sidebar.error("Usuário não encontrado.")
            st.stop()

        senha_correta = dados["usuarios"][usuario]["senha"]

        if senha_correta != senha:
            st.sidebar.error("Senha incorreta.")
            st.stop()

        st.session_state.usuario_logado = usuario
        st.rerun()
else:
    usuario = st.session_state.usuario_logado
    tipo_usuario = dados["usuarios"][usuario]["tipo"]
    st.sidebar.success(f"Olá {usuario}!")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario_logado = None
        st.rerun()

# ===============================
# SE NÃO LOGADO
# ===============================
if not st.session_state.usuario_logado:
    st.info("Faça login para continuar.")
    st.stop()

tipo_usuario = dados["usuarios"][usuario]["tipo"]

# ===============================
# ADMIN — IMPORTAR CSV
# ===============================
if tipo_usuario == "admin":
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("📁 Importar CSV", type="csv")

    if arquivo:
        df = pd.read_csv(arquivo)
        df.columns = df.columns.str.strip()

        df = df[df["STATUS"].isin(ACOES_VALIDAS)]

        dados["dados_planilha"] = df.to_dict(orient="records")
        dados["status_blocos"] = {}
        salvar_dados(dados)

        st.sidebar.success("CSV importado e salvo!")

# ===============================
# SE NÃO HOUVER DADOS
# ===============================
if not dados["dados_planilha"]:
    st.info("Nenhum dado importado ainda.")
    st.stop()

df = pd.DataFrame(dados["dados_planilha"])

# ===============================
# AGRUPAMENTO
# ===============================
grupos = []
for fornecedor, g1 in df.groupby("FORNECEDOR"):
    for pag, g2 in g1.groupby("PAG"):
        blocos = [g2.iloc[i:i+9] for i in range(0, len(g2), 9)]
        grupos.extend(blocos)

total_paginas = (len(grupos) - 1) // ITENS_POR_PAGINA + 1

# ===============================
# PAGINAÇÃO NUMÉRICA
# ===============================
pagina = st.session_state.get("pagina", 1)

st.markdown("### 📌 Páginas")
cols = st.columns(min(total_paginas, 10))

for i in range(1, total_paginas + 1):
    status_pag = []
    for bloco in grupos[(i-1)*ITENS_POR_PAGINA:i*ITENS_POR_PAGINA]:
        idb = str(bloco["ID"].iloc[0])
        status_pag.append(dados["status_blocos"].get(idb, {}).get("status", "pendente"))

    if status_pag and all(s == "executado" for s in status_pag):
        cor = "🟢"
    elif any(s == "em_execucao" for s in status_pag):
        cor = "🟡"
    else:
        cor = "🔴"

    if cols[(i-1) % len(cols)].button(f"{cor} {i}"):
        st.session_state.pagina = i
        st.rerun()

inicio = (pagina - 1) * ITENS_POR_PAGINA
fim = inicio + ITENS_POR_PAGINA
blocos_pagina = grupos[inicio:fim]

st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

# ===============================
# BLOCOS
# ===============================
for bloco in blocos_pagina:
    id_bloco = str(bloco["ID"].iloc[0])
    status = dados["status_blocos"].get(id_bloco, {"status": "pendente"})

    if status["status"] == "executado":
        icone = "🟢"
    elif status["status"] == "em_execucao":
        icone = "🟡" if status.get("usuario") == usuario else "🔒"
    else:
        icone = "🔴"

    st.subheader(f"{icone} Subprocesso {id_bloco}")
    st.dataframe(bloco, use_container_width=True)

    c1, c2 = st.columns(2)

    if status["status"] == "pendente":
        if c1.button("▶ Iniciar", key=f"iniciar_{id_bloco}"):
            dados["status_blocos"][id_bloco] = {
                "status": "em_execucao",
                "usuario": usuario,
                "inicio": datetime.now().isoformat()
            }
            salvar_dados(dados)
            st.rerun()

    if status.get("usuario") == usuario and status["status"] == "em_execucao":
        if c2.button("✔ Finalizar", key=f"finalizar_{id_bloco}"):
            dados["status_blocos"][id_bloco]["status"] = "executado"
            dados["historico"].append({
                "id": id_bloco,
                "usuario": usuario,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salvar_dados(dados)
            st.rerun()

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
if dados["historico"]:
    st.sidebar.dataframe(pd.DataFrame(dados["historico"]))
else:
    st.sidebar.info("Nenhum subprocesso finalizado ainda.")
