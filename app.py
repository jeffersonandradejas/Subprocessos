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
# ADMIN — IMPORTAR CSV
# ===============================
if tipo_usuario == "admin":
    st.sidebar.title("⚙️ Administração")
    arquivo = st.sidebar.file_uploader("📁 Importar CSV", type="csv")

    if arquivo:
        df_csv = pd.read_csv(arquivo)
        df_csv.columns = df_csv.columns.str.strip().str.lower()

        # Filtra apenas status válidos
        if "status" in df_csv.columns:
            df_csv = df_csv[df_csv["status"].isin(ACOES_VALIDAS)]

        df_csv = df_csv.where(pd.notnull(df_csv), None)

        subprocessos_existentes = pd.DataFrame(
            supabase.table("subprocessos").select("*").execute().data or []
        )

        # Remove duplicados
        if not subprocessos_existentes.empty:
            existentes_json = subprocessos_existentes["dados"].apply(lambda x: str(x))
            df_csv = df_csv[~df_csv.apply(lambda row: str(row.to_dict()) in list(existentes_json), axis=1)]
            st.info(f"{len(df_csv)} novas linhas serão importadas após remover duplicatas.")

        if df_csv.empty:
            st.warning("Nenhuma linha nova para importar.")
            st.stop()

        # Criar blocos inteligentes
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

        # Inserir no Supabase
        for _, row in df_final.iterrows():
            dados_dict = {k.lower(): (v if pd.notnull(v) else None) for k, v in row.items()}
            try:
                supabase.table("subprocessos").insert({
                    "id_bloco": int(dados_dict.get("id_bloco")),
                    "fornecedor": dados_dict.get("fornecedor"),
                    "pag": parse_int(dados_dict.get("pag")),
                    "dados": dados_dict,
                    "created_at": datetime.now().isoformat()
                }).execute()
            except Exception as e:
                st.error(f"Erro ao inserir linha {dados_dict}: {e}")

        st.sidebar.success("CSV importado e blocos criados com sucesso!")
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
# EXTRAI COLUNAS DO JSON "dados" PARA COLUNAS EXCLUSIVAS
# ===============================
dados_cols = ["sol", "apoiada", "empenho", "id", "pag"]
for col in dados_cols:
    df[col] = df["dados"].apply(lambda x: x.get(col) if x else None)

# ===============================
# AGRUPAMENTO INTELIGENTE (SUGESTÕES)
# ===============================
grupos_fornecedor = []
for fornecedor, g1 in df.groupby("fornecedor"):
    for pag, g2 in g1.groupby("pag"):
        grupos_fornecedor.append(g2.copy())

# ===============================
# PAGINAÇÃO DE SUGESTÕES
# ===============================
grupos_paginados = [
    grupos_fornecedor[i:i+SUGESTOES_POR_PAGINA]
    for i in range(0, len(grupos_fornecedor), SUGESTOES_POR_PAGINA)
]

total_paginas = len(grupos_paginados)
pagina = st.session_state.get("pagina", 1)

st.markdown("### 📌 Páginas")

# NOVO LAYOUT DE BOTOES UNIFORMES
MAX_COLS = 13
linhas = (total_paginas + MAX_COLS - 1) // MAX_COLS  # ceil(total_paginas / MAX_COLS)

for l in range(linhas):
    start = l * MAX_COLS
    end = min(start + MAX_COLS, total_paginas)
    cols = st.columns(end - start)
    
    for idx, i in enumerate(range(start + 1, end + 1)):
        status_pag = []
        for bloco in grupos_paginados[i-1]:
            idb = bloco["id_bloco"].iloc[0]
            status_pag.append(status_blocos.get(idb, {}).get("status", "pendente"))

        if status_pag and all(s == "executado" for s in status_pag):
            icone = "🟢"
        elif any(s == "em_execucao" for s in status_pag):
            icone = "🟡"
        else:
            icone = "🔴"

        button_clicked = cols[idx].button(
            f"{icone} {i}",
            key=f"pagina_{i}",
            help=f"Página {i}",
        )
        if button_clicked:
            st.session_state.pagina = i
            st.rerun()

inicio = pagina - 1
blocos_pagina = grupos_paginados[inicio]

st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

# ===============================
# EXIBIÇÃO DAS SUGESTÕES COM COLUNAS REORDENADAS
# ===============================
for bloco in blocos_pagina:
    id_bloco = bloco["id_bloco"].iloc[0]
    status = status_blocos.get(id_bloco, {"status": "pendente"})

    if status["status"] == "executado":
        icone = "🟢"
    elif status["status"] == "em_execucao" and status.get("usuario") == usuario:
        icone = "🟡"
    else:
        icone = "🔴"

    st.subheader(f"{icone} Sugestão - Fornecedor: {bloco['fornecedor'].iloc[0]} | PAG: {bloco['pag'].iloc[0]}")

    # Novo DataFrame para exibição: apenas colunas selecionadas, linha numerada começando de 1
    bloco_display = bloco.copy().reset_index(drop=True)
    bloco_display.index = bloco_display.index + 1  # inicia em 1
    colunas_exibir = ["sol", "apoiada", "empenho", "id"]
    st.dataframe(
        bloco_display[colunas_exibir],
        use_container_width=True
    )

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
