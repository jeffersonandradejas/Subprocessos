import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import os

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config("Subprocessos Inteligentes", layout="wide")

# ===============================
# SUPABASE CLIENT
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ACOES_VALIDAS = ["ASSINAR OD", "ASSINAR CH"]
ITENS_POR_PAGINA = 8

# ===============================
# FUNÇÃO DE CARREGAR DADOS
# ===============================
def carregar_dados():
    # Subprocessos
    res_sub = supabase.table("subprocessos").select("*").execute()
    subprocessos = res_sub.data or []

    # Status blocos
    res_status = supabase.table("status_blocos").select("*").execute()
    status_blocos = {s['id_bloco']: s for s in (res_status.data or [])}

    # Histórico
    res_hist = supabase.table("historico_execucao").select("*").execute()
    historico = res_hist.data or []

    return subprocessos, status_blocos, historico

# ===============================
# LOGIN
# ===============================
st.sidebar.title("👤 Login")

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if not st.session_state.usuario_logado:
    usuario_input = st.sidebar.text_input("Nome do usuário")
    senha_input = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("🔐 Entrar"):
        res_user = supabase.table("usuarios").select("*").eq("usuario", usuario_input).execute()
        usuario_data = res_user.data[0] if res_user.data else None

        if not usuario_data:
            st.sidebar.error("Usuário não encontrado.")
            st.stop()
        if usuario_data["senha"] != senha_input:
            st.sidebar.error("Senha incorreta.")
            st.stop()

        st.session_state.usuario_logado = usuario_input
        st.rerun()
else:
    usuario = st.session_state.usuario_logado
    res_user = supabase.table("usuarios").select("*").eq("usuario", usuario).execute()
    tipo_usuario = res_user.data[0]["tipo"]
    st.sidebar.success(f"Olá {usuario}!")

    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario_logado = None
        st.rerun()

# ===============================
# BLOQUEIA ACESSO SEM LOGIN
# ===============================
if not st.session_state.usuario_logado:
    st.info("Faça login para continuar.")
    st.stop()

usuario = st.session_state.usuario_logado

# ===============================
# ADMIN — IMPORTAR CSV
# ===============================
if tipo_usuario == "admin":
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("📁 Importar CSV", type="csv")

    if arquivo:
        df_csv = pd.read_csv(arquivo)
        df_csv.columns = df_csv.columns.str.strip()

        # Filtra apenas status válidos
        df_csv = df_csv[df_csv["STATUS"].isin(ACOES_VALIDAS)]

        # Substitui NaN/NaT por None
        df_csv = df_csv.where(pd.notnull(df_csv), None)

        # Insere no Supabase
        for _, row in df_csv.iterrows():
            dados_dict = {k.lower(): (v if pd.notnull(v) else None) for k, v in row.items()}
            supabase.table("subprocessos").insert({
                "id_bloco": str(dados_dict.get("id")),
                "fornecedor": dados_dict.get("fornecedor"),
                "pag": str(dados_dict.get("pag")),
                "dados": dados_dict
            }).execute()
        st.sidebar.success("CSV importado com sucesso!")
        st.rerun()

# ===============================
# CARREGAR DADOS ATUALIZADOS
# ===============================
subprocessos, status_blocos, historico = carregar_dados()

if not subprocessos:
    st.warning("Nenhum subprocesso disponível. Admin deve importar CSV.")
    st.stop()

df = pd.DataFrame(subprocessos)

# ===============================
# AGRUPAMENTO INTELIGENTE
# ===============================
grupos = []
for fornecedor, g1 in df.groupby("fornecedor"):
    for pag, g2 in g1.groupby("pag"):
        blocos = [g2.iloc[i:i+9] for i in range(0, len(g2), 9)]
        grupos.extend(blocos)

total_paginas = max(1, (len(grupos) - 1) // ITENS_POR_PAGINA + 1)

# ===============================
# PAGINAÇÃO
# ===============================
pagina = st.session_state.get("pagina", 1)
st.markdown("### 📌 Páginas")
cols = st.columns(min(total_paginas, 10))

for i in range(1, total_paginas + 1):
    status_pag = []
    for bloco in grupos[(i-1)*ITENS_POR_PAGINA:i*ITENS_POR_PAGINA]:
        idb = str(bloco["id"].iloc[0])
        status_pag.append(status_blocos.get(idb, {}).get("status", "pendente"))

    if status_pag and all(s == "executado" for s in status_pag):
        icone = "🟢"
    elif any(s == "em_execucao" for s in status_pag):
        icone = "🟡"
    else:
        icone = "🔴"

    if cols[(i-1) % len(cols)].button(f"{icone} {i}"):
        st.session_state.pagina = i
        st.rerun()

inicio = (pagina - 1) * ITENS_POR_PAGINA
fim = inicio + ITENS_POR_PAGINA
blocos_pagina = grupos[inicio:fim]

st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

# ===============================
# EXIBIÇÃO DOS BLOCOS
# ===============================
for bloco in blocos_pagina:
    id_bloco = str(bloco["id"].iloc[0])
    status = status_blocos.get(id_bloco, {"status": "pendente"})

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
        if c1.button("▶ Iniciar execução", key=f"iniciar_{id_bloco}"):
            supabase.table("status_blocos").upsert({
                "id_bloco": id_bloco,
                "status": "em_execucao",
                "usuario": usuario,
                "inicio": datetime.now().isoformat()
            }).execute()
            st.rerun()

    if status.get("usuario") == usuario and status["status"] == "em_execucao":
        if c2.button("✔ Finalizar execução", key=f"finalizar_{id_bloco}"):
            supabase.table("status_blocos").update({
                "status": "executado"
            }).eq("id_bloco", id_bloco).execute()
            supabase.table("historico_execucao").insert({
                "id_bloco": id_bloco,
                "usuario": usuario,
                "data_execucao": datetime.now().isoformat()
            }).execute()
            st.rerun()

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
if historico:
    st.sidebar.dataframe(pd.DataFrame(historico))
else:
    st.sidebar.info("Nenhum subprocesso executado ainda.")
