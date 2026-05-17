"""
nodes/compose_parecer.py — Nó Final (Nó 7) do agente PROECE 3.4

Responsabilidade:
  - Analisa todas as divergências acumuladas na lista state.divergencias.
  - Define a decisão final: APROVAR, DEVOLVER PARA AJUSTES ou DEVOLVER PARA REELABORAÇÃO.
  - Gera o Parecer Técnico estruturado em Markdown (state.parecer_md) com referências às evidências.
  - Redige o e-mail de notificação regulamentar para o coordenador proponente (state.email_txt).
"""

import logging
import inspect
from state import AgenteState

logger = logging.getLogger(__name__)

class SmartEmailString(str):
    """
    Classe inteligente de string que devolve formatação HTML/Markdown 
    quando está a ser renderizada numa UI (Streamlit), mas devolve 
    códigos de cor ANSI quando impressa no terminal e formatação com quebras
    de linha corretas (\\n) ao ser gravada em arquivos txt no disco.
    """
    def __new__(cls, ui_version, terminal_version, file_version):
        # A CORREÇÃO: O Python C-level (f.write e st.markdown) extrai o valor base da string diretamente.
        # Ao inicializarmos a string base com o 'file_version', garantimos que o .txt terá as quebras corretas.
        obj = str.__new__(cls, file_version)
        obj._ui_version = ui_version
        obj._terminal_version = terminal_version
        obj._file_version = file_version
        return obj

    def __str__(self):
        # Inspeciona as chamadas anteriores para saber quem pediu a string
        for frame in inspect.stack()[:6]:
            if frame.function in ['write', 'writelines', 'dump', 'emit_artifacts', 'gerar_arquivos']:
                return self._file_version
        return self._terminal_version

    def __repr__(self):
        return self._terminal_version


