import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ===============================
# FUNÇÃO PARA PARSEAR NÚMEROS
# ===============================
def parse_int(valor):
    try:
        if valor is None:
            return None
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None

# ===============================
# CONFIGURAÇÃO SUPABASE
# ===============================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ACOES_VALIDAS = ["ASSINAR OD", "ASSINAR CH"]
SUGESTOES_POR_PAGINA = 10
PAGINAS_VISIVEIS = 5

# ===============================
# FUNÇÃO DE CARREGAR DADOS
# ===============================
def carregar_dados():
    subprocessos = supabase.table("subprocessos").select("*").execute().data or []
    status_blocos_list = supabase.table("status_blocos").select("*").execute().data or []
    historico = supabase.table("historico_execucao").select("*").execute().data or []
    status_blocos = {s["id_bloco"]: s for s in status_blocos_list}
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

        if not usuario_data or usuario_data["senha"] != senha_input:
            st.sidebar.error("Usuário ou senha inválidos")
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

if not st.session_state.usuario_logado:
    st.stop()

usuario = st.session_state.usuario_logado

# ===============================
# CARREGAR DADOS
# ===============================
subprocessos, status_blocos, historico = carregar_dados()
df = pd.DataFrame(subprocessos)

# ===============================
# EXTRAI DADOS DO JSON
# ===============================
for col in ["sol", "apoiada", "empenho", "id", "pag"]:
    df[col] = df["dados"].apply(lambda x: x.get(col) if x else None)

# ===============================
# PESQUISA
# ===============================
st.sidebar.title("🔍 Pesquisa")
termo = st.sidebar.text_input("Pesquisar").lower().strip()

if termo:
    df = df[
        df["fornecedor"].astype(str).str.lower().str.contains(termo) |
        df["sol"].astype(str).str.lower().str.contains(termo) |
        df["empenho"].astype(str).str.lower().str.contains(termo) |
        df["id"].astype(str).str.lower().str.contains(termo)
    ]

# ===============================
# AGRUPAMENTO
# ===============================
grupos = []
for fornecedor, g1 in df.groupby("fornecedor"):
    for pag, g2 in g1.groupby("pag"):
        grupos.append(g2.copy())

grupos_paginados = [
    grupos[i:i + SUGESTOES_POR_PAGINA]
    for i in range(0, len(grupos), SUGESTOES_POR_PAGINA)
]

total_paginas = len(grupos_paginados)

# ===============================
# PAGINAÇÃO
# ===============================
st.markdown("### 📌 Páginas")

pagina_atual = st.session_state.get("pagina", 1)
inicio = st.session_state.get("inicio_paginas", 1)

if pagina_atual < inicio:
    inicio = pagina_atual
elif pagina_atual >= inicio + PAGINAS_VISIVEIS:
    inicio = pagina_atual - PAGINAS_VISIVEIS + 1

fim = min(inicio + PAGINAS_VISIVEIS - 1, total_paginas)
st.session_state.inicio_paginas = inicio

# ---------- números ----------
cols = st.columns(PAGINAS_VISIVEIS)

for idx, i in enumerate(range(inicio, fim + 1)):
    status_pag = []
    for bloco in grupos_paginados[i - 1]:
        idb = int(bloco["id_bloco"].iloc[0])
        status = status_blocos.get(idb, {}).get("status", "pendente")
        if status != "executado" and any(int(h["id_bloco"]) == idb for h in historico):
            status = "executado"
        status_pag.append(status)

    icone = (
        "🟢" if all(s == "executado" for s in status_pag)
        else "🟡" if any(s == "executado" for s in status_pag)
        else "🔴"
    )

    label = f"👉 {icone} {i}" if i == pagina_atual else f"{icone} {i}"

    if cols[idx].button(label, key=f"pag_{i}"):
        st.session_state.pagina = i
        st.rerun()

# ---------- controles centralizados ----------
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1, 2, 1])

with c2:
    col_prev, col_next = st.columns(2)

    col_prev.button(
        "⬅ Página anterior",
        disabled=inicio == 1,
        key="prev_page"
    )

    col_next.button(
        "Próxima página ➡",
        disabled=fim >= total_paginas,
        key="next_page"
    )

if inicio > 1 and st.session_state.get("prev_page"):
    st.session_state.inicio_paginas = max(inicio - PAGINAS_VISIVEIS, 1)
    st.session_state.pagina = st.session_state.inicio_paginas
    st.rerun()

if fim < total_paginas and st.session_state.get("next_page"):
    st.session_state.inicio_paginas = fim + 1
    st.session_state.pagina = st.session_state.inicio_paginas
    st.rerun()

# ===============================
# EXIBIÇÃO DOS BLOCOS
# ===============================
st.markdown(f"### 📄 Página {pagina_atual} de {total_paginas}")

for bloco in grupos_paginados[pagina_atual - 1]:
    id_bloco = int(bloco["id_bloco"].iloc[0])
    status = status_blocos.get(id_bloco, {"status": "pendente"})
    estado = status.get("status")

    if estado != "executado" and any(int(h["id_bloco"]) == id_bloco for h in historico):
        estado = "executado"

    icone = "🟢" if estado == "executado" else "🟡" if estado == "em_execucao" else "🔴"

    st.subheader(
        f"{icone} Sugestão - Fornecedor: {bloco['fornecedor'].iloc[0]} | PAG: {bloco['pag'].iloc[0]}"
    )

    st.dataframe(
        bloco[["sol", "apoiada", "empenho", "id"]],
        use_container_width=True
    )

    c1, c2 = st.columns(2)

    if estado == "pendente":
        if c1.button("▶ Iniciar execução", key=f"iniciar_{id_bloco}"):
            supabase.table("status_blocos").upsert({
                "id_bloco": id_bloco,
                "status": "em_execucao",
                "usuario": usuario,
                "inicio": datetime.now().isoformat()
            }).execute()
            st.rerun()

    elif estado == "em_execucao" and status.get("usuario") == usuario:
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

    elif estado == "em_execucao":
        c1.button(f"🔒 Em execução por {status.get('usuario')}", disabled=True)

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
if historico:
    st.sidebar.dataframe(pd.DataFrame(historico))
