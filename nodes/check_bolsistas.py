"""
nodes/check_bolsistas.py — Nó Validador 2 do agente PROECE 3.4

Responsabilidade:
  - Cruza os nomes declarados em state.bolsistas com state.base_bolsistas (Edital).
  - Valida o NOME DO BOLSISTA e o TÍTULO DO PROJETO simultaneamente.
  - E2: Bolsista não encontrado no edital para aquele projeto específico (Fraude).
  - E3: Período de vigência declarado diferente do oficial.
"""

import logging
from state import AgenteState, CheckResult

logger = logging.getLogger(__name__)

def check_bolsistas_consistency(state: AgenteState) -> dict: # <-- Alterado para devolver dict
    if not state.ingest_ok:
        return {}

    # Criamos listas LOCAIS para não causar conflitos de memória no LangGraph
    novos_logs = ["[check_bolsistas] A iniciar verificação de bolsistas..."]
    novas_divergencias = []
    novos_checks = []

    if not state.bolsistas:
        novos_logs.append("[check_bolsistas] OK — Projeto sem bolsistas.")
        return {"log": novos_logs}

    titulo_projeto_declarado = state.titulo_projeto.strip().lower()

    for bolsista_declarado in state.bolsistas:
        nome_declarado = bolsista_declarado.nome.strip()
        
        # 1. Procura o bolsista no EDITAL pelo NOME e pelo TÍTULO DO PROJETO
        bolsista_oficial = None
        for b in state.base_bolsistas:
            nome_oficial = b.get("Nome do(a) acadêmico(a)", "").strip().lower()
            projeto_oficial = b.get("Projeto vinculado / Coordenação", "").strip().lower()
            
            # Verifica se o nome bate E se o título do projeto está dentro da string da coluna do Edital
            if nome_oficial == nome_declarado.lower() and titulo_projeto_declarado in projeto_oficial:
                bolsista_oficial = b
                break

        # ── CENÁRIO A: Bolsista NÃO consta no Edital para este projeto (Erro E2) ──
        if not bolsista_oficial:
            motivo = f"E2: Bolsista '{nome_declarado}' declarado não consta no Edital Oficial para o projeto submetido."
            evidencia = f"Declarado no relatório: {nome_declarado} (Projeto: {state.titulo_projeto}) | Oficial no Edital: Não localizado"
            
            novos_checks.append(CheckResult(passou=False, motivo=motivo, evidencia=evidencia))
            novas_divergencias.append(motivo)
            novos_logs.append(f"[check_bolsistas] FALHOU — {motivo}")
            continue

        # ── CENÁRIO B: Bolsista CONSTA no Edital (Verificar Vigência - Erro E3) ──
        # O Edital salva as datas como "01/01/2024 a 31/12/2024"
        vigencia_oficial = bolsista_oficial.get("Vigência da Bolsa", "")
        datas_oficiais = vigencia_oficial.split(" a ")
        
        inicio_oficial = datas_oficiais[0].strip() if len(datas_oficiais) == 2 else vigencia_oficial
        fim_oficial = datas_oficiais[1].strip() if len(datas_oficiais) == 2 else ""

        declarado_inicio = bolsista_declarado.periodo_declarado_inicio.strip()
        declarado_fim = bolsista_declarado.periodo_declarado_fim.strip()

        if inicio_oficial != declarado_inicio or fim_oficial != declarado_fim:
            motivo = f"E3: O período de vigência declarado para '{nome_declarado}' difere do vínculo formal no Edital."
            evidencia = f"Período Declarado: {declarado_inicio} a {declarado_fim} | Vigência Oficial: {vigencia_oficial}"
            
            novos_checks.append(CheckResult(passou=False, motivo=motivo, evidencia=evidencia))
            novas_divergencias.append(motivo)
            novos_logs.append(f"[check_bolsistas] FALHOU — {motivo}")
        else:
            motivo = f"Bolsista '{nome_declarado}' validado com sucesso (Nome, Projeto e Vigência corretos)."
            evidencia = f"Período Declarado: {declarado_inicio} a {declarado_fim} | Vigência Oficial: {vigencia_oficial}"
            
            novos_checks.append(CheckResult(passou=True, motivo=motivo, evidencia=evidencia))
            novos_logs.append(f"[check_bolsistas] OK — {motivo}")

    # Retorna APENAS os dados novos para o LangGraph fazer o merge
    return {
        "check_bolsistas": novos_checks,
        "divergencias": novas_divergencias,
        "log": novos_logs
    }