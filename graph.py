"""
graph.py — Orquestrador LangGraph do Agente PROECE 3.4
"""

from langgraph.graph import StateGraph, START, END
from state import AgenteState

# Importação dos nossos nós
from nodes.ingest_report import ingest_report
from nodes.extract_structured import extract_structured
from nodes.load_internal_bases import load_internal_bases
from nodes.check_financial import check_financial_consistency
from nodes.check_bolsistas import check_bolsistas_consistency
from nodes.check_completeness import check_completeness_and_hours
from nodes.compose_parecer import compose_parecer
from nodes.emit import emit_artifacts

def build_graph():
    # 1. Inicializa o Grafo com a nossa estrutura de Estado
    workflow = StateGraph(AgenteState)

    # 2. Regista todos os Nós (Workers)
    workflow.add_node("ingest", ingest_report)
    workflow.add_node("extract", extract_structured)
    workflow.add_node("load_bases", load_internal_bases)
    
    # Nós Fiscais (Vão rodar em paralelo)
    workflow.add_node("check_financeiro", check_financial_consistency)
    workflow.add_node("check_bolsistas", check_bolsistas_consistency)
    workflow.add_node("check_completeness", check_completeness_and_hours)
    
    # Nós de Saída
    workflow.add_node("compose", compose_parecer)
    workflow.add_node("emit", emit_artifacts)

    # 3. Define as Arestas (O Caminho / Edges)
    workflow.add_edge(START, "ingest")
    workflow.add_edge("ingest", "extract")
    workflow.add_edge("extract", "load_bases")

    # ── RAMIFICAÇÃO PARALELA (Fan-out) ──
    # A partir do load_bases, o fluxo divide-se em 3 caminhos simultâneos
    workflow.add_edge("load_bases", "check_financeiro")
    workflow.add_edge("load_bases", "check_bolsistas")
    workflow.add_edge("load_bases", "check_completeness")

    # ── JUNÇÃO PARALELA (Fan-in) ──
    # O "compose" só é acionado quando os 3 checks paralelos terminarem
    workflow.add_edge("check_financeiro", "compose")
    workflow.add_edge("check_bolsistas", "compose")
    workflow.add_edge("check_completeness", "compose")

    # Finalização
    workflow.add_edge("compose", "emit")
    workflow.add_edge("emit", END)

    # 4. Compila o Grafo numa Aplicação Executável
    return workflow.compile()