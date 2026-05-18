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

def check_completeness_and_hours(state: AgenteState) -> dict: # <-- Alterado para devolver dict
    if not state.ingest_ok:
        return {}

    # Listas locais para evitar concorrência no LangGraph
    novos_logs = ["[check_completeness] A iniciar verificação de completude (E4), carga horária (E5) e prestação de contas..."]
    novas_divergencias = []

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
        # Verifica se a tabela de prestação de contas existe
        if not getattr(state.recursos, 'categorias', None):
            campos_faltantes.append("Prestação de Contas (Tabela de Gastos)")

    # Atividades — só marca E4 se NENHUMA seção narrativa de execução foi preenchida.
    # Relatórios em formato discursivo (PDF narrativo) descrevem atividades no texto
    # em vez de tabelas estruturadas; não penalizar por extração estrutural vazia.
    tem_texto_execucao = bool(
        getattr(state.secoes, 'sintese_execucao', '') or
        getattr(state.secoes, 'resultados_alcancados', '') or
        getattr(state.secoes, 'metodologia', '')
    )
    if (not state.atividades or len(state.atividades) == 0) and not tem_texto_execucao:
        campos_faltantes.append("Atividades Realizadas")

    # Seções textuais
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
        
        check_comp = CheckResult(passou=False, motivo=motivo_e4, evidencia=evidencia_e4)
        novas_divergencias.append(motivo_e4 + f" ({', '.join(campos_faltantes)})")
        novos_logs.append(f"[check_completeness] FALHOU (E4) — Seções em falta: {', '.join(campos_faltantes)}")
    else:
        motivo_e4 = "Todas as seções e campos obrigatórios (incluindo Objetivo e Prestação de Contas) foram identificados."
        check_comp = CheckResult(passou=True, motivo=motivo_e4, evidencia="Relatório 100% completo.")
        novos_logs.append("[check_completeness] OK (E4) — Completude estrutural verificada.")


    # ════════════════════════════════════════════════════════════════════════
    # 2. VERIFICAÇÃO DO SOMATÓRIO DE HORAS (Erro E5)
    # ════════════════════════════════════════════════════════════════════════
    soma_calculada = sum(a.carga_horaria_h for a in state.atividades) if state.atividades else 0
    total_declarado = state.total_horas_declarado if state.total_horas_declarado else 0
    tem_atividades_estruturadas = bool(state.atividades and len(state.atividades) > 0)

    if not tem_atividades_estruturadas:
        # Sem atividades extraídas não é possível calcular a soma — não disparar E5
        motivo_e5 = "Sem atividades estruturadas extraídas para validar carga horária (formato narrativo)."
        evidencia_e5 = "Verificação E5 ignorada — atividades em formato de texto, não tabular."
        check_hor = CheckResult(passou=True, motivo=motivo_e5, evidencia=evidencia_e5)
        novos_logs.append("[check_completeness] SKIP (E5) — Sem atividades estruturadas.")
    elif soma_calculada != total_declarado:
        motivo_e5 = "E5: Inconsistência no somatório da carga horária."
        evidencia_e5 = f"Soma das atividades ({len(state.atividades)} itens): {soma_calculada}h | Total declarado pelo coordenador: {total_declarado}h"
        check_hor = CheckResult(passou=False, motivo=motivo_e5, evidencia=evidencia_e5)
        novas_divergencias.append(motivo_e5)
        novos_logs.append(f"[check_completeness] FALHOU (E5) — {motivo_e5}")
    else:
        motivo_e5 = "O somatório de horas das atividades coincide com o total declarado."
        evidencia_e5 = f"Soma das atividades: {soma_calculada}h | Total declarado: {total_declarado}h"
        check_hor = CheckResult(passou=True, motivo=motivo_e5, evidencia=evidencia_e5)
        novos_logs.append("[check_completeness] OK (E5) — Consistência matemática das horas validada.")


    # ════════════════════════════════════════════════════════════════════════
    # 3. VERIFICAÇÃO DA PRESTAÇÃO DE CONTAS (Cálculo e Limite do Fomento)
    # ════════════════════════════════════════════════════════════════════════
    if state.recursos and state.recursos.projeto_teve_recursos:
        gastos = getattr(state.recursos, 'categorias', [])
        if gastos:
            # Calcula o somatório dos itens gastos na prestação de contas
            soma_gastos = 0.0
            for g in gastos:
                if isinstance(g, dict):
                    soma_gastos += float(g.get("valor", 0.0))
                else:
                    soma_gastos += float(getattr(g, "valor", 0.0))
            
            total_declarado_pc = state.recursos.valor_total_declarado
            
            # Localiza o valor do fomento concedido na base oficial
            valor_fomento = 0.0
            if hasattr(state, 'base_fomentos'):
                fomento_oficial = next((f for f in state.base_fomentos if f.get("protocolo_projeto") == state.protocolo_projeto), None)
                if fomento_oficial:
                    valor_fomento = float(fomento_oficial.get("valor_aprovado", 0.0))
                    
            erros_pc = []
            
            # Margem de tolerância
            if abs(soma_gastos - total_declarado_pc) > 0.01:
                erros_pc.append(f"a soma dos itens (R$ {soma_gastos:,.2f}) difere do total declarado na tabela (R$ {total_declarado_pc:,.2f})")
                
            if soma_gastos > valor_fomento + 0.01:
                erros_pc.append(f"o gasto total (R$ {soma_gastos:,.2f}) excede o limite do fomento aprovado pela PROECE (R$ {valor_fomento:,.2f})")
                
            if erros_pc:
                motivo_pc = "Erro na Prestação de Contas: " + " e ".join(erros_pc) + "."
                novas_divergencias.append(motivo_pc)
                novos_logs.append(f"[check_completeness] FALHOU (Prestação de Contas) — {motivo_pc}")
            else:
                novos_logs.append("[check_completeness] OK — Prestação de contas validada matematicamente e dentro do limite do fomento oficial.")

    # Retorna APENAS o que foi alterado em forma de dict
    return {
        "check_completude": check_comp,
        "check_horas": check_hor,
        "divergencias": novas_divergencias,
        "log": novos_logs
    }