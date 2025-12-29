import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config("Subprocessos Inteligentes", layout="wide")

ITENS_POR_PAGINA = 8
ACOES_VALIDAS = ["ASSINAR OD", "ASSINAR CH"]

# ===============================
# CONEXÃO COM SUPABASE
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        usuario = (
            supabase.table("usuarios")
            .select("*")
            .eq("usuario", usuario_input)
            .execute()
        )
        if not usuario.data:
            st.sidebar.error("Usuário não encontrado.")
            st.stop()

        if usuario.data[0]["senha"] != senha_input:
            st.sidebar.error("Senha incorreta.")
            st.stop()

        st.session_state.usuario_logado = usuario_input
        st.rerun()
else:
    usuario = st.session_state.usuario_logado
    tipo_usuario = (
        supabase.table("usuarios")
        .select("tipo")
        .eq("usuario", usuario)
        .execute()
    ).data[0]["tipo"]
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
tipo_usuario = (
    supabase.table("usuarios")
    .select("tipo")
    .eq("usuario", usuario)
    .execute()
).data[0]["tipo"]

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

        # Apaga subprocessos antigos
        supabase.table("subprocessos").delete().neq("id", 0).execute()
        supabase.table("status_blocos").delete().neq("id_bloco", "").execute()
        supabase.table("historico_execucao").delete().neq("id", 0).execute()

        # Insere novos subprocessos
        for _, row in df.iterrows():
            dados = row.to_dict()
            id_bloco = str(dados["ID"])
            supabase.table("subprocessos").insert({
                "id_bloco": id_bloco,
                "fornecedor": dados["FORNECEDOR"],
                "pag": dados["PAG"],
                "dados": dados
            }).execute()
        st.sidebar.success("CSV importado com sucesso!")

# ===============================
# CARREGAR SUBPROCESSOS
# ===============================
subprocessos_resp = supabase.table("subprocessos").select("*").execute()
if not subprocessos_resp.data:
    st.warning("Nenhum CSV importado ainda.")
    st.stop()

df = pd.DataFrame([s["dados"] for s in subprocessos_resp.data])

# ===============================
# AGRUPAMENTO INTELIGENTE
# ===============================
grupos = []
for fornecedor, g1 in df.groupby("FORNECEDOR"):
    for pag, g2 in g1.groupby("PAG"):
        blocos = [g2.iloc[i:i+9] for i in range(0, len(g2), 9)]
        grupos.extend(blocos)

total_paginas = max(1, (len(grupos) - 1) // ITENS_POR_PAGINA + 1)

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
        status_resp = supabase.table("status_blocos").select("*").eq("id_bloco", idb).execute()
        status_pag.append(status_resp.data[0]["status"] if status_resp.data else "pendente")

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
    id_bloco = str(bloco["ID"].iloc[0])
    status_resp = supabase.table("status_blocos").select("*").eq("id_bloco", id_bloco).execute()
    status = status_resp.data[0] if status_resp.data else {"status": "pendente"}

    if status["status"] == "executado":
        icone = "🟢"
    elif status["status"] == "em_execucao":
        icone = "🟡" if status.get("usuario") == usuario else "🔒"
    else:
        icone = "🔴"

    st.subheader(f"{icone} Subprocesso {id_bloco}")
    st.dataframe(bloco, use_container_width=True)

    c1, c2 = st.columns(2)

    # Iniciar execução
    if status["status"] == "pendente":
        if c1.button("▶ Iniciar execução", key=f"iniciar_{id_bloco}"):
            supabase.table("status_blocos").upsert({
                "id_bloco": id_bloco,
                "status": "em_execucao",
                "usuario": usuario,
                "inicio": datetime.now().isoformat()
            }).execute()
            st.rerun()

    # Finalizar execução
    if status.get("usuario") == usuario and status["status"] == "em_execucao":
        if c2.button("✔ Finalizar execução", key=f"finalizar_{id_bloco}"):
            supabase.table("status_blocos").update({"status": "executado"}).eq("id_bloco", id_bloco).execute()
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
historico_resp = supabase.table("historico_execucao").select("*").execute()
if historico_resp.data:
    st.sidebar.dataframe(pd.DataFrame(historico_resp.data))
else:
    st.sidebar.info("Nenhum subprocesso executado ainda.")
