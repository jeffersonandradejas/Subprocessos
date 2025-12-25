import streamlit as st
import pandas as pd
import json
from datetime import datetime

# ----------------------------
# Funções auxiliares
# ----------------------------

# Carrega ou cria dados.json
def carregar_dados():
    try:
        with open("dados.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"usuarios": {}}

# Salva dados.json
def salvar_dados(dados):
    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

# Destacar blocos executados ou em execução
def destacar_linhas(df, status_dict):
    def cor_linha(row):
        s = status_dict.get(row["SOL"], "")
        if s == "em execução":
            return ["background-color: #FFF3CD"] * len(row)
        elif s == "executado":
            return ["background-color: #E0E0E0"] * len(row)
        else:
            return [""] * len(row)
    return df.style.apply(cor_linha, axis=1)

# ----------------------------
# Carrega dados
# ----------------------------
dados = carregar_dados()

# ----------------------------
# Login / Primeiro usuário
# ----------------------------
usuario = st.text_input("👤 Nome do usuário").strip().lower()

if usuario:
    if usuario not in dados["usuarios"]:
        # Primeiro usuário vira admin automaticamente
        dados["usuarios"][usuario] = {"admin": True if not dados["usuarios"] else False, "blocos": {}, "historico": []}
        salvar_dados(dados)
    usuario_info = dados["usuarios"][usuario]
    admin = usuario_info.get("admin", False)

    st.success(f"Olá {usuario}! {'(Administrador)' if admin else ''}")

    # ----------------------------
    # Painel administrador
    # ----------------------------
    if admin:
        st.sidebar.subheader("⚙️ Painel de Administração")
        novo_usuario = st.sidebar.text_input("➕ Adicionar novo usuário")
        if st.sidebar.button("Adicionar usuário"):
            if novo_usuario and novo_usuario.lower() not in dados["usuarios"]:
                dados["usuarios"][novo_usuario.lower()] = {"admin": False, "blocos": {}, "historico": []}
                salvar_dados(dados)
                st.sidebar.success(f"Usuário {novo_usuario} criado!")

    # ----------------------------
    # Área de colagem da planilha
    # ----------------------------
    st.subheader("📋 Cole os dados da planilha")
    colados = st.text_area("Cole os dados aqui (separados por TAB)", height=300)
    if st.button("📥 Importar dados"):
        if colados.strip():
            try:
                linhas = [linha for linha in colados.strip().split("\n") if linha.strip()]
                df = pd.DataFrame([linha.split("\t") for linha in linhas[1:]], columns=linhas[0].split("\t"))

                # Adiciona os blocos ao usuário atual
                for _, row in df.iterrows():
                    bloco_id = row["SOL"]
                    usuario_info["blocos"][bloco_id] = {
                        "FORNECEDOR": row["FORNECEDOR"],
                        "PAG": row["PAG"],
                        "VALOR": float(row["VALOR"].replace("R$","").replace(".","").replace(",", ".")),
                        "STATUS": row["STATUS"],
                        "DATA": row["DATA"]
                    }
                salvar_dados(dados)
                st.success("✅ Dados importados com sucesso!")
            except Exception as e:
                st.error(f"❌ Erro ao processar os dados: {e}")

    # ----------------------------
    # Exibição dos blocos
    # ----------------------------
    st.subheader("📄 Blocos")
    blocos_dict = usuario_info["blocos"]
    if blocos_dict:
        df_blocos = pd.DataFrame([
            {"SOL": k, **v} for k, v in blocos_dict.items()
        ])

        # Botões de controle por bloco
        for idx, row in df_blocos.iterrows():
            st.markdown(f"### {row['SOL']} - {row['FORNECEDOR']}")
            st.write(f"PAG: {row['PAG']} | VALOR: R$ {row['VALOR']:,.2f} | DATA: {row['DATA']} | STATUS: {row['STATUS']}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"❌ Marcar como em execução {row['SOL']}", key=f"exec_{row['SOL']}"):
                    blocos_dict[row['SOL']]['STATUS'] = "em execução"
                    salvar_dados(dados)
                    st.experimental_rerun()
            with col2:
                if st.button(f"✔ Marcar como executado {row['SOL']}", key=f"done_{row['SOL']}"):
                    blocos_dict[row['SOL']]['STATUS'] = "executado"
                    usuario_info["historico"].append({
                        "id": row['SOL'],
                        "fornecedor": row['FORNECEDOR'],
                        "pag": row['PAG'],
                        "valor": row['VALOR'],
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })
                    salvar_dados(dados)
                    st.experimental_rerun()

    else:
        st.info("Nenhum bloco registrado ainda. Cole os dados da planilha acima ou adicione manualmente.")

    # ----------------------------
    # Histórico lateral
    # ----------------------------
    st.sidebar.subheader("🗓 Histórico de Subprocessos")
    historico = usuario_info.get("historico", [])
    if historico:
        df_hist = pd.DataFrame(historico)
        st.sidebar.dataframe(df_hist)
    else:
        st.sidebar.info("Nenhum subprocesso registrado ainda.")
