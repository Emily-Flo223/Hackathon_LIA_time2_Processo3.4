"""
interface/pages/home.py — Tela inicial com Kanban Reorganizado e Planilha Geral
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path

# Definição dos caminhos físicos das pastas do projeto
OUTPUT_DIR = Path("output")
REVIEWED_DIR = Path("reviewed")  # Pasta para os processos já revisados pelo usuário

# 1. Mapeamento dos resultados do agente (Coluna: Analisar)
relatorios_para_analisar = []
if OUTPUT_DIR.exists():
    relatorios_para_analisar = sorted([
        d.name for d in OUTPUT_DIR.iterdir() if d.is_dir()
    ])

# 2. Mapeamento dos relatórios já revisados pelo usuário (Coluna: Analisados)
relatorios_revisados = []
if REVIEWED_DIR.exists():
    relatorios_revisados = sorted([
        d.name for d in REVIEWED_DIR.iterdir() if d.is_dir()
    ])

# Título e Cabeçalho (Customizado idêntico à imagem, sem o LIA)
st.markdown("""
<div style="border-bottom: 1px solid #e5e7eb; padding-bottom: 15px; margin-bottom: 20px;">
    <h1 style="margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 32px; font-weight: 800; color: #007BC0;">PROECE - UFMS</h1>
    <p style="margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 18px; color: #6b7280; margin-top: 2px;">Pró-Reitoria de Extensão, Cultura e Esporte</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Bem-vindo(a) ao **Sistema Multi-Agente de Auditoria de Relatórios de Extensão**. 
