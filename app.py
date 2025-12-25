import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# -------------------
# Arquivo de dados
# -------------------
ARQUIVO_DADOS = "dados.json"

# -------------------
# Funções auxiliares
# -------------------
def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        dados = {
            "usuarios": {"admin": {"senha": "admin123", "role": "admin"}},
            "blocos": {},
            "historico": []
        }
        salvar_dados(dados)
        return dados

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def destacar_linha(status):
    if status.lower() == "em execução":
        return ["background-color: #FFF3CD"]*5
    elif status.lower() == "executado":
        return ["background-color: #E0E0E0"]*5
    else:
        return [""]*5

# -------------------
# Autenticação simples
# -------------------
st.sidebar.title("👤 Login")
username = st.sidebar.text_input("Usuário")
senha = st.sidebar.text_input("Senha", type="password")
st.session_state.authenticated = st.session_state.get("authenticated", False)

dados = carregar_dados()
usuario_info = None

if st.sidebar.button("Entrar"):
    if username in dados["usuarios"] and dados["usuarios"][username]["senha"] == senha:
        st.session_state.authenticated = True
        st.session_state.usuario = username
        st.success(f"✅ Logado como {username}")
    else:
        st.error("❌ Usuário ou senha incorretos")

if st.session_state.get("authenticated"):
    usuario_info = dados["usuarios"][st.session_state.usuario]
    st.title("📌 Subprocessos Inteligentes Offline/Online")
    
    # -------------------
    # Importar Dados
    # -------------------
    st.subheader("📋 Importar dados da planilha")
    metodo_importacao = st.radio("Escolha como importar os dados:", ["📋 Colar planilha", "📁 Importar CSV"])
    df_importado = None

    if metodo_importacao == "📋 Colar planilha":
        colados = st.text_area("Cole os dados aqui (separados por TAB)", height=300)
        if st.button("📥 Importar dados colados"):
            if colados.strip():
                try:
                    linhas = [linha for linha in colados.strip().split("\n") if linha.strip()]
                    cabecalho = linhas[0].split("\t")
                    num_cols = len(cabecalho)
                    linhas_split = [linha.split("\t") for linha in linhas[1:]]
                    linhas_corrigidas = [
                        l + [""]*(num_cols - len(l)) if len(l) < num_cols else l[:num_cols]
                        for l in linhas_split
                    ]
                    df_importado = pd.DataFrame(linhas_corrigidas, columns=cabecalho)
                    st.success("✅ Dados importados com sucesso!")
                except Exception as e:
                    st.error(f"❌ Erro ao processar os dados: {e}")

    elif metodo_importacao == "📁 Importar CSV":
        arquivo = st.file_uploader("Escolha um arquivo CSV", type="csv")
        if arquivo:
            try:
                df_importado = pd.read_csv(arquivo)
                st.success("✅ CSV importado com sucesso!")
            except Exception as e:
                st.error(f"❌ Erro ao ler o CSV: {e}")

    if df_importado is not None:
        for _, row in df_importado.iterrows():
            bloco_id = row["SOL"]
            dados["blocos"][bloco_id] = {
                "FORNECEDOR": row.get("FORNECEDOR",""),
                "PAG": row.get("PAG",""),
                "VALOR": str(row.get("VALOR","")),
                "STATUS": row.get("STATUS",""),
                "DATA": row.get("DATA","")
            }
        salvar_dados(dados)
        st.experimental_rerun()

    # -------------------
    # Histórico de Subprocessos
    # -------------------
    st.sidebar.title("🗓 Histórico de Subprocessos")
    if dados["historico"]:
        historico_df = pd.DataFrame(dados["historico"])
        st.sidebar.dataframe(historico_df)
    else:
        st.sidebar.info("Nenhum subprocesso registrado ainda.")

    # -------------------
    # Configuração de Blocos (somente admin)
    # -------------------
    if usuario_info.get("role") == "admin":
        st.subheader("⚙️ Configuração de Blocos")
        novo_bloco = st.text_input("➕ Adicionar novo bloco (ID)")
        if st.button("Adicionar bloco"):
            if novo_bloco:
                if novo_bloco not in dados["blocos"]:
                    dados["blocos"][novo_bloco] = {
                        "FORNECEDOR": "",
                        "PAG": "",
                        "VALOR": "",
                        "STATUS": "",
                        "DATA": ""
                    }
                    salvar_dados(dados)
                    st.success(f"Bloco {novo_bloco} adicionado!")
                    st.experimental_rerun()
                else:
                    st.warning("Bloco já existe!")

    # -------------------
    # Paginação e exibição dos blocos
    # -------------------
    st.subheader("📄 Blocos")
    blocos_list = list(dados["blocos"].items())
    blocos_por_pagina = 8
    total_paginas = (len(blocos_list) - 1) // blocos_por_pagina + 1

    if "pagina_atual" not in st.session_state:
        st.session_state.pagina_atual = 0

    inicio = st.session_state.pagina_atual * blocos_por_pagina
    fim = inicio + blocos_por_pagina
    blocos_pagina = blocos_list[inicio:fim]

    for bloco_id, bloco in blocos_pagina:
        st.subheader(f"Bloco {bloco_id}")
        df_bloco = pd.DataFrame([bloco])
        st.dataframe(df_bloco.style.apply(lambda x: destacar_linha(bloco["STATUS"]), axis=1))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Marcar como em execução", key=f"exec_{bloco_id}"):
                dados["blocos"][bloco_id]["STATUS"] = "em execução"
                salvar_dados(dados)
                st.experimental_rerun()
        with col2:
            if st.button("✔ Marcar como executado", key=f"done_{bloco_id}"):
                dados["blocos"][bloco_id]["STATUS"] = "executado"
                dados["historico"].append({
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "usuario": st.session_state.usuario,
                    "id": bloco_id,
                    "fornecedor": bloco["FORNECEDOR"],
                    "pag": bloco["PAG"],
                    "valor": bloco["VALOR"]
                })
                salvar_dados(dados)
                st.experimental_rerun()

    # Navegação entre páginas
    col_prev, col_next = st.columns(2)
    if col_prev.button("⬅ Página anterior") and st.session_state.pagina_atual > 0:
        st.session_state.pagina_atual -= 1
        st.experimental_rerun()
    if col_next.button("➡ Próxima página") and st.session_state.pagina_atual < total_paginas - 1:
        st.session_state.pagina_atual += 1
        st.experimental_rerun()
