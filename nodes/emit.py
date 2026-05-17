"""
nodes/emit.py — Nó de Saída e Entrega (Nó 8) do agente PROECE 3.4

Responsabilidade:
  - Cria um diretório físico de saídas (ex: output/protocolo_projeto/).
  - Salva o parecer opinativo em formato Markdown (.md).
  - Salva o parecer estruturado analítico em formato JSON (.json).
  - Salva a minuta de e-mail de notificação regulamentar em formato texto (.txt).
"""

import json
import logging
from pathlib import Path
from typing import Optional  # <-- CORREÇÃO: Importação do Optional adicionada
from state import AgenteState

logger = logging.getLogger(__name__)

# CORREÇÃO: Definição do ROOT_DIR para localizar a raiz do projeto de forma dinâmica
ROOT_DIR = Path(__file__).parent.parent

def emit_artifacts(state: AgenteState, output_base_dir: Optional[Path] = None) -> AgenteState:
    """
    Nó 8 — emit_artifacts
    Lê os textos e dados gerados e realiza a gravação física no disco rígido.
    """
    if not state.ingest_ok:
        state.log.append("[emit] Ignorado devido a erro crítico de ingestão anterior.")
        return state

    state.log.append("[emit] A iniciar a gravação física dos artefactos da auditoria...")

    try:
        # Define e cria a pasta de saída para o projeto atual
        # Evita lançar erro se o output_base_dir não for fornecido externamente
        base_dir = Path(output_base_dir) if output_base_dir else ROOT_DIR / "output"
        folder_nome = state.protocolo_projeto.replace(".", "_").replace("/", "_")
        project_output_dir = base_dir / folder_nome
        project_output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Salva o Parecer Técnico em Markdown (.md)
        parecer_path = project_output_dir / f"parecer_auditoria_{state.id_relatorio}.md"
        with open(parecer_path, "w", encoding="utf-8") as f:
            f.write(state.parecer_md)
        state.log.append(f"[emit] Parecer Markdown salvo em: {parecer_path.name}")

        # 2. Prepara e salva o Parecer Estruturado em JSON (.json)
        state.parecer_json = {
            "metadata": {
                "execution_id": state.execution_id,
                "id_relatorio": state.id_relatorio,
                "protocolo_projeto": state.protocolo_projeto,
                "titulo_projeto": state.titulo_projeto,
                "coordenador": state.coordenador,
                "decisao_final": state.decisao
            },
            "auditoria_completude": {
                "passou": state.check_completude.passou if state.check_completude else True,
                "motivo": state.check_completude.motivo if state.check_completude else "",
                "evidencia": state.check_completude.evidencia if state.check_completude else ""
            },
            "auditoria_financeira": {
                "passou": state.check_financeiro.passou if state.check_financeiro else True,
                "motivo": state.check_financeiro.motivo if state.check_financeiro else "",
                "evidencia": state.check_financeiro.evidencia if state.check_financeiro else ""
            },
            "auditoria_horas": {
                "passou": state.check_horas.passou if state.check_horas else True,
                "motivo": state.check_horas.motivo if state.check_horas else "",
                "evidencia": state.check_horas.evidencia if state.check_horas else ""
            },
            "lista_divergencias_acumuladas": state.divergencias
        }

        json_path = project_output_dir / f"dados_auditoria_{state.id_relatorio}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(state.parecer_json, f, ensure_ascii=False, indent=4)
        state.log.append(f"[emit] Relatório estruturado JSON salvo em: {json_path.name}")

        # 3. Salva a minuta de e-mail (.txt)
        email_path = project_output_dir / f"minuta_email_{state.id_relatorio}.txt"
        with open(email_path, "w", encoding="utf-8") as f:
            f.write(state.email_txt)
        state.log.append(f"[emit] Minuta do e-mail regulamentar salva em: {email_path.name}")

        state.log.append(f"[emit] OK — Todos os artefactos foram persistidos com sucesso na pasta de saídas.")

    except Exception as e:
        state.log.append(f"[emit] ERRO crítico ao gravar artefactos em disco: {str(e)}")
        print(f"❌ Erro no nó emit_artifacts: {str(e)}")

    return state