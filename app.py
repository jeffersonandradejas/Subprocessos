
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
            st.info(f"{len(df_csv)} novas linhas serão importadas após remover duplicatas.")

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
# CARREGAR DADOS
# ===============================
subprocessos, status_blocos, historico = carregar_dados()

if not subprocessos:
    st.warning("Nenhum subprocesso disponível.")
    st.stop()

df = pd.DataFrame(subprocessos)

# ===============================
# EXTRAI DADOS DO JSON
# ===============================
for col in ["sol", "apoiada", "empenho", "id", "pag"]:
    df[col] = df["dados"].apply(lambda x: x.get(col) if x else None)

# ===============================
# CAMPO DE PESQUISA NA SIDEBAR
# ===============================
st.sidebar.title("🔍 Pesquisa")
termo_pesquisa = st.sidebar.text_input(
    "Pesquisar por fornecedor, solicitação, empenho ou ID"
).strip().lower()

# ===============================
# FILTRA OS DADOS COM BASE NA PESQUISA
# ===============================
if termo_pesquisa:
    df = df[
        df["fornecedor"].astype(str).str.lower().str.contains(termo_pesquisa) |
        df["sol"].astype(str).str.lower().str.contains(termo_pesquisa) |
        df["empenho"].astype(str).str.lower().str.contains(termo_pesquisa) |
        df["id"].astype(str).str.lower().str.contains(termo_pesquisa)
    ]

# ===============================
# AGRUPAMENTO
# ===============================
grupos_fornecedor = []
for fornecedor, g1 in df.groupby("fornecedor"):
    for pag, g2 in g1.groupby("pag"):
        grupos_fornecedor.append(g2.copy())

# ===============================
# PAGINAÇÃO
# ===============================
grupos_paginados = [
    grupos_fornecedor[i:i + SUGESTOES_POR_PAGINA]
    for i in range(0, len(grupos_fornecedor), SUGESTOES_POR_PAGINA)
]

total_paginas = len(grupos_paginados)
pagina = st.session_state.get("pagina", 1)

# ===============================
# CSS DOS BOTÕES DE PAGINAÇÃO
# ===============================
st.markdown(
    """
    <style>
    /* Apenas os botões de paginação com número no texto */
    div.stButton > button {
        min-width: 60px !important;
        height: 35px !important;
        padding: 0 !important;
        margin: 2px !important;
        font-size: 14px !important;
        white-space: normal !important;
    }

    /* Botões de execução (Iniciar/Finalizar) */
    div.stButton > button:contains("Iniciar execução"),
    div.stButton > button:contains("Finalizar execução") {
        min-width: 180px !important;
        height: 35px !important;
        font-size: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("### 📌 Páginas")

BOTOES_POR_LINHA = 8

for linha_inicio in range(0, total_paginas, BOTOES_POR_LINHA):
    cols = st.columns(BOTOES_POR_LINHA)
    ...

# recarrega o histórico atualizado
historico = supabase.table("historico_execucao").select("*").execute().data or []

for linha_inicio in range(0, total_paginas, BOTOES_POR_LINHA):
    cols = st.columns(BOTOES_POR_LINHA)

    for offset in range(BOTOES_POR_LINHA):
        i = linha_inicio + offset + 1
        if i > total_paginas:
            break

        status_pag = []
        for bloco in grupos_paginados[i - 1]:
            idb = int(bloco["id_bloco"].iloc[0])
            
            # status direto do bloco
            status_bloco = status_blocos.get(idb, {}).get("status", "pendente")
            
            # se não estiver executado, verifica histórico
            if status_bloco != "executado":
                if any(int(h.get("id_bloco")) == idb for h in historico):
                    status_bloco = "executado"

            status_pag.append(status_bloco)

        # determina ícone da página
        if all(s == "executado" for s in status_pag):
            icone = "🟢"
        elif any(s == "executado" for s in status_pag):
            icone = "🟡"
        else:
            icone = "🔴"

        # label do botão
        label = f"{icone} {i}"
        if i == pagina:
            if i < 10:
                label = f"👉 ({icone} {i})"
            else:
                label = f"👉 {icone} {i}"

        if cols[offset].button(label, key=f"pag_{i}"):
            st.session_state.pagina = i
            st.rerun()


# ===============================
# EXIBIÇÃO DOS BLOCOS E BOTÕES INDIVIDUAIS
# ===============================
blocos_pagina = grupos_paginados[pagina - 1]
st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

for bloco in blocos_pagina:
    id_bloco = int(bloco["id_bloco"].iloc[0])

    # Recarrega status do bloco do banco
    status_atual = supabase.table("status_blocos").select("*").eq("id_bloco", id_bloco).execute().data
    if status_atual:
        status_atual = status_atual[0]
    else:
        status_atual = {"status": "pendente", "usuario": None}

    usuario_bloco = status_atual.get("usuario", None)
    estado = status_atual.get("status", "pendente")

    # 🔹 Verifica histórico para blocos finalizados
    if estado != "executado":
        if any(int(h.get("id_bloco")) == id_bloco for h in historico):
            estado = "executado"

    # Define ícone com base no status
    if estado == "executado":
        icone = "🟢"
    elif estado == "em_execucao":
        icone = "🟡"
    else:
        icone = "🔴"

    st.subheader(
        f"{icone} Sugestão - Fornecedor: {bloco['fornecedor'].iloc[0]} | PAG: {bloco['pag'].iloc[0]}"
    )

    # Mostra tabela do bloco
    bloco_display = bloco.copy().reset_index(drop=True)
    bloco_display.index += 1
    st.dataframe(
        bloco_display[["sol", "apoiada", "empenho", "id"]],
        use_container_width=True
    )

    # ===============================
    # BOTÕES INDIVIDUAIS PARA CADA BLOCO
    # ===============================
    c1, c2 = st.columns(2)

    # Botão iniciar execução
    if estado == "pendente":
        if c1.button("▶ Iniciar execução", key=f"iniciar_{id_bloco}"):
            try:
                supabase.table("status_blocos").upsert({
                    "id_bloco": id_bloco,
                    "status": "em_execucao",
                    "usuario": usuario,
                    "inicio": datetime.now().isoformat()
                }).execute()
                st.success(f"Sugestão {id_bloco} iniciada!")
            except Exception as e:
                st.error(f"Erro ao iniciar execução: {e}")
            st.experimental_rerun()

    # Botão finalizar execução (somente para quem iniciou)
    elif estado == "em_execucao" and usuario_bloco == usuario:
        if c2.button("✔ Finalizar execução", key=f"finalizar_{id_bloco}"):
            try:
                supabase.table("status_blocos").update({
                    "status": "executado"
                }).eq("id_bloco", id_bloco).execute()

                supabase.table("historico_execucao").insert({
                    "id_bloco": id_bloco,
                    "usuario": usuario,
                    "data_execucao": datetime.now().isoformat()
                }).execute()

                st.success(f"Sugestão {id_bloco} finalizada!")
            except Exception as e:
                st.error(f"Erro ao finalizar execução: {e}")
            st.experimental_rerun()

    # Bloqueado para outro usuário
    elif estado == "em_execucao" and usuario_bloco != usuario:
        c1.button(f"🔒 Em execução por {usuario_bloco}", disabled=True, key=f"bloqueado_{id_bloco}")

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.title("🗓 Histórico")
if historico:
    st.sidebar.dataframe(pd.DataFrame(historico))
else:
    st.sidebar.info("Nenhum subprocesso executado ainda.")