Esta plataforma automatiza a conferência técnica, financeira e estrutural dos projetos submetidos à Pró-Reitoria de Extensão, Cultura e Esporte (PROECE/UFMS).
""")

# Secção de Métricas Rápidas atualizada com os novos escopos das colunas
st.subheader("Visão Geral do Sistema")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="🔍 Relatórios para Analisar (Agente)", value=len(relatorios_para_analisar))
with col2:
    st.metric(label="✅ Relatórios Analisados (Usuário)", value=len(relatorios_revisados))
with col3:
    st.info("⏱️ **Tempo Poupado**\n\nRedução drástica no trabalho manual.")

st.markdown("---")

# Exibição do Novo Kanban (Analisar vs Analisados)
col_esq, col_dir = st.columns(2)

with col_esq:
    st.subheader("🔍 Analisar")
    
    # Filtro para selecionar os relatórios na coluna Kanban (Analisar)
    filtro_status = st.selectbox(
        "Filtrar por classificação:",
        ["Todos", "APROVADO", "DEVOLVER PARA AJUSTE", "DEVOLVER PARA REELABORAÇÃO"],
        key="filtro_analisar",
        label_visibility="collapsed" 
    )
    
    with st.container(height=450):
        if relatorios_para_analisar:
            relatorios_mostrados = 0
            for r in relatorios_para_analisar:
                # Extrai a decisão final do arquivo JSON gerado pelo agente
                decisao = "Desconhecido"
                json_path = OUTPUT_DIR / r / f"dados_auditoria_{r}.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                            decisao = dados.get("metadata", {}).get("decisao_final", "Desconhecido")
                    except Exception:
                        pass
                
                # Aplica a lógica do filtro selecionado
                decisao_upper = decisao.upper()
                mostrar_card = True
                if filtro_status != "Todos":
                    if filtro_status == "APROVADO" and not ("APROVAR" in decisao_upper or "ACERTADO" in decisao_upper):
                        mostrar_card = False
                    elif filtro_status == "DEVOLVER PARA AJUSTE" and "AJUSTES" not in decisao_upper:
                        mostrar_card = False
                    elif filtro_status == "DEVOLVER PARA REELABORAÇÃO" and "REELABORA" not in decisao_upper:
                        mostrar_card = False
                
                # Só desenha o card se passar no filtro
                if mostrar_card:
                    relatorios_mostrados += 1
                    
                    # Formatação visual da tag baseada na decisão do agente
                    if "APROVAR" in decisao_upper or "ACERTADO" in decisao_upper:
                        badge = "🟢 **Aprovado**"
                    elif "AJUSTES" in decisao_upper:
                        badge = "🟡 **Ajustes**"
                    elif "REELABORA" in decisao_upper:
                        badge = "🔴 **Reelaboração**"
                    else:
                        badge = f"⚪ **{decisao}**"

                    with st.container(border=True):
                        cols = st.columns([6, 4], vertical_alignment="center")
                        with cols[0]:
                            st.markdown(f"🗂️ **{r}**")
                            st.markdown(badge)
                        with cols[1]:
                            if st.button("Analisar", key=f"btn_analisar_{r}", use_container_width=True):
                                st.toast(f"Visualizando resultados de {r}...")
            
            # Mensagem caso o filtro esconda todos os relatórios
            if relatorios_mostrados == 0:
                st.write(f"Nenhum relatório encontrado para o filtro: **{filtro_status}**.")
        else:
            st.write("Nenhum resultado do agente pendente de análise.")

with col_dir:
    st.subheader("✅ Analisados")
    
    # Filtro para selecionar os relatórios na coluna Kanban (Analisados)
    filtro_status_revisados = st.selectbox(
        "Filtrar por classificação:",
        ["Todos", "APROVADO", "DEVOLVER PARA AJUSTE", "DEVOLVER PARA REELABORAÇÃO"],
        key="filtro_analisados",
        label_visibility="collapsed" 
    )

    with st.container(height=450):
        if relatorios_revisados:
            relatorios_mostrados_revisados = 0
            for r in relatorios_revisados:
                # Busca metadados históricos caso existam na pasta reviewed
                status_revisao = "Revisado com Sucesso"
                decisao = "Revisado"
                json_path = REVIEWED_DIR / r / f"dados_auditoria_{r}.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r", encoding="utf-8") as f:
                            dados = json.load(f)
                            decisao = dados.get("metadata", {}).get("decisao_final", "Revisado")
                            status_revisao = f"Decisão Final: {decisao}"
                    except Exception:
                        pass

                # Aplica a lógica do filtro selecionado
                decisao_upper = decisao.upper()
                mostrar_card = True
                if filtro_status_revisados != "Todos":
                    if filtro_status_revisados == "APROVADO" and not ("APROVAR" in decisao_upper or "ACERTADO" in decisao_upper):
                        mostrar_card = False
                    elif filtro_status_revisados == "DEVOLVER PARA AJUSTE" and "AJUSTES" not in decisao_upper:
                        mostrar_card = False
                    elif filtro_status_revisados == "DEVOLVER PARA REELABORAÇÃO" and "REELABORA" not in decisao_upper:
                        mostrar_card = False
                
                # Só desenha o card se passar no filtro
                if mostrar_card:
                    relatorios_mostrados_revisados += 1
                    with st.container(border=True):
                        st.markdown(f"📦 **{r}**")
                        st.caption(status_revisao)
            
            # Mensagem caso o filtro esconda todos os relatórios
            if relatorios_mostrados_revisados == 0:
                st.write(f"Nenhum relatório encontrado para o filtro: **{filtro_status_revisados}**.")
        else:
            st.write("Nenhum processo foi movido para revisado pelo usuário ainda.")

st.markdown("---")

# ── SEÇÃO SUBSTITUÍDA: PLANILHA GERAL CONSOLIDADA (.XLSX) ──
st.subheader("📊 Planilha Geral Consolidada")

consolidado_path = OUTPUT_DIR / "consolidado_auditoria.xlsx"

if consolidado_path.exists():
    try:
        # Divide a visualização em abas correspondentes às abas reais do Excel
        tab_div, tab_est = st.tabs(["📋 Aba: Divergências Encontradas", "📈 Aba: Estatísticas de Execução"])
        
        with tab_div:
            df_div = pd.read_excel(consolidado_path, sheet_name="Divergencias")
            st.dataframe(df_div, use_container_width=True)
            
        with tab_est:
            df_est = pd.read_excel(consolidado_path, sheet_name="Estatisticas")
            st.dataframe(df_est, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro ao ler os dados do arquivo Excel consolidado: {str(e)}")
else:
    st.info("A planilha máster 'consolidado_auditoria.xlsx' ainda não foi gerada na pasta 'output/'.")

st.markdown("---")

# Secção de Funcionamento
st.subheader("Como funciona o Agente?")
st.markdown("""
O nosso motor inteligente divide o processo em etapas paralelas para máxima eficiência:
1. **Ingestão** Lê os ficheiros PDF/DOCX e extrai o texto bruto, convertendo-o em um formato estruturado para análise.
2. **Extração LLM:** Estrutura os dados brutos utilizando inteligência artificial.
3. **Auditoria Paralela:** * 💰 *Consistência Financeira:* Cruza valores com os fomentos oficiais.
    * 🎓 *Validação de Bolsistas:* Confirma o vínculo e a vigência no Edital.
    * 🏗️ *Completude:* Verifica secções obrigatórias e somatórios de carga horária.
4. **Parecer Automático:** Emite a decisão (Aprovar, Ajustes ou Reelaboração) e gera a minuta de e-mail.
""")

# Rodapé institucional
st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("Desenvolvido para otimizar o fluxo de extensão universitária | PROECE - UFMS")