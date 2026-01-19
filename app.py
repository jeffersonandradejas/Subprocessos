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
SUGESTOES_POR_PAGINA = 8

# ===============================
# FUNÇÃO DE CARREGAR DADOS
# ===============================
def carregar_dados():
    subprocessos = supabase.table("subprocessos").select("*").execute().data or []
    status_blocos_list = supabase.table("status_blocos").select("*").execute().data or []
    historico = supabase.table("historico_execucao").select("*").execute().data or []

    status_blocos = {s['id_bloco']: s for s in status_blocos_list}
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

if not st.session_state.usuario_logado:
    st.info("Faça login para continuar.")
    st.stop()

usuario = st.session_state.usuario_logado

# ===============================
# CARREGAR DADOS
# ===============================
subprocessos, status_blocos, historico = carregar_dados()

df = pd.DataFrame(subprocessos)

for col in ["sol", "apoiada", "empenho", "id", "pag"]:
    df[col] = df["dados"].apply(lambda x: x.get(col) if x else None)

# ===============================
# AGRUPAMENTO
# ===============================
grupos_fornecedor = []
for fornecedor, g1 in df.groupby("fornecedor"):
    for pag, g2 in g1.groupby("pag"):
        grupos_fornecedor.append(g2.copy())

grupos_paginados = [
    grupos_fornecedor[i:i + SUGESTOES_POR_PAGINA]
    for i in range(0, len(grupos_fornecedor), SUGESTOES_POR_PAGINA)
]

total_paginas = len(grupos_paginados)
pagina = st.session_state.get("pagina", 1)

# ===============================
# PAGINAÇÃO — 2 LINHAS (5 + 5)
# ===============================
st.markdown("### 📌 Páginas")

PAGINAS_POR_LINHA = 5
TOTAL_PAGINAS_VISIVEIS = 10

inicio = ((pagina - 1) // TOTAL_PAGINAS_VISIVEIS) * TOTAL_PAGINAS_VISIVEIS + 1
fim = min(inicio + TOTAL_PAGINAS_VISIVEIS - 1, total_paginas)

historico = supabase.table("historico_execucao").select("*").execute().data or []

# Linha de cima
cols_top = st.columns(PAGINAS_POR_LINHA + 1)

if inicio > 1:
    if cols_top[0].button("◀"):
        st.session_state.pagina = inicio - 1
        st.rerun()

for idx, i in enumerate(range(inicio, min(inicio + PAGINAS_POR_LINHA, fim + 1))):
    status_pag = []
    for bloco in grupos_paginados[i - 1]:
        idb = int(bloco["id_bloco"].iloc[0])
        status_bloco = status_blocos.get(idb, {}).get("status", "pendente")
        if status_bloco != "executado":
            if any(int(h["id_bloco"]) == idb for h in historico):
                status_bloco = "executado"
        status_pag.append(status_bloco)

    if all(s == "executado" for s in status_pag):
        icone = "🟢"
    elif any(s == "executado" for s in status_pag):
        icone = "🟡"
    else:
        icone = "🔴"

    label = f"{icone} {i}"
    if i == pagina:
        label = f"👉 {icone} {i}"

    if cols_top[idx + 1].button(label, key=f"top_{i}"):
        st.session_state.pagina = i
        st.rerun()

# Linha de baixo
cols_bottom = st.columns(PAGINAS_POR_LINHA + 1)

for idx, i in enumerate(range(inicio + PAGINAS_POR_LINHA, fim + 1)):
    status_pag = []
    for bloco in grupos_paginados[i - 1]:
        idb = int(bloco["id_bloco"].iloc[0])
        status_bloco = status_blocos.get(idb, {}).get("status", "pendente")
        if status_bloco != "executado":
            if any(int(h["id_bloco"]) == idb for h in historico):
                status_bloco = "executado"
        status_pag.append(status_bloco)

    if all(s == "executado" for s in status_pag):
        icone = "🟢"
    elif any(s == "executado" for s in status_pag):
        icone = "🟡"
    else:
        icone = "🔴"

    label = f"{icone} {i}"
    if i == pagina:
        label = f"👉 {icone} {i}"

    if cols_bottom[idx + 1].button(label, key=f"bottom_{i}"):
        st.session_state.pagina = i
        st.rerun()

if fim < total_paginas:
    if cols_bottom[0].button("▶"):
        st.session_state.pagina = fim + 1
        st.rerun()

# ===============================
# EXIBIÇÃO DOS BLOCOS
# ===============================
blocos_pagina = grupos_paginados[pagina - 1]
st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

for bloco in blocos_pagina:
    id_bloco = int(bloco["id_bloco"].iloc[0])

    status_atual = supabase.table("status_blocos").select("*").eq("id_bloco", id_bloco).execute().data
    status_atual = status_atual[0] if status_atual else {"status": "pendente", "usuario": None}

    estado = status_atual["status"]
    usuario_bloco = status_atual.get("usuario")

    if estado != "executado":
        if any(int(h["id_bloco"]) == id_bloco for h in historico):
            estado = "executado"

    icone = "🟢" if estado == "executado" else "🟡" if estado == "em_execucao" else "🔴"

    st.subheader(
        f"{icone} Sugestão - Fornecedor: {bloco['fornecedor'].iloc[0]} | PAG: {bloco['pag'].iloc[0]}"
    )

    bloco_display = bloco.copy().reset_index(drop=True)
    bloco_display.index += 1

    st.dataframe(
        bloco_display[["sol", "apoiada", "empenho", "id"]],
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
            st.experimental_rerun()

    elif estado == "em_execucao" and usuario_bloco == usuario:
        if c2.button("✔ Finalizar execução", key=f"finalizar_{id_bloco}"):
            supabase.table("status_blocos").update({
                "status": "executado"
            }).eq("id_bloco", id_bloco).execute()

            supabase.table("historico_execucao").insert({
                "id_bloco": id_bloco,
                "usuario": usuario,
                "data_execucao": datetime.now().isoformat()
            }).execute()

            st.experimental_rerun()

    elif estado == "em_execucao" and usuario_bloco != usuario:
        c1.button(f"🔒 Em execução por {usuario_bloco}", disabled=True)

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
st.sidebar.dataframe(pd.DataFrame(historico))
