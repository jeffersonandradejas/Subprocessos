import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config("Subprocessos Inteligentes", layout="wide")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ACOES_VALIDAS = ["ASSINAR OD", "ASSINAR CH"]
ITENS_POR_PAGINA = 8


def parse_int(valor):
    try:
        if valor is None:
            return None
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None


# ===============================
# CARREGAR DADOS
# ===============================
def carregar_dados():
    subprocessos = supabase.table("subprocessos").select("*").execute().data or []
    status_blocos = {
        s["id_bloco"]: s
        for s in supabase.table("status_blocos").select("*").execute().data or []
    }
    historico = supabase.table("historico_execucao").select("*").execute().data or []
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
            st.sidebar.error("Credenciais inválidas")
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
        .data[0]["tipo"]
    )
    st.sidebar.success(f"Olá {usuario}")
    if st.sidebar.button("Sair"):
        st.session_state.usuario_logado = None
        st.rerun()

if not st.session_state.usuario_logado:
    st.stop()


# ===============================
# ADMIN — IMPORTAR CSV
# ===============================
if tipo_usuario == "admin":
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("Importar CSV", type="csv")

    if arquivo:
        df = pd.read_csv(arquivo)
        df.columns = df.columns.str.strip().str.lower()
        df = df[df["status"].isin(ACOES_VALIDAS)]
        df = df.where(pd.notnull(df), None)

        existentes = pd.DataFrame(
            supabase.table("subprocessos").select("dados").execute().data or []
        )

        if not existentes.empty:
            existentes_set = set(existentes["dados"].astype(str))
            df = df[~df.apply(lambda r: str(r.to_dict()) in existentes_set, axis=1)]

        if df.empty:
            st.warning("Nenhuma linha nova para importar.")
            st.stop()

        df.sort_values(by=["fornecedor"], inplace=True)

        ultimo = supabase.table("subprocessos").select("id_bloco").order("id_bloco", desc=True).limit(1).execute().data
        id_bloco_atual = ultimo[0]["id_bloco"] + 1 if ultimo else 1

        for fornecedor, grupo in df.groupby("fornecedor"):
            grupo = grupo.copy()
            grupo["id_bloco"] = id_bloco_atual
            for _, row in grupo.iterrows():
                supabase.table("subprocessos").insert({
                    "id_bloco": id_bloco_atual,
                    "fornecedor": row.get("fornecedor"),
                    "pag": row.get("pag"),
                    "dados": row.to_dict()
                }).execute()
            id_bloco_atual += 1

        st.sidebar.success("CSV importado com sucesso!")
        st.rerun()


# ===============================
# EXIBIÇÃO PRINCIPAL
# ===============================
subprocessos, status_blocos, historico = carregar_dados()
df = pd.DataFrame(subprocessos)

if df.empty:
    st.warning("Nenhum subprocesso disponível.")
    st.stop()

# ====== LÓGICA INTELIGENTE ======
if df["fornecedor"].duplicated().any():
    modo = "fornecedor"
    grupos = dict(tuple(df.groupby("fornecedor")))
else:
    modo = "pag"
    grupos = dict(tuple(df.groupby("pag")))

lista_grupos = list(grupos.items())
total_paginas = max(1, (len(lista_grupos) - 1) // ITENS_POR_PAGINA + 1)

pagina = st.session_state.get("pagina", 1)
st.markdown("### 📌 Páginas")
cols = st.columns(min(total_paginas, 10))

for i in range(1, total_paginas + 1):
    if cols[(i - 1) % len(cols)].button(str(i)):
        st.session_state.pagina = i
        st.rerun()

inicio = (pagina - 1) * ITENS_POR_PAGINA
fim = inicio + ITENS_POR_PAGINA

st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

for chave, bloco in lista_grupos[inicio:fim]:
    st.subheader(f"{modo.upper()}: {chave}")
    st.dataframe(bloco, use_container_width=True)

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
if historico:
    st.sidebar.dataframe(pd.DataFrame(historico))
