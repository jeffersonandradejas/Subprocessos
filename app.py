import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# ===============================
# CONFIGURAÇÃO
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
# LOGIN (usuarios no Supabase)
# ===============================
st.sidebar.title("👤 Login")

if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

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

# ===============================
# CARREGAR SUBPROCESSOS (SUPABASE)
# ===============================
res = supabase.table("subprocessos").select("*").execute()
if not res.data:
    st.error("⚠️ Nenhum subprocesso encontrado no banco.")
    st.stop()

df = pd.DataFrame(res.data)

# ===============================
# AGRUPAMENTO (FORNECEDOR / PAG)
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
        st.session_state.pagina = i
        st.rerun()

inicio = (pagina - 1) * ITENS_POR_PAGINA
fim = inicio + ITENS_POR_PAGINA

# ===============================
# STATUS ATUAL
# ===============================
resres_status = supabase.table("status_blocos").select("*").execute()
status_blocos = {r["id_bloco"]: r for r in (res_status.data or [])}

# ===============================
# EXIBIÇÃO
# ===============================
for bloco in grupos[inicio:fim]:
    id_bloco = bloco["id_bloco"].iloc[0]
    status = status_blocos.get(id_bloco, {"status": "pendente"})

    icone = "🔴"
    if status["status"] == "em_execucao":
        icone = "🟡"
    elif status["status"] == "executado":
        icone = "🟢"

    st.subheader(f"{icone} Subprocesso {id_bloco}")
    st.dataframe(bloco, use_container_width=True)

    c1, c2 = st.columns(2)

    if status["status"] == "pendente":
        if c1.button("▶ Iniciar", key=f"in_{id_bloco}"):
            supabase.table("status_blocos").upsert({
                "id_bloco": id_bloco,
                "status": "em_execucao",
                "usuario": usuario,
                "inicio": datetime.utcnow().isoformat()
            }).execute()
            st.rerun()

    if status["status"] == "em_execucao" and status.get("usuario") == usuario:
        if c2.button("✔ Finalizar", key=f"fim_{id_bloco}"):
            supabase.table("status_blocos").upsert({
                "id_bloco": id_bloco,
                "status": "executado",
                "usuario": usuario
            }).execute()

            supabase.table("historico_execucao").insert({
                "id_bloco": id_bloco,
                "usuario": usuario
            }).execute()

            st.rerun()

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
hist = supabase.table("historico_execucao").select("*").order("data_execucao", desc=True).execute()
if hist.data:
    st.sidebar.dataframe(pd.DataFrame(hist.data))
else:
    st.sidebar.info("Sem histórico")
