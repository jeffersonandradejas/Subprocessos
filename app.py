import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ===============================
# CONFIGURAÇÃO DO SUPABASE
# ===============================
SUPABASE_URL = "https://seuprojeto.supabase.co"  # substitua pela sua URL
SUPABASE_KEY = "sb_secret__VPEd..."  # substitua pela sua SECRET KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# CONSTANTES
# ===============================
ITENS_POR_PAGINA = 8

# ===============================
# FUNÇÃO PARA CONVERTER NÚMEROS
# ===============================
def parse_int(valor):
    try:
        if valor is None:
            return None
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None

# ===============================
# IMPORTAÇÃO DO CSV
# ===============================
st.title("📁 Importar CSV")

uploaded_file = st.file_uploader("Escolha o CSV", type="csv")
if uploaded_file is not None:
    df_csv = pd.read_csv(uploaded_file)
    # Normaliza cabeçalhos para minúsculas
    df_csv.columns = df_csv.columns.str.lower()
    
    # Remove duplicatas
    df_csv.drop_duplicates(subset=["id"], inplace=True, ignore_index=True)
    
    # Converte colunas importantes
    if "pag" in df_csv.columns:
        df_csv["pag"] = df_csv["pag"].apply(lambda x: str(x).strip() if pd.notnull(x) else None)
    
    # Adiciona id_bloco sequencial (apenas para organizar internamente)
    df_csv["id_bloco"] = range(1, len(df_csv) + 1)

    # Cria coluna dados como JSON
    df_csv["dados"] = df_csv.apply(lambda row: {
        "sol": row.get("sol"),
        "apoiada": row.get("apoiada"),
        "empenho": row.get("empenho"),
        "id": row.get("id"),
        "pag": row.get("pag"),
        "fornecedor": row.get("fornecedor"),
        "pregão": row.get("pregão"),
        "valor": row.get("valor"),
        "data": row.get("data")
    }, axis=1)

    # ===============================
    # INSERÇÃO NO SUPABASE
    # ===============================
    for _, row in df_csv.iterrows():
        try:
            supabase.table("subprocessos").insert({
                "id_bloco": row["id_bloco"],
                "fornecedor": row["fornecedor"],
                "pag": row["pag"],
                "dados": row["dados"]
            }).execute()
        except Exception as e:
            st.warning(f"Erro ao inserir linha {row.to_dict()}: {e}")

    st.success(f"{len(df_csv)} linhas processadas!")

# ===============================
# EXIBIÇÃO DOS SUBPROCESSOS
# ===============================
st.header("📄 Subprocessos")

# Busca todos os registros do Supabase
res = supabase.table("subprocessos").select("*").execute()
df = pd.DataFrame(res.data)

if not df.empty:
    # Extrai colunas de 'dados'
    for campo in ["sol", "apoiada", "empenho", "id", "pag"]:
        df[campo] = df["dados"].apply(lambda x: x.get(campo) if x else None)

    # Agrupamento inteligente
    grupos = []
    for fornecedor, g1 in df.groupby("fornecedor"):
        blocos = [g1.iloc[i:i+ITENS_POR_PAGINA] for i in range(0, len(g1), ITENS_POR_PAGINA)]
        grupos.extend(blocos)

    pag_remaining = df.groupby("pag")
    for pag, g1 in pag_remaining:
        ids_existentes = pd.concat(grupos)["id"].tolist() if grupos else []
        g1_novas = g1[~g1["id"].isin(ids_existentes)]
        if not g1_novas.empty:
            blocos = [g1_novas.iloc[i:i+ITENS_POR_PAGINA] for i in range(0, len(g1_novas), ITENS_POR_PAGINA)]
            grupos.extend(blocos)

    total_paginas = max(1, len(grupos))

    # Paginação
    if "pagina" not in st.session_state:
        st.session_state.pagina = 1
    pagina = st.session_state.pagina

    st.markdown("### 📌 Páginas")
    cols = st.columns(min(total_paginas, 10))
    for i in range(1, total_paginas + 1):
        if cols[(i-1) % len(cols)].button(f"{i}"):
            st.session_state.pagina = i
            st.rerun()

    inicio = (pagina - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    blocos_pagina = grupos[inicio:fim]

    st.markdown(f"### 📄 Página {pagina} de {total_paginas}")

    # Exibição dos blocos
    for bloco in blocos_pagina:
        bloco_display = bloco.copy()
        bloco_display.insert(0, "Nº", range(1, len(bloco_display) + 1))
        colunas_exibir = ["Nº", "sol", "apoiada", "empenho", "id"]
        st.dataframe(bloco_display[colunas_exibir], use_container_width=True)
else:
    st.info("Nenhum subprocesso carregado ainda.")
