import streamlit as st
import pandas as pd
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ler dados da tabela subprocessos
res = supabase.table("subprocessos").select("*").execute()
df = pd.DataFrame(res.data)

st.dataframe(df)
