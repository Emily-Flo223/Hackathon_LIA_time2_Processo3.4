"""
interface/pages/detalhes.py — Tela de detalhes de Entrada e Saída dos Relatórios
"""

import streamlit as st
import json
import pandas as pd
from pathlib import Path

# Definição dos caminhos físicos das pastas do projeto
OUTPUT_DIR = Path("output")

# Título e Cabeçalho customizado de acordo com o padrão institucional
st.markdown("""
<div style="border-bottom: 1px solid #e5e7eb; padding-bottom: 15px; margin-bottom: 20px;">
    <h1 style="margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 32px; font-weight: 800; color: #111827;">Agente PROECE</h1>
    <p style="margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 18px; color: #6b7280; margin-top: 2px;">Processo 3.4: Análise de Relatórios de Ações de Extensão</p>
</div>
""", unsafe_allow_html=True)

# Mapeia os relatórios que já possuem análise do agente gerada
relatorios_analisados = []
if OUTPUT_DIR.exists():
    relatorios_analisados = sorted([
        d.name for d in OUTPUT_DIR.iterdir() if d.is_dir()
    ])

if not relatorios_analisados:
    st.info("Nenhum relatório analisado pelo agente foi localizado. Execute o `run_graph.py` primeiro.")
else:
    # Caixa de seleção para escolher qual relatório inspecionar
    relatorio_selecionado = st.selectbox(
        "Selecione um relatório para inspecionar os detalhes:",
        relatorios_analisados
    )
    
    st.markdown("---")
    
    # Caminhos para os arquivos de saída do relatório escolhido
    pasta_relatorio = OUTPUT_DIR / relatorio_selecionado
    json_path = pasta_relatorio / f"dados_auditoria_{relatorio_selecionado}.json"
    md_path = pasta_relatorio / f"parecer_auditoria_{relatorio_selecionado}.md"
    email_path = pasta_relatorio / f"minuta_email_{relatorio_selecionado}.txt"

    # Carrega os dados estruturados do JSON
    dados_json = None
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dados_json = json.load(f)
        except Exception as e:
            st.error(f"Erro ao ler os dados estruturados: {str(e)}")

    if dados_json:
        metadata = dados_json.get("metadata", {})
        
        # ALTERAÇÃO SOLICITADA: Mapeamento estrito das chaves exatas fornecidas
        protocolo_detectado = metadata.get("protocolo_projeto") or dados_json.get("protocolo_projeto", "Não identificado")
        tipo_detectado = metadata.get("tipo_relatorio") or dados_json.get("tipo_relatorio", "Não identificado")

        # ══════════════════════════════════════════════════════════════════════════
        # 🏢 SEÇÃO 1: INFORMAÇÕES DE ENTRADA (Dados identificados e extraídos)
        # ══════════════════════════════════════════════════════════════════════════
        st.subheader("📥 Informações de Entrada (Dados Extraídos do Relatório)")
        
        # Painel em colunas com os metadados principais extraídos
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📌 Título do Projeto:** {metadata.get('titulo_projeto', 'Não identificado')}")
            st.markdown(f"**👤 Coordenador:** {metadata.get('coordenador', 'Não identificado')}")
            st.markdown(f"**🆔 ID do Relatório:** `{metadata.get('id_relatorio', relatorio_selecionado)}`")
        with col2:
            st.markdown(f"**🔢 Protocolo do Projeto:** `{protocolo_detectado}`")
            st.markdown(f"**📊 Tipo de Relatório:** {tipo_detectado}")
            st.markdown(f"**📅 Decisão do Agente:** `{metadata.get('decisao_final', 'Não definida')}`")

        st.markdown("<br>", unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════════════════════
        # ⚖️ SEÇÃO 2: AUDITORIAS E VERIFICAÇÕES (Mapeamento de Divergências)
        # ══════════════════════════════════════════════════════════════════════════
        st.subheader("⚖️ Resultados das Validações (Filtros e Cruzamentos)")
        
        # Cria cards para expor as três frentes de auditoria paralela do LangGraph
        auditorias = [
            ("Completude Estrutural", dados_json.get("auditoria_completude", {})),
            ("Consistência Financeira", dados_json.get("auditoria_financeira", {})),
            ("Carga Horária das Atividades", dados_json.get("auditoria_horas", {}))
        ]
        
        cols_aud = st.columns(3)
        for idx, (nome_aud, dados_aud) in enumerate(auditorias):
            with cols_aud[idx]:
                passou = dados_aud.get("passou", True)
                if passou:
                    st.success(f"**{nome_aud}**\n\n🟢 Status: Em conformidade")
                else:
                    st.error(f"**{nome_aud}**\n\n🔴 Status: Divergência encontrada")
                    st.markdown(f"**Motivo:** *{dados_aud.get('motivo', '')}*")
                    st.caption(f"**Evidência:** {dados_aud.get('evidencia', '')}")

        # Lista expandida de todas as divergências concatenadas pelo reducer do LangGraph
        divergencias = dados_json.get("lista_divergencias_acumuladas", [])
        if divergencias:
            with st.expander("⚠️ Ver Lista Completa de Divergências Acumuladas", expanded=True):
                for div in divergencias:
                    st.markdown(f"- {div}")
        else:
            st.success("Nenhuma divergência ou desconformidade foi acumulada para este processo.")

        st.markdown("---")

        # ══════════════════════════════════════════════════════════════════════════
        # 📤 SEÇÃO 3: ARTEFATOS DE SAÍDA (Parecer Markdown e Minuta do E-mail)
        # ══════════════════════════════════════════════════════════════════════════
        st.subheader("📤 Artefatos de Saída (Resultados Finais Gerados)")
        
        tab_parecer, tab_email, tab_json_bruto = st.tabs([
            "📄 Parecer Técnico (.md)", 
            "✉️ Minuta de E-mail de Notificação (.txt)", 
            "⚙️ Estrutura de Dados Bruta (.json)"
        ])
        
        with tab_parecer:
            if md_path.exists():
                try:
                    with open(md_path, "r", encoding="utf-8") as f:
                        conteudo_md = f.read()
                    st.markdown(conteudo_md)
                except Exception as e:
                    st.error(f"Erro ao carregar o parecer técnico: {str(e)}")
            else:
                st.warning("O arquivo de parecer em Markdown não foi localizado para esta pasta.")
                
            with tab_email:
                if email_path.exists():
                    try:
                        with open(email_path, "r", encoding="utf-8") as f:
                            conteudo_email = f.read()
                        st.text_area(label="Texto da Minuta Regulamentar", value=conteudo_email, height=350, label_visibility="collapsed")
                    except Exception as e:
                        st.error(f"Erro ao carregar a minuta de e-mail: {str(e)}")
                else:
                    st.warning("O arquivo contendo a minuta do e-mail não foi localizado para esta pasta.")

            with tab_json_bruto:
                st.json(dados_json)

    st.markdown("---")
    st.caption("Desenvolvido para otimizar o fluxo de extensão universitária | PROECE - UFMS")