"""
interface/app.py — Ponto de entrada da interface Streamlit
"""

import streamlit as st

# A configuração da página DEVE ser sempre o primeiro comando do Streamlit
st.set_page_config(
    page_title="Agente PROECE 3.4",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Como estamos a usar a estrutura "pages/", o app.py pode ser usado apenas 
# para inicializar variáveis de estado (session_state) ou redirecionar automaticamente.
# Aqui vamos redirecionar logo para a página inicial (home) para uma experiência fluida.

st.switch_page("pages/home.py")