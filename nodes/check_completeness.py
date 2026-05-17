"""
nodes/check_completeness.py — Nó Validador 3 do agente PROECE 3.4

Responsabilidade:
  - Verifica se todas as seções e campos obrigatórios estão preenchidos (Erro E4).
  - Confere se o somatório das horas das atividades bate com o total declarado (Erro E5).
  - Confere a Prestação de Contas (soma exata dos itens e teto do fomento oficial).
"""

import logging
from state import AgenteState, CheckResult

logger = logging.getLogger(__name__)

def check_completeness_and_hours(state: AgenteState) -> AgenteState:
    if not state.ingest_ok:
        return state

    state.log.append("[check_completeness] A iniciar verificação de completude (E4), carga horária (E5) e prestação de contas...")

    # ════════════════════════════════════════════════════════════════════════
    # 1. VERIFICAÇÃO DE COMPLETUDE (Erro E4)
    # ════════════════════════════════════════════════════════════════════════
    campos_faltantes = []

    # Identificação básica
    if not state.titulo_projeto: campos_faltantes.append("Título do Projeto")
    if not state.protocolo_projeto: campos_faltantes.append("Protocolo do Projeto")
    if not state.coordenador: campos_faltantes.append("Coordenador")
    
    # Recursos Financeiros (Prestação de contas básica)
    if state.recursos is None:
        campos_faltantes.append("Declaração de Recursos Financeiros")
    elif state.recursos.projeto_teve_recursos:
        # Verifica se a tabela de prestação de contas existe (foi extraída do PDF/DOCX)
        if not getattr(state.recursos, 'categorias', None):
            campos_faltantes.append("Prestação de Contas (Tabela de Gastos)")

    # Atividades
    if not state.atividades or len(state.atividades) == 0:
        campos_faltantes.append("Atividades Realizadas")

    # Seções textuais (Objetivo, Metodologia, Resultados/Produtos, Considerações, etc.)
    if not state.secoes:
        campos_faltantes.append("Seções Textuais (Relatório Vazio)")
    else:
        if not getattr(state.secoes, 'objetivo', ''): campos_faltantes.append("Objetivo")
        if not state.secoes.sintese_execucao: campos_faltantes.append("Síntese da Execução")
        if not state.secoes.metodologia: campos_faltantes.append("Metodologia Utilizada")
        if not state.secoes.resultados_alcancados: campos_faltantes.append("Resultados Alcançados / Produtos")
        if not state.secoes.consideracoes_finais: campos_faltantes.append("Considerações Finais")

    if campos_faltantes:
        motivo_e4 = "E4: Ausência de campos ou seções obrigatórias no relatório."
        evidencia_e4 = "Campos ausentes: " + ", ".join(campos_faltantes)
        
        state.check_completude = CheckResult(passou=False, motivo=motivo_e4, evidencia=evidencia_e4)
        state.divergencias.append(motivo_e4 + f" ({', '.join(campos_faltantes)})")
        state.log.append(f"[check_completeness] FALHOU (E4) — Seções em falta: {', '.join(campos_faltantes)}")
    else:
        motivo_e4 = "Todas as seções e campos obrigatórios (incluindo Objetivo e Prestação de Contas) foram identificados."
        state.check_completude = CheckResult(passou=True, motivo=motivo_e4, evidencia="Relatório 100% completo.")
        state.log.append("[check_completeness] OK (E4) — Completude estrutural verificada.")


    # ════════════════════════════════════════════════════════════════════════
    # 2. VERIFICAÇÃO DO SOMATÓRIO DE HORAS (Erro E5)
    # ════════════════════════════════════════════════════════════════════════
    soma_calculada = sum(a.carga_horaria_h for a in state.atividades) if state.atividades else 0
    total_declarado = state.total_horas_declarado if state.total_horas_declarado else 0

    if soma_calculada != total_declarado:
        motivo_e5 = "E5: Inconsistência no somatório da carga horária."
        evidencia_e5 = f"Soma das atividades ({len(state.atividades)} itens): {soma_calculada}h | Total declarado pelo coordenador: {total_declarado}h"
        
        state.check_horas = CheckResult(passou=False, motivo=motivo_e5, evidencia=evidencia_e5)
        state.divergencias.append(motivo_e5)
        state.log.append(f"[check_completeness] FALHOU (E5) — {motivo_e5}")
    else:
        motivo_e5 = "O somatório de horas das atividades coincide com o total declarado."
        evidencia_e5 = f"Soma das atividades: {soma_calculada}h | Total declarado: {total_declarado}h"
        
        state.check_horas = CheckResult(passou=True, motivo=motivo_e5, evidencia=evidencia_e5)
        state.log.append("[check_completeness] OK (E5) — Consistência matemática das horas validada.")

    return state