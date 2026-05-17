"""
nodes/check_financial.py — Nó Validador 1 do agente PROECE 3.4

Responsabilidade:
  - Cruza state.recursos.valor_total_declarado com a state.base_fomentos.
  - Verifica tolerância de 1% de divergência.
  - Popula state.check_financeiro com o CheckResult apropriado.
  - Adiciona o erro em state.divergencias se falhar.
"""

import logging
from state import AgenteState, CheckResult

logger = logging.getLogger(__name__)

def check_financial_consistency(state: AgenteState) -> AgenteState:
    """
    Verifica a consistência financeira do relatório face à base oficial.
    Atualiza state.check_financeiro e state.divergencias.
    """
    # Se a ingestão ou extração falharam, pulamos a validação
    if not state.ingest_ok:
        state.log.append("[check_financial] Ignorado pois ingest_ok=False")
        return state

    state.log.append("[check_financial] A iniciar verificação financeira (cruzamento com fomentos)...")

    protocolo = state.protocolo_projeto
    declarado = state.recursos.valor_total_declarado if state.recursos else 0.0
    declarou_recurso = state.recursos.projeto_teve_recursos if state.recursos else False

    # Procura o protocolo na base oficial de fomentos
    fomento_oficial = next((f for f in state.base_fomentos if f["protocolo_projeto"] == protocolo), None)

    # ── CENÁRIO A: Projeto declarou recursos, mas NÃO existe na base oficial ──
    if declarou_recurso and not fomento_oficial:
        motivo = "E1: O projeto declarou recursos, mas não consta na base oficial de fomentos concedidos."
        evidencia = f"Valor declarado no relatório: R$ {declarado:,.2f} | Valor na base PROECE: Inexistente"
        
        state.check_financeiro = CheckResult(passou=False, motivo=motivo, evidencia=evidencia)
        state.divergencias.append(motivo)
        state.log.append(f"[check_financial] FALHOU — {motivo}")

    # ── CENÁRIO B: Projeto EXISTE na base oficial ──
    elif fomento_oficial:
        valor_oficial = fomento_oficial.get("valor_aprovado", 0.0)
        
        # B.1: Omissão (Esqueceu-se de declarar o dinheiro recebido)
        if not declarou_recurso and valor_oficial > 0:
            motivo = "E1: Relatório omitiu recursos, mas a base oficial indica que houve fomento."
            evidencia = f"O coordenador marcou que o projeto não teve recursos, mas a base oficial regista fomento de R$ {valor_oficial:,.2f}."
            
            state.check_financeiro = CheckResult(passou=False, motivo=motivo, evidencia=evidencia)
            state.divergencias.append(motivo)
            state.log.append(f"[check_financial] FALHOU — {motivo}")
        
        # B.2: Verificação do Limite de Tolerância (Erro E1 do Gabarito)
        elif declarou_recurso:
            # Proteção contra divisão por zero
            divergencia_pct = abs(declarado - valor_oficial) / valor_oficial if valor_oficial > 0 else 1.0
            
            # Tolerância estrita de 1% (0.01)
            if divergencia_pct > 0.01:
                motivo = f"Erro E1: Valor declarado diverge do concedido em mais de 1% (Divergência: {(divergencia_pct*100):.2f}%)."
                evidencia = f"Declarado: R$ {declarado:,.2f} | Oficial: R$ {valor_oficial:,.2f}"
                
                state.check_financeiro = CheckResult(passou=False, motivo=motivo, evidencia=evidencia)
                state.divergencias.append(motivo)
                state.log.append(f"[check_financial] FALHOU — {motivo}")
            else:
                # Tudo certo! Dentro da margem de erro.
                motivo = "Consistência financeira verificada com sucesso (dentro da tolerância de 1%)."
                evidencia = f"Declarado: R$ {declarado:,.2f} | Oficial: R$ {valor_oficial:,.2f}"
                
                state.check_financeiro = CheckResult(passou=True, motivo=motivo, evidencia=evidencia)
                state.log.append(f"[check_financial] OK — {motivo}")

    # ── CENÁRIO C: Não declarou recursos e não tem nada na base (Correto) ──
    else:
        motivo = "Projeto sem recursos financeiros, alinhado com a base oficial."
        state.check_financeiro = CheckResult(passou=True, motivo=motivo, evidencia="Declarado: Sem recursos | Oficial: Sem recursos")
        state.log.append(f"[check_financial] OK — {motivo}")

    return state