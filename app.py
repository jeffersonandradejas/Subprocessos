import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# ---------------------------
# Arquivo JSON de persistência
# ---------------------------
ARQUIVO = "dados.json"

def carregar_dados():
    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {"usuarios": {}}

def salvar_dados(dados):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# ---------------------------
# Streamlit App
# ---------------------------
st.set_page_config(page_title="Controle de Subprocessos", layout="wide")
st.title("📌 Subprocessos Inteligentes Offline/Online")

dados = carregar_dados()

# ---------------------------
# Login simples
# ---------------------------
usuario = st.text_input("👤 Nome do usuário").strip().lower()
if not usuario:
    st.stop()

if usuario not in dados["usuarios"]:
    dados["usuarios"][usuario] = {"blocos": {}, "historico": []}
    salvar_dados(dados)

user = dados["usuarios"][usuario]

# ---------------------------
# Carregar/Inserir blocos de subprocessos
# ---------------------------
st.subheader("⚙️ Configuração de Blocos")

if "blocos_df" not in st.session_state:
    # Inicialmente converte os blocos do JSON em DataFrame
    if user["blocos"]:
        st.session_state.blocos_df = pd.DataFrame.from_dict(user["blocos"], orient="index")
        st.session_state.blocos_df.index.name = "ID"
        st.session_state.blocos_df.reset_index(inplace=True)
    else:
        st.session_state.blocos_df = pd.DataFrame(columns=["ID", "fornecedor", "pag", "valor", "status"])

df_blocos = st.session_state.blocos_df

# Inserir novo bloco
with st.expander("➕ Adicionar novo bloco"):
    fornecedor = st.text_input("Fornecedor", key="fornecedor")
    pag = st.text_input("PAG", key="pag")
    valor = st.number_input("Valor", min_value=0.0, key="valor")
    if st.button("Adicionar bloco"):
        novo_id = str(len(df_blocos) + 1)
        novo_bloco = {"ID": novo_id, "fornecedor": fornecedor, "pag": pag, "valor": valor, "status": ""}
        df_blocos = pd.concat([df_blocos, pd.DataFrame([novo_bloco])], ignore_index=True)
        st.session_state.blocos_df = df_blocos
        # Atualizar no JSON
        user["blocos"][novo_id] = novo_bloco
        salvar_dados(dados)
        st.success(f"Bloco {novo_id} adicionado!")

# ---------------------------
# Paginação
# ---------------------------
blocos_por_pagina = 5
total_paginas = (len(df_blocos) - 1) // blocos_por_pagina + 1
if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = 0

pagina = st.session_state.pagina_atual
inicio = pagina * blocos_por_pagina
fim = inicio + blocos_por_pagina
blocos_pagina = df_blocos.iloc[inicio:fim]

# ---------------------------
# Função de destaque por status
# ---------------------------
def destacar_status(row):
    if row["status"] == "em execução":
        return ["background-color: #FFF3CD"]*len(row)
    elif row["status"] == "executado":
        return ["background-color: #E0E0E0"]*len(row)
    else:
        return [""]*len(row)

# ---------------------------
# Exibir blocos da página
# ---------------------------
st.subheader(f"📄 Blocos Página {pagina + 1} / {total_paginas}")

for i, row in blocos_pagina.iterrows():
    st.dataframe(pd.DataFrame([row]).style.apply(destacar_status, axis=1))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Marcar como em execução", key=f"exec_{row['ID']}"):
            df_blocos.loc[df_blocos["ID"]==row["ID"], "status"] = "em execução"
            user["blocos"][row["ID"]]["status"] = "em execução"
            salvar_dados(dados)
            st.experimental_rerun()
    with col2:
        if st.button("✔ Marcar como executado", key=f"exec_final_{row['ID']}"):
            df_blocos.loc[df_blocos["ID"]==row["ID"], "status"] = "executado"
            user["blocos"][row["ID"]]["status"] = "executado"
            # Adicionar ao histórico
            user["historico"].append({
                "id": row["ID"],
                "fornecedor": row["fornecedor"],
                "pag": row["pag"],
                "valor": row["valor"],
                "data": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            salvar_dados(dados)
            st.experimental_rerun()

# ---------------------------
# Navegação entre páginas
# ---------------------------
col1, col2 = st.columns(2)
if col1.button("⬅ Página anterior") and pagina > 0:
    st.session_state.pagina_atual -= 1
    st.experimental_rerun()
if col2.button("➡ Próxima página") and pagina < total_paginas - 1:
    st.session_state.pagina_atual += 1
    st.experimental_rerun()

# ---------------------------
# Histórico lateral
# ---------------------------
st.sidebar.title("🗓 Histórico de Subprocessos")
if user["historico"]:
    st.sidebar.dataframe(pd.DataFrame(user["historico"]))
else:
    st.sidebar.info("Nenhum subprocesso registrado ainda.")
