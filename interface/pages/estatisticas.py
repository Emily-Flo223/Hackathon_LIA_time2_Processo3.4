"""
interface/pages/estatisticas.py — Dashboard de Estatísticas e Acurácia do Agente
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path

if not st.session_state.get("autenticado"):
    st.switch_page("app.py")

OUTPUT_DIR = Path("output")
GABARITO_PATH = Path("data/gabarito.csv")

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
    <h1 style="margin: 0; font-family: 'Segoe UI', sans-serif; font-size: 32px; font-weight: 800; color: #007BC0;">Estatísticas do Agente</h1>
    <p style="margin: 0; font-size: 16px; color: #6b7280; margin-top: 4px;">Acurácia, distribuição de erros e comparação com gabarito</p>
</div>
""", unsafe_allow_html=True)

# ── Coleta os resultados gerados pelo agente ──────────────────────────────────
resultados = []
if OUTPUT_DIR.exists():
    for pasta in sorted(OUTPUT_DIR.iterdir()):
        if not pasta.is_dir():
            continue
        json_path = pasta / f"dados_auditoria_{pasta.name}.json"
        if not json_path.exists():
            continue
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            meta = dados.get("metadata", {})
            resultados.append({
                "relatorio": pasta.name,
                "decisao_agente": meta.get("decisao_final", "Desconhecida"),
                "coordenador": meta.get("coordenador", "—"),
                "tipo": meta.get("tipo_relatorio", "—"),
                "titulo": meta.get("titulo_projeto", "—"),
                "fin_passou": dados.get("auditoria_financeira", {}).get("passou", True),
                "comp_passou": dados.get("auditoria_completude", {}).get("passou", True),
                "horas_passou": dados.get("auditoria_horas", {}).get("passou", True),
                "divergencias": len(dados.get("lista_divergencias_acumuladas", [])),
            })
        except Exception:
            pass

if not resultados:
    st.info("Nenhum relatório processado encontrado. Execute o agente primeiro.")
    st.stop()

df = pd.DataFrame(resultados)

# ── Normaliza as decisões para comparação ────────────────────────────────────
def normalizar(d):
    d = d.upper()
    if "APROVAR" in d or "ACERTADO" in d:
        return "APROVAR"
    elif "REELABORA" in d:
        return "DEVOLVER PARA REELABORAÇÃO"
    elif "AJUSTE" in d:
        return "DEVOLVER PARA AJUSTES"
    return d

df["decisao_norm"] = df["decisao_agente"].apply(normalizar)

# ── Carrega gabarito se disponível ────────────────────────────────────────────
gabarito_disponivel = GABARITO_PATH.exists()
acuracia = None
df_comp = None

if gabarito_disponivel:
    try:
        df_gab = pd.read_csv(GABARITO_PATH)
        df_gab["relatorio"] = df_gab["arquivo"].str.replace(r"\.(docx|pdf)$", "", regex=True)
        df_gab["esperado_norm"] = df_gab["categoria_esperada"].str.upper().str.strip()

        def norm_gab(d):
            if "APROVAR" in d:
                return "APROVAR"
            elif "REELABORA" in d:
                return "DEVOLVER PARA REELABORAÇÃO"
            elif "AJUSTE" in d:
                return "DEVOLVER PARA AJUSTES"
            return d

        df_gab["esperado_norm"] = df_gab["esperado_norm"].apply(norm_gab)
        df_comp = df.merge(df_gab[["relatorio", "esperado_norm", "tipo_erro", "descricao_erro"]], on="relatorio", how="left")
        df_comp["acerto"] = df_comp["decisao_norm"] == df_comp["esperado_norm"]
        acuracia = df_comp["acerto"].mean() * 100
    except Exception as e:
        st.warning(f"Não foi possível carregar o gabarito: {e}")

# ── Métricas gerais ────────────────────────────────────────────────────────────
total = len(df)
aprovados = (df["decisao_norm"] == "APROVAR").sum()
ajustes = (df["decisao_norm"] == "DEVOLVER PARA AJUSTES").sum()
reelaboracao = (df["decisao_norm"] == "DEVOLVER PARA REELABORAÇÃO").sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Processados", total)
col2.metric("Aprovados", aprovados, delta=f"{aprovados/total*100:.0f}%")
col3.metric("Devolver p/ Ajustes", ajustes, delta=f"{ajustes/total*100:.0f}%", delta_color="off")
col4.metric("Devolver p/ Reelaboração", reelaboracao, delta=f"{reelaboracao/total*100:.0f}%", delta_color="inverse")

if acuracia is not None:
    st.markdown("---")
    acc_col, _ = st.columns([1, 2])
    with acc_col:
        st.metric("Acurácia do Agente (vs Gabarito)", f"{acuracia:.1f}%",
                  help="Percentual de relatórios cuja decisão do agente coincide com o gabarito esperado.")
        st.progress(acuracia / 100)

st.markdown("---")

# ── Distribuição visual ────────────────────────────────────────────────────────
st.subheader("Distribuição das Decisões")

bar_data = pd.DataFrame({
    "Decisão": ["Aprovados", "Devolver p/ Ajustes", "Devolver p/ Reelaboração"],
    "Quantidade": [int(aprovados), int(ajustes), int(reelaboracao)],
})
st.bar_chart(bar_data.set_index("Decisão"), color="#007BC0")

# ── Tabela comparativa com gabarito ────────────────────────────────────────────
if df_comp is not None:
    st.markdown("---")
    st.subheader("Comparação Agente vs Gabarito")

    df_exib = df_comp[["relatorio", "tipo_erro", "decisao_norm", "esperado_norm", "acerto"]].copy()
    df_exib.columns = ["Relatório", "Tipo Erro", "Decisão Agente", "Esperado (Gabarito)", "Acerto"]
    df_exib["Acerto"] = df_exib["Acerto"].map({True: "✅", False: "❌"})

    acertos_filtro = st.radio("Filtrar:", ["Todos", "Apenas Acertos", "Apenas Erros"], horizontal=True)
    if acertos_filtro == "Apenas Acertos":
        df_exib = df_exib[df_exib["Acerto"] == "✅"]
    elif acertos_filtro == "Apenas Erros":
        df_exib = df_exib[df_exib["Acerto"] == "❌"]

    st.dataframe(df_exib, use_container_width=True, hide_index=True)

# ── Distribuição por tipo de erro (gabarito) ──────────────────────────────────
if gabarito_disponivel and df_comp is not None:
    st.markdown("---")
    st.subheader("Distribuição por Tipo de Erro (Gabarito)")
    tipo_counts = df_comp["tipo_erro"].value_counts().reset_index()
    tipo_counts.columns = ["Tipo de Erro", "Quantidade"]
    st.bar_chart(tipo_counts.set_index("Tipo de Erro"), color="#007BC0")

# ── Auditoria por componente ──────────────────────────────────────────────────
st.markdown("---")
st.subheader("Taxa de Falha por Componente de Auditoria")

falha_fin = (~df["fin_passou"]).sum()
falha_comp = (~df["comp_passou"]).sum()
falha_horas = (~df["horas_passou"]).sum()

comp_data = pd.DataFrame({
    "Componente": ["Consistência Financeira", "Completude Estrutural", "Carga Horária"],
    "Falhas": [int(falha_fin), int(falha_comp), int(falha_horas)],
})
st.bar_chart(comp_data.set_index("Componente"), color="#ef4444")

st.markdown("---")
st.caption("Desenvolvido para otimizar o fluxo de extensão universitária | PROECE - UFMS")
