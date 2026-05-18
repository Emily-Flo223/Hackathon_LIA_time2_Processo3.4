"""
interface/app.py — Ponto de entrada da interface Streamlit com autenticação
"""

import streamlit as st

st.set_page_config(
    page_title="Agente PROECE 3.4",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Usuários sintéticos para teste
USUARIOS = {
    "admin": {"senha": "proece2024", "nome": "Administrador", "perfil": "Admin"},
    "auditor": {"senha": "ufms2024", "nome": "Auditor PROECE", "perfil": "Auditor"},
    "demo": {"senha": "demo", "nome": "Usuário Demo", "perfil": "Visualizador"},
}


def tela_login():
    col_esq, col_centro, col_dir = st.columns([1, 1.2, 1])
    with col_centro:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="font-size: 36px; font-weight: 800; color: #007BC0; margin: 0;">PROECE</h1>
            <p style="font-size: 16px; color: #6b7280; margin-top: 4px;">Pró-Reitoria de Extensão, Cultura e Esporte · UFMS</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("#### Acesso ao Sistema")
            usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")

            if st.button("Entrar", use_container_width=True, type="primary"):
                if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = usuario
                    st.session_state["nome_usuario"] = USUARIOS[usuario]["nome"]
                    st.session_state["perfil_usuario"] = USUARIOS[usuario]["perfil"]
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("Credenciais para teste"):
            st.markdown("""
            | Usuário | Senha | Perfil |
            |---------|-------|--------|
            | `admin` | `proece2024` | Administrador |
            | `auditor` | `ufms2024` | Auditor |
            | `demo` | `demo` | Visualizador |
            """)


# Controle de autenticação
if not st.session_state.get("autenticado"):
    tela_login()
else:
    st.switch_page("pages/home.py")
