"""
interface/pages/detalhes.py — Tela de detalhes de Entrada e Saída dos Relatórios
"""

import streamlit as st
import json
import shutil
from pathlib import Path

if not st.session_state.get("autenticado"):
    st.switch_page("app.py")

OUTPUT_DIR = Path("output")
REVIEWED_DIR = Path("reviewed")

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
    <h1 style="margin: 0; font-family: 'Segoe UI', sans-serif; font-size: 32px; font-weight: 800; color: #111827;">Agente PROECE</h1>
    <p style="margin: 0; font-size: 18px; color: #6b7280; margin-top: 2px;">Processo 3.4: Análise de Relatórios de Ações de Extensão</p>
</div>
""", unsafe_allow_html=True)

relatorios_analisados = []
if OUTPUT_DIR.exists():
    relatorios_analisados = sorted([d.name for d in OUTPUT_DIR.iterdir() if d.is_dir()])

if not relatorios_analisados:
    st.info("Nenhum relatório analisado pelo agente foi localizado. Execute o agente primeiro.")
    st.stop()

# Seleciona o relatório (com pré-seleção vinda da home)
default_idx = 0
if "relatorio_selecionado" in st.session_state:
    nome = st.session_state.pop("relatorio_selecionado")
    if nome in relatorios_analisados:
        default_idx = relatorios_analisados.index(nome)

relatorio_selecionado = st.selectbox(
    "Selecione um relatório para inspecionar os detalhes:",
    relatorios_analisados,
    index=default_idx
)

st.markdown("---")

pasta_relatorio = OUTPUT_DIR / relatorio_selecionado
json_path   = pasta_relatorio / f"dados_auditoria_{relatorio_selecionado}.json"
md_path     = pasta_relatorio / f"parecer_auditoria_{relatorio_selecionado}.md"
email_path  = pasta_relatorio / f"minuta_email_{relatorio_selecionado}.txt"

pasta_destino    = REVIEWED_DIR / relatorio_selecionado
anotacao_path    = pasta_destino / f"anotacao_humana_{relatorio_selecionado}.txt"
email_edit_path  = pasta_relatorio / f"minuta_email_{relatorio_selecionado}_editado.txt"

dados_json = None
if json_path.exists():
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            dados_json = json.load(f)
    except Exception as e:
        st.error(f"Erro ao ler os dados estruturados: {e}")

if not dados_json:
    st.warning("Arquivo de dados não encontrado para este relatório.")
    st.stop()

metadata        = dados_json.get("metadata", {})
protocolo       = metadata.get("protocolo_projeto") or dados_json.get("protocolo_projeto", "Não identificado")
tipo            = metadata.get("tipo_relatorio") or dados_json.get("tipo_relatorio", "Não identificado")
decisao_final   = metadata.get("decisao_final", "Não definida")
decisao_upper   = decisao_final.upper()
ja_revisado     = pasta_destino.exists()

# ── Banner de decisão ──────────────────────────────────────────────────────────
if "APROVAR" in decisao_upper or "ACERTADO" in decisao_upper:
    st.success(f"**Decisão do Agente: {decisao_final}**")
elif "REELABORA" in decisao_upper:
    st.error(f"**Decisão do Agente: {decisao_final}**")
else:
    st.warning(f"**Decisão do Agente: {decisao_final}**")

# ── Bloco de revisão humana ────────────────────────────────────────────────────
if ja_revisado:
    col_info, col_btn = st.columns([7, 3])
    with col_info:
        st.info("Este relatório já foi movido para **Analisados**.")
        if anotacao_path.exists():
            anotacao_salva = anotacao_path.read_text(encoding="utf-8").strip()
            if anotacao_salva:
                st.caption(f"📝 Anotação do auditor: *{anotacao_salva}*")
    with col_btn:
        if st.button("↩️ Devolver para Reavaliação", use_container_width=True):
            try:
                shutil.rmtree(str(pasta_destino))
                st.success("Relatório devolvido para reavaliação.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao devolver: {e}")
else:
    with st.container(border=True):
        st.markdown("**Marcar como Analisado**")
        anotacao_input = st.text_area(
            "Anotação do auditor (opcional):",
            placeholder="Descreva aqui sua justificativa, observações ou comentários sobre esta análise...",
            height=80,
            key=f"anotacao_{relatorio_selecionado}"
        )
        if st.button("✅ Confirmar e mover para Analisados", type="primary", use_container_width=True):
            try:
                REVIEWED_DIR.mkdir(exist_ok=True)
                shutil.copytree(str(pasta_relatorio), str(pasta_destino))
                if anotacao_input.strip():
                    anotacao_path.write_text(anotacao_input.strip(), encoding="utf-8")
                st.success(f"Relatório **{relatorio_selecionado}** movido para Analisados!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao mover relatório: {e}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 1: INFORMAÇÕES EXTRAÍDAS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📥 Informações Extraídas do Relatório")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**Título do Projeto:** {metadata.get('titulo_projeto', 'Não identificado')}")
    st.markdown(f"**Coordenador:** {metadata.get('coordenador', 'Não identificado')}")
    st.markdown(f"**ID do Relatório:** `{metadata.get('id_relatorio', relatorio_selecionado)}`")
with col2:
    st.markdown(f"**Protocolo do Projeto:** `{protocolo}`")
    st.markdown(f"**Tipo de Relatório:** {tipo}")
    st.markdown(f"**ID de Execução:** `{metadata.get('execution_id', '—')[:8]}...`")

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 2: AUDITORIAS
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("⚖️ Resultados das Validações")

auditorias = [
    ("Completude Estrutural",        dados_json.get("auditoria_completude", {})),
    ("Consistência Financeira",      dados_json.get("auditoria_financeira", {})),
    ("Carga Horária das Atividades", dados_json.get("auditoria_horas", {})),
]

cols_aud = st.columns(3)
for idx, (nome_aud, dados_aud) in enumerate(auditorias):
    with cols_aud[idx]:
        if dados_aud.get("passou", True):
            st.success(f"**{nome_aud}**\n\n🟢 Em conformidade")
        else:
            st.error(f"**{nome_aud}**\n\n🔴 Divergência encontrada")
            st.markdown(f"**Motivo:** *{dados_aud.get('motivo', '')}*")
            st.caption(f"**Evidência:** {dados_aud.get('evidencia', '')}")

divergencias = dados_json.get("lista_divergencias_acumuladas", [])
if divergencias:
    with st.expander("⚠️ Lista Completa de Divergências", expanded=True):
        for div in divergencias:
            st.markdown(f"- {div}")
else:
    st.success("Nenhuma divergência acumulada para este processo.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SEÇÃO 3: ARTEFATOS DE SAÍDA
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📤 Artefatos de Saída")

tab_parecer, tab_email, tab_json_bruto = st.tabs([
    "📄 Parecer Técnico (.md)",
    "✉️ Minuta de E-mail (.txt)",
    "⚙️ Dados Brutos (.json)",
])

# ── Aba: Parecer ──────────────────────────────────────────────────────────────
with tab_parecer:
    if md_path.exists():
        try:
            conteudo_md = md_path.read_text(encoding="utf-8")
            st.markdown(conteudo_md)
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                label="⬇️ Baixar Parecer (.md)",
                data=conteudo_md.encode("utf-8"),
                file_name=f"parecer_{relatorio_selecionado}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Erro ao carregar o parecer: {e}")
    else:
        st.warning("Arquivo de parecer não localizado.")

# ── Aba: E-mail editável ──────────────────────────────────────────────────────
with tab_email:
    # Usa versão editada se existir, caso contrário a original do agente
    if email_edit_path.exists():
        conteudo_email = email_edit_path.read_text(encoding="utf-8")
        st.caption("✏️ Você está visualizando a versão **editada** deste e-mail.")
    elif email_path.exists():
        conteudo_email = email_path.read_text(encoding="utf-8")
    else:
        conteudo_email = ""

    if conteudo_email:
        email_editado = st.text_area(
            "Edite o conteúdo do e-mail antes de enviar:",
            value=conteudo_email,
            height=400,
            key=f"email_edit_{relatorio_selecionado}",
        )

        col_salvar, col_resetar, col_baixar = st.columns(3)

        with col_salvar:
            if st.button("💾 Salvar alterações", use_container_width=True, type="primary"):
                try:
                    email_edit_path.write_text(email_editado, encoding="utf-8")
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

        with col_resetar:
            if email_edit_path.exists():
                if st.button("↩️ Restaurar original", use_container_width=True):
                    try:
                        email_edit_path.unlink()
                        st.info("Versão original restaurada.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao restaurar: {e}")

        with col_baixar:
            st.download_button(
                label="⬇️ Baixar E-mail (.txt)",
                data=email_editado.encode("utf-8"),
                file_name=f"email_{relatorio_selecionado}.txt",
                mime="text/plain",
                use_container_width=True,
            )
    else:
        st.warning("Arquivo de e-mail não localizado.")

# ── Aba: JSON ─────────────────────────────────────────────────────────────────
with tab_json_bruto:
    st.json(dados_json)
    json_bytes = json.dumps(dados_json, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        label="⬇️ Baixar Dados (.json)",
        data=json_bytes,
        file_name=f"dados_{relatorio_selecionado}.json",
        mime="application/json",
        use_container_width=True,
    )

st.markdown("---")
st.caption("Desenvolvido para otimizar o fluxo de extensão universitária | PROECE - UFMS")
