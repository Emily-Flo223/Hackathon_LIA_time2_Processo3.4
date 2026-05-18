"""
interface/pages/executar.py — Página para executar o agente diretamente pela interface
"""

import streamlit as st
import subprocess
import sys
from pathlib import Path

if not st.session_state.get("autenticado"):
    st.switch_page("app.py")

if st.session_state.get("perfil_usuario") == "Visualizador":
    st.error("Seu perfil não tem permissão para executar o agente.")
    st.stop()

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

with st.sidebar:
    st.markdown(f"**{st.session_state.get('nome_usuario', 'Usuário')}**")
    st.caption(f"Perfil: {st.session_state.get('perfil_usuario', '')}")
    st.markdown("---")
    st.page_link("pages/home.py", label="Inicio", icon="🏠")
    st.page_link("pages/detalhes.py", label="Detalhes", icon="🔍")
    st.page_link("pages/estatisticas.py", label="Estatísticas", icon="📊")
    st.page_link("pages/executar.py", label="Executar Agente", icon="▶️")
    st.markdown("---")
    if st.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.switch_page("app.py")

st.markdown("""
<div style="border-bottom: 1px solid #e5e7eb; padding-bottom: 15px; margin-bottom: 20px;">
    <h1 style="margin: 0; font-family: 'Segoe UI', sans-serif; font-size: 32px; font-weight: 800; color: #007BC0;">Executar Agente</h1>
    <p style="margin: 0; font-size: 16px; color: #6b7280; margin-top: 4px;">Processa os relatórios da pasta <code>data/</code> e gera os resultados em <code>output/</code></p>
</div>
""", unsafe_allow_html=True)

# ── Status atual da pasta data/ ───────────────────────────────────────────────
relatorios_disponiveis = []
if DATA_DIR.exists():
    relatorios_disponiveis = sorted([
        f for f in DATA_DIR.iterdir()
        if f.is_file()
        and f.name.lower().startswith("relatorio_")
        and "edital" not in f.name.lower()
    ])

relatorios_processados = []
if OUTPUT_DIR.exists():
    relatorios_processados = [d.name for d in OUTPUT_DIR.iterdir() if d.is_dir()]

col1, col2 = st.columns(2)
col1.metric("Relatórios disponíveis em data/", len(relatorios_disponiveis))
col2.metric("Já processados em output/", len(relatorios_processados))

st.markdown("---")

# ── Reprocessar Reelaborações ──────────────────────────────────────────────────
import json

relatorios_reelaboracao = []
if OUTPUT_DIR.exists():
    for pasta in OUTPUT_DIR.iterdir():
        if not pasta.is_dir():
            continue
        jp = pasta / f"dados_auditoria_{pasta.name}.json"
        if not jp.exists():
            continue
        try:
            with open(jp, "r", encoding="utf-8") as f:
                d = json.load(f)
            decisao = d.get("metadata", {}).get("decisao_final", "").upper()
            if "REELABORA" in decisao:
                nome_arquivo = next(
                    (f.name for f in DATA_DIR.iterdir()
                     if f.stem == pasta.name and f.suffix in (".pdf", ".docx")),
                    None
                )
                if nome_arquivo:
                    relatorios_reelaboracao.append(nome_arquivo)
        except Exception:
            pass

if relatorios_reelaboracao:
    with st.container(border=True):
        st.markdown(f"**🔴 {len(relatorios_reelaboracao)} relatório(s) classificado(s) como Reelaboração**")
        st.caption("Esses relatórios tiveram erros graves na análise anterior. Você pode reprocessá-los após corrigir os documentos em `data/`.")

        with st.expander("Ver relatórios para reprocessar"):
            for r in relatorios_reelaboracao:
                st.markdown(f"- `{r}`")

        if st.button("🔄 Reprocessar todos os Reelaboração", type="secondary", use_container_width=True):
            st.session_state["reprocessar_lista"] = relatorios_reelaboracao
            st.session_state["executando"] = True
            st.rerun()

st.markdown("---")

# ── Configuração da execução ──────────────────────────────────────────────────
st.subheader("Configurar Execução")

quantidade = st.slider(
    "Quantidade de relatórios a processar:",
    min_value=1,
    max_value=max(len(relatorios_disponiveis), 1),
    value=min(5, len(relatorios_disponiveis)),
    help="Selecione quantos relatórios serão processados nesta rodada."
)

if relatorios_disponiveis:
    st.info(f"Serão processados os primeiros **{quantidade}** relatórios da pasta `data/`.")
    with st.expander("Ver relatórios que serão processados"):
        for r in relatorios_disponiveis[:quantidade]:
            ja_processado = r.stem in relatorios_processados
            status = "✅ Já processado — será reprocessado" if ja_processado else "🆕 Novo"
            st.markdown(f"- `{r.name}` — {status}")
else:
    st.warning("Nenhum relatório encontrado na pasta `data/`. Verifique se os arquivos estão corretos.")
    st.stop()

st.markdown("---")

# ── Execução ──────────────────────────────────────────────────────────────────
if "executando" not in st.session_state:
    st.session_state["executando"] = False

if not st.session_state["executando"]:
    if st.button("▶️ Iniciar Processamento", type="primary", use_container_width=True):
        st.session_state["executando"] = True
        st.rerun()
else:
    st.info("Processando relatórios... Isso pode levar alguns minutos.")
    log_placeholder = st.empty()
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    logs = []
    processo_ok = False
    erro_msg = ""

    try:
        import os
        lista_reprocessar = st.session_state.pop("reprocessar_lista", None)
        if lista_reprocessar:
            env_vars = {
                "RELATORIOS_ESPECIFICOS": ",".join(lista_reprocessar),
                "PYTHONIOENCODING": "utf-8"
            }
        else:
            env_vars = {"QUANTIDADE_A_EXECUTAR": str(quantidade), "PYTHONIOENCODING": "utf-8"}
        env = {**os.environ, **env_vars}

        proc = subprocess.Popen(
            [sys.executable, "run_graph.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(Path(".").resolve())
        )

        i = 0
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                logs.append(line)
                if "Fila" in line and "/" in line:
                    try:
                        partes = line.split("[Fila ")[1].split("/")
                        atual = int(partes[0])
                        total_str = partes[1].split("]")[0]
                        total = int(total_str)
                        progress_bar.progress(atual / total)
                        status_placeholder.caption(f"Processando {atual}/{total}...")
                    except Exception:
                        pass
                log_placeholder.code("\n".join(logs[-20:]), language=None)

        proc.wait()
        processo_ok = proc.returncode == 0

    except Exception as e:
        erro_msg = str(e)

    st.session_state["executando"] = False

    if processo_ok:
        progress_bar.progress(1.0)
        st.success("Processamento concluído com sucesso! Acesse a **Home** para ver os resultados.")
        with st.expander("Log completo"):
            st.code("\n".join(logs), language=None)
        if st.button("Ir para Home"):
            st.switch_page("pages/home.py")
    else:
        st.error(f"Erro durante o processamento. {erro_msg}")
        with st.expander("Log de erros"):
            st.code("\n".join(logs), language=None)
        if st.button("Tentar novamente"):
            st.rerun()

st.markdown("---")
st.caption("Desenvolvido para otimizar o fluxo de extensão universitária | PROECE - UFMS")
