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
SUGESTOES_POR_PAGINA = 10   # quantos blocos por página
PAGINAS_POR_LINHA = 5       # 2 linhas de 5 = 10 páginas visíveis por vez

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
# ADMIN — IMPORTAR CSV
# ===============================
if tipo_usuario == "admin":
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("📁 Importar CSV", type="csv")
    if arquivo:
        df_csv = pd.read_csv(arquivo)
        df_csv.columns = df_csv.columns.str.strip().str.lower()
        if "status" in df_csv.columns:
            df_csv = df_csv[df_csv["status"].isin(ACOES_VALIDAS)]
        df_csv = df_csv.where(pd.notnull(df_csv), None)

        subprocessos_existentes = pd.DataFrame(
            supabase.table("subprocessos").select("*").execute().data or []
        )

        if not subprocessos_existentes.empty:
            existentes_json = subprocessos_existentes["dados"].apply(lambda x: str(x))
            df_csv = df_csv[
                ~df_csv.apply(lambda row: str(row.to_dict()) in list(existentes_json), axis=1)
            ]
        if df_csv.empty:
            st.warning("Nenhuma linha nova para importar.")
            st.stop()

        df_csv.sort_values(by=["fornecedor", "pag"], inplace=True, ignore_index=True)
        ultimo_id_bloco = int(subprocessos_existentes["id_bloco"].max()) if not subprocessos_existentes.empty else 0
        id_bloco_atual = ultimo_id_bloco + 1

        blocos = []
        for fornecedor, g1 in df_csv.groupby("fornecedor"):
            for pag, g2 in g1.groupby("pag"):
                g2 = g2.copy()
                g2["id_bloco"] = id_bloco_atual
                blocos.append(g2)
                id_bloco_atual += 1

        df_final = pd.concat(blocos, ignore_index=True)
        for _, row in df_final.iterrows():
            dados_dict = {k.lower(): (v if pd.notnull(v) else None) for k, v in row.items()}
            supabase.table("subprocessos").insert({
                "id_bloco": int(dados_dict.get("id_bloco")),
                "fornecedor": dados_dict.get("fornecedor"),
                "pag": parse_int(dados_dict.get("pag")),
                "dados": dados_dict,
                "created_at": datetime.now().isoformat()
            }).execute()

        st.sidebar.success("CSV importado com sucesso!")
        st.rerun()

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
# PAGINAÇÃO DUPLEX
# ===============================
st.markdown("### 📌 Páginas")
pagina_atual = st.session_state.get("pagina", 1)
inicio_paginas = st.session_state.get("inicio_paginas", 1)

# Ajusta início para a página atual
if pagina_atual < inicio_paginas:
    inicio_paginas = pagina_atual
elif pagina_atual >= inicio_paginas + 2 * PAGINAS_POR_LINHA:
    inicio_paginas = pagina_atual - 2 * PAGINAS_POR_LINHA + 1
st.session_state.inicio_paginas = inicio_paginas

fim_paginas = min(inicio_paginas + 2 * PAGINAS_POR_LINHA - 1, total_paginas)

# Função para criar uma linha de botões de página
def criar_linha_paginas(inicio, fim, offset_linha=0):
    n_botoes = fim - inicio + 1
    cols = st.columns(n_botoes)
    for idx, i in enumerate(range(inicio, fim + 1)):
        status_pag = []
        for bloco in grupos_paginados[i - 1]:
            idb = int(bloco["id_bloco"].iloc[0])
            status = status_blocos.get(idb, {}).get("status", "pendente")
            if status != "executado" and any(int(h["id_bloco"]) == idb for h in historico):
                status = "executado"
            status_pag.append(status)
        icone = "🟢" if all(s == "executado" for s in status_pag) else "🟡" if any(s == "executado" for s in status_pag) else "🔴"
        label = f"👉 {icone} {i}" if i == pagina_atual else f"{icone} {i}"
        if cols[idx].button(label, key=f"pag_{i}_{offset_linha}"):
            st.session_state.pagina = i
            st.rerun()

# Linha 1
linha1_inicio = inicio_paginas
linha1_fim = min(inicio_paginas + PAGINAS_POR_LINHA - 1, fim_paginas)
criar_linha_paginas(linha1_inicio, linha1_fim, offset_linha=1)

# Linha 2
linha2_inicio = linha1_fim + 1
linha2_fim = fim_paginas
if linha2_inicio <= linha2_fim:
    criar_linha_paginas(linha2_inicio, linha2_fim, offset_linha=2)

# Botões de navegação centralizados
nav_cols = st.columns(3)
# Página anterior
if inicio_paginas > 1:
    if nav_cols[0].button("Página anterior"):
        st.session_state.inicio_paginas = max(inicio_paginas - 2 * PAGINAS_POR_LINHA, 1)
        st.session_state.pagina = st.session_state.inicio_paginas
        st.rerun()
else:
    nav_cols[0].button("Página anterior", disabled=True)

nav_cols[1].markdown(" ")  # Espaço central

# Próxima página
if fim_paginas < total_paginas:
    if nav_cols[2].button("Próxima página"):
        st.session_state.inicio_paginas = fim_paginas + 1
        st.session_state.pagina = st.session_state.inicio_paginas
        st.rerun()
else:
    nav_cols[2].button("Próxima página", disabled=True)

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

    st.dataframe(bloco[["sol", "apoiada", "empenho", "id"]], use_container_width=True)

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
else:
    st.sidebar.info("Nenhum subprocesso executado ainda.")