def compose_parecer(state: AgenteState) -> AgenteState:
    """
    Agrega as inconsistências encontradas, define o veredito do relatório
    e gera a documentação analítica de saída do agente.
    """
    if not state.ingest_ok:
        state.log.append("[compose_parecer] Ignorado pois ingest_ok=False devido a erro crítico anterior.")
        state.decisao = "DEVOLVER PARA REELABORAÇÃO"
        state.parecer_md = "# Parecer Técnico de Auditoria\n\nErro crítico intransponível no processamento ou extração inicial do documento."
        state.email_txt = "Prezado coordenador,\nseu relatório não pôde ser processado devido a erros na estrutura do arquivo."
        return state

    state.log.append("[compose_parecer] A iniciar a consolidação das divergências e geração do parecer...")

    # ════════════════════════════════════════════════════════════════════════
    # 1. DEFINIÇÃO DA DECISÃO (Regra de Negócio / Priorização de Gravidade)
    # ════════════════════════════════════════════════════════════════════════
    tem_reelaboracao = any("E4" in div for div in state.divergencias)
    tem_ajustes = len(state.divergencias) > 0 and not tem_reelaboracao

    if tem_reelaboracao:
        state.decisao = "DEVOLVER PARA REELABORAÇÃO"
    elif tem_ajustes:
        state.decisao = "DEVOLVER PARA AJUSTES"
    else:
        state.decisao = "APROVAR"

    # ════════════════════════════════════════════════════════════════════════
    # 2. CONSTRUÇÃO DO PARECER TÉCNICO (state.parecer_md)
    # ════════════════════════════════════════════════════════════════════════
    parecer = [
        "# UNIVERSIDADE FEDERAL DE MATO GROSSO DO SUL",
        "## PRÓ-REITORIA DE EXTENSÃO, CULTURA E ESPORTE (PROECE)",
        "### RELATÓRIO TÉCNICO DE AUDITORIA DE AÇÕES DE EXTENSÃO",
        "",
        f"**Número do Relatório:** {state.id_relatorio}",
        f"**Protocolo da Submissão:** {state.protocolo_projeto}",
        f"**Título da Ação:** {state.titulo_projeto}",
        f"**Coordenador(a) Proponente:** {state.coordenador}",
        f"**Tipo de Relatório:** {state.tipo_relatorio}",
        f"**Data de Envio para Auditoria:** {state.data_envio}",
        "",
        "---",
        "",
        f"## CONCLUSÃO DO PARECER: **{state.decisao}**",
        ""
    ]

    if state.decisao == "APROVAR":
        parecer.extend([
            "Após minuciosa análise automatizada do relatório de extensão e cruzamento integral com as bases internas da PROECE (fomentos e editais oficiais), constatou-se a total conformidade regulamentar e consistência dos dados declarados.",
            "",
            "### Pontos de Conformidade Verificados:",
            "1. **Consistência Financeira:** O valor total declarado coincide com a base oficial de concessões da PROECE.",
            "2. **Regularidade de Bolsistas:** Todos os discentes declarados constam no Edital Oficial de Seleção e possuem períodos vigentes perfeitamente alinhados.",
            "3. **Carga Horária Analítica:** O somatório analítico das horas das atividades desenvolvidas confere exatamente com o resumo consolidado.",
            "4. **Completude Estrutural:** Todas as seções de texto obrigatórias estão devidamente preenchidas.",
            "",
            "Diante do exposto, este parecer técnico recomenda a **APROVAÇÃO** e homologação definitiva do referido relatório."
        ])
    else:
        parecer.extend([
            "Durante os procedimentos de cruzamento de dados e auditoria de conformidade regulamentar, foram identificadas inconformidades ou desvios em relação às bases de dados oficiais da PROECE.",
            "",
            "### Inconformidades Identificadas no Estado:"
        ])
        
        for idx, div in enumerate(state.divergencias, start=1):
            parecer.append(f"{idx}. ⚠️ **{div}**")
            
        parecer.extend([
            "",
            "### Matriz Analítica de Evidências Extraídas:",
            "| Componente de Validação | Status da Inspeção | Detalhamento Técnico da Evidência |",
            "| :--- | :---: | :--- |"
        ])
        
        fin_status = "❌ FALHA" if state.check_financeiro and not state.check_financeiro.passou else "✅ OK"
        fin_evid = state.check_financeiro.evidencia if state.check_financeiro else "Sem apontamentos divergentes."
        parecer.append(f"| Consistência Financeira (Nó 4) | {fin_status} | {fin_evid} |")

        comp_status = "❌ FALHA" if state.check_completude and not state.check_completude.passou else "✅ OK"
        comp_evid = state.check_completude.evidencia if state.check_completude else "Todas as seções obrigatórias identificadas."
        parecer.append(f"| Completude Estrutural (Nó 6) | {comp_status} | {comp_evid} |")

        hr_status = "❌ FALHA" if state.check_horas and not state.check_horas.passou else "✅ OK"
        hr_evid = state.check_horas.evidencia if state.check_horas else "Cálculos matemáticos batem perfeitamente."
        parecer.append(f"| Carga Horária Geral (Nó 6) | {hr_status} | {hr_evid} |")

        if state.check_bolsistas:
            for b_check in state.check_bolsistas:
                b_status = "❌ FALHA" if not b_check.passou else "✅ OK"
                parecer.append(f"| Vínculo de Bolsistas (Nó 5) | {b_status} | {b_check.motivo} — {b_check.evidencia} |")

        parecer.extend([
            "",
            f"Diante das irregularidades acima expostas, o documento foi classificado com a decisão de **{state.decisao}**. O proponente deverá seguir as diretrizes regulamentares anexas para sanar as pendências ou proceder com a reestruturação."
        ])

    state.parecer_md = "\n".join(parecer)

    # ════════════════════════════════════════════════════════════════════════
    # 3. REDAÇÃO DA MINUTA DE E-MAIL (state.email_txt)
    # ════════════════════════════════════════════════════════════════════════
    
    # Configurações de cores para o terminal
    ANSI_GREEN = "\033[92m"
    ANSI_YELLOW = "\033[93m"
    ANSI_RED = "\033[91m"
    ANSI_BOLD = "\033[1m"
    ANSI_RESET = "\033[0m"

    if state.decisao == "APROVAR":
        decisao_term = f"{ANSI_GREEN}{state.decisao}{ANSI_RESET}"
        decisao_ui   = f"<span style='color: green; font-weight: bold;'>{state.decisao}</span>"
        decisao_file = f"<span style='color: green; font-weight: bold;'>{state.decisao}</span>"
    elif state.decisao == "DEVOLVER PARA AJUSTES":
        decisao_term = f"{ANSI_YELLOW}{state.decisao}{ANSI_RESET}"
        decisao_ui   = f"<span style='color: #DF9A00; font-weight: bold;'>{state.decisao}</span>"
        decisao_file = f"<span style='color: #DF9A00; font-weight: bold;'>{state.decisao}</span>"
    else:
        decisao_term = f"{ANSI_RED}{state.decisao}{ANSI_RESET}"
        decisao_ui   = f"<span style='color: red; font-weight: bold;'>{state.decisao}</span>"
        decisao_file = f"<span style='color: red; font-weight: bold;'>{state.decisao}</span>"

    titulo_term = f"{ANSI_BOLD}{state.titulo_projeto}{ANSI_RESET}"
    titulo_ui   = f"<b>{state.titulo_projeto}</b>"
    titulo_file = f"<b>{state.titulo_projeto}</b>"

    def build_email(titulo_fmt, decisao_fmt, quebra_linha="\n"):
        email = [
            f"Assunto: PROECE/UFMS - Resultado da Auditoria - Relatório {state.tipo_relatorio} - Protocolo {state.protocolo_projeto}",
            "",
            f"Prezado(a) Coordenador(a) {state.coordenador},",
            "",
            f"Informamos que o Relatório {state.tipo_relatorio} de Ação de Extensão associado à submissão de protocolo {state.protocolo_projeto} ({titulo_fmt}) passou pelo rito de auditoria digital e cruzamento automatizado de dados da PROECE.",
            "",
            f"A decisão final emitida pela comissão de fiscalização automatizada foi: {decisao_fmt}.",
            ""
        ]

        if state.decisao == "APROVAR":
            email.extend([
                "Parabéns! O seu relatório foi considerado totalmente consistente e em estrita conformidade com as exigências regulamentares vigentes na UFMS. A prestação de contas financeira e as atribuições de carga horária dos discentes foram deferidas com sucesso e o processo seguirá para arquivamento definitivo.",
                "",
                "Agradecemos imensamente o seu empenho e contribuição contínua com as ações de extensão da nossa universidade."
            ])
        elif state.decisao == "DEVOLVER PARA AJUSTES":
            email.extend([
                "Identificamos divergências pontuais ou omissões menores de preenchimento que impedem a homologação imediata do documento. Solicitamos que aceda ao sistema corporativo e realize as devidas correções considerando as seguintes inconformidades apontadas pelo fiscal:",
                ""
            ])
            for div in state.divergencias:
                email.append(f"  ⚠️ {div}")
            email.extend([
                "",
                "O prazo para submissão dos ajustes e reenvio do relatório é de até 10 dias úteis a contar do recebimento desta notificação. O não cumprimento das correções poderá acarretar restrições para novos fomentos institucionais."
            ])
        else:  # DEVOLVER PARA REELABORAÇÃO
            email.extend([
                "Constatamos inconformidades estruturais graves no documento enviado, tais como a ausência completa de seções textuais obrigatórias descritas nas resoluções normativas e no edital regulador. Devido à gravidade técnica, o relatório foi rejeitado em sua totalidade.",
                "",
                "Será necessário realizar a REELABORAÇÃO completa do documento e proceder com um novo envio após sanar as seguintes omissões detectadas:",
                ""
            ])
            for div in state.divergencias:
                email.append(f"  ❌ {div}")
            email.extend([
                "",
                "Por favor, certifique-se de preencher todos os campos de rito obrigatório antes de submeter uma nova submissão. Em caso de dúvidas, a equipe técnica da Coordenadoria de Extensão estará à disposição."
            ])

        email.extend([
            "",
            "Atenciosamente,",
            "",
            "GABINETE DA PRÓ-REITORIA DE EXTENSÃO, CULTURA E ESPORTE",
            "Fundação Universidade Federal de Mato Grosso do Sul (UFMS)"
        ])
        
        return quebra_linha.join(email)

    # Utilizamos "  \n" (dois espaços e \n) no arquivo TXT. Isso é a sintaxe oficial do Markdown
    # para quebrar linha. Assim, o Bloco de Notas reconhece a quebra normal, e o st.markdown() 
    # também respeita as quebras sem colar tudo na mesma linha!
    state.email_txt = SmartEmailString(
        ui_version=build_email(titulo_ui, decisao_ui, quebra_linha="  \n"),
        terminal_version=build_email(titulo_term, decisao_term, quebra_linha="\n"),
        file_version=build_email(titulo_file, decisao_file, quebra_linha="  \n")
    )
    
    state.log.append(f"[compose_parecer] OK — Processo de parecer concluído com veredito final firmado.")

    return state