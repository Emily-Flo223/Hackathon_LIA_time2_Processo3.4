"""
run_graph.py — Script principal para testar o Grafo do Agente com limite de relatórios
"""

import os
import uuid
from pathlib import Path
from graph import build_graph
from state import AgenteState
from utils.logger import get_structured_logger

# Inicializa o logger estruturado para o orquestrador principal
json_logger = get_structured_logger("run_graph")

# ── CONFIGURAÇÃO DE QUANTIDADE ──────────────────────────────────────────────
# Altere este número para controlar quantos relatórios quer rodar por vez!
QUANTIDADE_A_EXECUTAR = 30  
# ────────────────────────────────────────────────────────────────────────────

def executar_auditoria_langgraph(caminho_relatorio: Path, app):
    # Gera um ID único de execução (UUID v4) para rastreamento nos logs estruturados
    execution_id = str(uuid.uuid4())
    
    # Grava o log estruturado em JSON de início da auditoria
    json_logger.info(
        "Iniciando auditoria via LangGraph", 
        extra={"execution_id": execution_id, "arquivo": caminho_relatorio.name}
    )
    
    print(f"\nIniciando Auditoria via LangGraph para: {caminho_relatorio.name} (ID: {execution_id[:8]})")
    
    # Estado Inicial com o caminho do ficheiro atual e o identificador de execução universal
    estado_inicial = AgenteState(
        arquivo_path=str(caminho_relatorio),
        execution_id=execution_id
    )
    
    # Invoca o Grafo
    estado_final = app.invoke(estado_inicial)
    
    # Exibe um resumo rápido no terminal para acompanhamento
    decisao = estado_final.get('decisao', 'Não definida')
    
    # Grava o log estruturado em JSON com a decisão tomada pelo Agente
    json_logger.info(
        f"Auditoria finalizada com decisão: {decisao}", 
        extra={"execution_id": execution_id, "arquivo": caminho_relatorio.name}
    )
    
    print(f"Decisao Final para {caminho_relatorio.name}: {decisao}")

def main():
    data_dir = Path("data")
    
    if not data_dir.exists():
        print(f"ERRO: Pasta '{data_dir}' nao encontrada na raiz do projeto.")
        return

    # Procura estritamente por arquivos que comecem com 'relatorio_' 
    # e garante que o ficheiro do edital é ignorado, protegendo a execução.
    todos_relatorios = sorted([
        f for f in data_dir.iterdir() 
        if f.is_file() 
        and f.name.lower().startswith("relatorio_") 
        and "edital" not in f.name.lower()
    ])

    total_encontrados = len(todos_relatorios)
    if total_encontrados == 0:
        print("ERRO: Nenhum relatorio comecando com 'relatorio_' foi localizado na pasta 'data'.")
        return

    # Se RELATORIOS_ESPECIFICOS estiver definido, processa só esses arquivos
    especificos = os.environ.get("RELATORIOS_ESPECIFICOS", "").strip()
    if especificos:
        nomes = [n.strip() for n in especificos.split(",") if n.strip()]
        relatorios_selecionados = [data_dir / n for n in nomes if (data_dir / n).exists()]
        print(f"Modo reprocessamento: {len(relatorios_selecionados)} relatório(s) especificado(s).")
    else:
        relatorios_selecionados = todos_relatorios[:QUANTIDADE_A_EXECUTAR]
    
    print(f"======================================================================")
    print(f"Foram encontrados {total_encontrados} relatorios no total.")
    print(f"Configurado para executar os primeiros {len(relatorios_selecionados)} da fila.")
    print(f"======================================================================")

    # Compila o grafo apenas uma vez antes do loop de lote
    app = build_graph()

    # Executa a pipeline do LangGraph relatório por relatório
    for idx, caminho in enumerate(relatorios_selecionados, start=1):
        print(f"[Fila {idx}/{len(relatorios_selecionados)}] Processando...")
        try:
            executar_auditoria_langgraph(caminho, app)
        except Exception as e:
            print(f"ERRO: Falha ao processar {caminho.name}: {str(e)}")

    print(f"\n{'-'*80}")
    print(f"Execucao em lote finalizada com sucesso!")
    print(f"Todos os relatorios processados geraram pastas individuais em 'output/'.")
    print(f"A planilha 'output/consolidado_auditoria.xlsx' foi totalmente atualizada.")
    print(f"{'-'*80}")

if __name__ == "__main__":
    main()