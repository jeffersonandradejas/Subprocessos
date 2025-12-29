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
# SUPABASE CLIENT
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# USUÁRIOS FIXOS (pode migrar para tabela Supabase depois)
# ===============================
usuarios = {
    "admin": {"senha": "123", "tipo": "admin"},
    "sabrina": {"senha": "ladybinacs", "tipo": "usuario"},
}

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
        if usuario_input not in usuarios:
            st.sidebar.error("Usuário não encontrado.")
            st.stop()
        if usuarios[usuario_input]["senha"] != senha_input:
            st.sidebar.error("Senha incorreta.")
            st.stop()
        st.session_state.usuario_logado = usuario_input
        st.rerun()
else:
    usuario = st.session_state.usuario_logado
    tipo_usuario = usuarios[usuario]["tipo"]
    st.sidebar.success(f"Olá {usuario}!")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.usuario_logado = None
        st.rerun()

if not st.session_state.usuario_logado:
    st.info("Faça login para continuar.")
    st.stop()

usuario = st.session_state.usuario_logado
tipo_usuario = usuarios[usuario]["tipo"]

# ===============================
# ADMIN: IMPORTAR CSV UMA VEZ
# ===============================
if tipo_usuario == "admin":
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("📁 Importar CSV", type="csv")
    if arquivo:
        df_csv = pd.read_csv(arquivo)
        df_csv.columns = df_csv.columns.str.strip()
        df_csv = df_csv[df_csv["STATUS"].isin(ACOES_VALIDAS)]

        # Salvar no Supabase
        for _, row in df_csv.iterrows():
            supabase.table("subprocessos").upsert(row.to_dict()).execute()
        st.sidebar.success("CSV importado e salvo no Supabase!")

# ===============================
# CARREGAR DADOS
# ===============================
def carregar_dados():
    # Subprocessos
    res = supabase.table("subprocessos").select("*").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    # Status dos blocos
    res_status = supabase.table("status_blocos").select("*").execute()
    status_blocos = {str(r["id_bloco"]): r for r in res_status.data} if res_status.data else {}
    # Histórico
    res_hist = supabase.table("historico").select("*").execute()
    historico = res_hist.data if res_hist.data else []
    return df, status_blocos, historico

df, status_blocos, historico = carregar_dados()
if df.empty:
    st.warning("Nenhum subprocesso disponível. Admin deve importar CSV.")
    st.stop()

# ===============================
# AGRUPAMENTO INTELIGENTE
# ===============================
grupos = []
for fornecedor, g1 in df.groupby("FORNECEDOR"):
    for pag, g2 in g1.groupby("PAG"):
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
    status_pag = []
    for bloco in grupos[(i-1)*ITENS_POR_PAGINA:i*ITENS_POR_PAGINA]:
        idb = str(bloco["ID"].iloc[0])
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
    id_bloco = str(bloco["ID"].iloc[0])
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
            supabase.table("status_blocos").upsert({
                "id_bloco": id_bloco,
                "status": "executado",
                "usuario": usuario,
                "fim": datetime.now().isoformat()
            }).execute()
            supabase.table("historico").insert({
                "id_bloco": id_bloco,
                "usuario": usuario,
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
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

# ===============================
# EXPORTAR CSV ATUALIZADO
# ===============================
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.sidebar.download_button(
    label="📥 Baixar CSV atualizado",
    data=csv_bytes,
    file_name="subprocessos_atual.csv",
    mime="text/csv"
)
