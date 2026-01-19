import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ===============================
# CONFIGURAÇÃO GERAL
# ===============================
BOTOES_PAGINA_VISIVEIS = 7  # 👈 CONTROLA QUANTAS PÁGINAS APARECEM
SUGESTOES_POR_PAGINA = 8    # 👈 QUANTOS BLOCOS POR PÁGINA

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
    usuario_input = st.sidebar.text_input("Usuário")
    senha_input = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        res = supabase.table("usuarios").select("*").eq("usuario", usuario_input).execute()
        if not res.data or res.data[0]["senha"] != senha_input:
            st.sidebar.error("Usuário ou senha inválidos")
            st.stop()

        st.session_state.usuario_logado = usuario_input
        st.rerun()

usuario = st.session_state.usuario_logado
if not usuario:
    st.stop()

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
termo = st.sidebar.text_input("Buscar").lower().strip()

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
# PAGINAÇÃO (7 POR VEZ)
# ===============================
pagina_atual = st.session_state.get("pagina", 1)
bloco_inicio = st.session_state.get("bloco_inicio", 1)

if pagina_atual < bloco_inicio:
    bloco_inicio = pagina_atual
elif pagina_atual >= bloco_inicio + BOTOES_PAGINA_VISIVEIS:
    bloco_inicio = pagina_atual - BOTOES_PAGINA_VISIVEIS + 1

bloco_fim = min(bloco_inicio + BOTOES_PAGINA_VISIVEIS - 1, total_paginas)
st.session_state.bloco_inicio = bloco_inicio

cols = st.columns(BOTOES_PAGINA_VISIVEIS + 2)

# ◀ Anterior
if bloco_inicio > 1:
    if cols[0].button("◀"):
        st.session_state.bloco_inicio = max(bloco_inicio - BOTOES_PAGINA_VISIVEIS, 1)
        st.session_state.pagina = st.session_state.bloco_inicio
        st.rerun()

# Botões numerados
for idx, i in enumerate(range(bloco_inicio, bloco_fim + 1)):
    status_pag = []

    for bloco in grupos_paginados[i - 1]:
        idb = int(bloco["id_bloco"].iloc[0])
        status = status_blocos.get(idb, {}).get("status", "pendente")
        if status != "executado" and any(int(h["id_bloco"]) == idb for h in historico):
            status = "executado"
        status_pag.append(status)

    if all(s == "executado" for s in status_pag):
        icone = "🟢"
    elif any(s == "executado" for s in status_pag):
        icone = "🟡"
    else:
        icone = "🔴"

    label = f"{icone} {i}"
    if i == pagina_atual:
        label = f"👉 ({icone} {i})"

    if cols[idx + 1].button(label, key=f"pag_{i}"):
        st.session_state.pagina = i
        st.rerun()

# ▶ Próximo
if bloco_fim < total_paginas:
    if cols[-1].button("▶"):
        st.session_state.bloco_inicio = bloco_fim + 1
        st.session_state.pagina = st.session_state.bloco_inicio
        st.rerun()

# ===============================
# EXIBIÇÃO DOS BLOCOS
# ===============================
st.markdown(f"### 📄 Página {pagina_atual} de {total_paginas}")
blocos_pagina = grupos_paginados[pagina_atual - 1]

for bloco in blocos_pagina:
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

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
if historico:
    st.sidebar.dataframe(pd.DataFrame(historico))
