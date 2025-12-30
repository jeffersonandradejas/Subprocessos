import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# ===============================
# CONFIG
# ===============================
st.set_page_config("Subprocessos Inteligentes", layout="wide")
ITENS_POR_PAGINA = 8

# ===============================
# SUPABASE
# ===============================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ===============================
# LOGIN
# ===============================
st.sidebar.title("👤 Login")

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
    st.session_state.tipo_usuario = None

if not st.session_state.usuario_logado:
    usuario = st.sidebar.text_input("Usuário")
    senha = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        res = (
            supabase.table("usuarios")
            .select("*")
            .eq("usuario", usuario)
            .eq("senha", senha)
            .execute()
        )

        if not res.data:
            st.sidebar.error("Usuário ou senha inválidos")
            st.stop()

        st.session_state.usuario_logado = usuario
        st.session_state.tipo_usuario = res.data[0]["tipo"]
        st.rerun()
else:
    st.sidebar.success(f"Olá {st.session_state.usuario_logado}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

if not st.session_state.usuario_logado:
    st.stop()

usuario = st.session_state.usuario_logado
tipo_usuario = st.session_state.tipo_usuario

# ===============================
# ADMIN — IMPORTAÇÃO CSV (UMA VEZ)
# ===============================
res_check = supabase.table("subprocessos").select("id").limit(1).execute()
tem_dados = bool(res_check.data)

if tipo_usuario == "admin" and not tem_dados:
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("📁 Importar CSV (apenas uma vez)", type="csv")

    if arquivo:
        df_csv = pd.read_csv(arquivo)
        df_csv.columns = df_csv.columns.str.lower().str.strip()

        for _, row in df_csv.iterrows():
            supabase.table("subprocessos").insert({
                "id_bloco": str(row.get("id")),
                "fornecedor": row.get("fornecedor"),
                "pag": str(row.get("pag")),
                "dados": row.to_dict()
            }).execute()

        st.success("✅ CSV importado com sucesso. Nunca mais será necessário importar.")
        st.rerun()

# ===============================
# CARREGAR SUBPROCESSOS
# ===============================
res = supabase.table("subprocessos").select("*").execute()

if not res.data:
    st.warning("Nenhum subprocesso disponível.")
    st.stop()

df = pd.DataFrame(res.data)

# ===============================
# AGRUPAMENTO
# ===============================
grupos = []
for fornecedor, g1 in df.groupby("fornecedor"):
    for pag, g2 in g1.groupby("pag"):
        blocos = [g2.iloc[i:i+9] for i in range(0, len(g2), 9)]
        grupos.extend(blocos)

total_paginas = max(1, (len(grupos) - 1) // ITENS_POR_PAGINA + 1)
pagina = st.session_state.get("pagina", 1)

# ===============================
# PAGINAÇÃO
# ===============================
st.markdown("### 📌 Páginas")
cols = st.columns(min(total_paginas, 10))

for i in range(1, total_paginas + 1):
    if cols[(i-1) % len(cols)].button(str(i)):
        st
