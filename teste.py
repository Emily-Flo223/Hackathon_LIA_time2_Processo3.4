"""
testar_pipeline.py — Script para testar os nós 1, 2, 3 e 4 manualmente

Uso:
  python3 testar_pipeline.py
"""

import sys
from pathlib import Path

# Garante que as importações funcionam a partir da raiz
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from state import AgenteState
from nodes.ingest_report import ingest_report
from nodes.extract_structured import extract_structured
from nodes.load_internal_bases import load_internal_bases
from nodes.check_financial import check_financial_consistency 

from nodes.check_bolsistas import check_bolsistas_consistency
from nodes.check_completeness import check_completeness_and_hours
from nodes.compose_parecer import compose_parecer
from nodes.emit import emit_artifacts

# Caminho para a pasta de dados gerados (onde estão os PDFs, DOCXs e os CSVs)
DATA_DIR = ROOT_DIR / "data"

def apply_update(state, update_data):
    """
    Função auxiliar: Se o nó retornar um dicionário (padrão LangGraph), 
    ele injeta os dados de volta no objeto AgenteState.
    Se o nó retornar o próprio AgenteState, ele apenas o devolve.
    """
    if isinstance(update_data, dict):
        for key, value in update_data.items():
            # Listas como logs e divergencias devem ser concatenadas
            if key in ["divergencias", "log"]:
                getattr(state, key).extend(value)
            else:
                setattr(state, key, value)
        return state
    return update_data

def testar_pipeline(quantidade_ficheiros=1):
    """
    Lê relatórios e passa-os pelos nós de ingestão, extração e carregamento de bases.
    """
    # Procura PDFs e DOCXs na diretoria data/
    ficheiros = list(DATA_DIR.glob("*.pdf")) + list(DATA_DIR.glob("*.docx"))
    
    if not ficheiros:
        print("❌ Nenhum relatório encontrado na pasta 'data/'.")
        return

    ficheiros_selecionados = ficheiros[:quantidade_ficheiros]

    for ficheiro in ficheiros_selecionados:
        print(f"\n{'='*70}")
        print(f"📄 A TESTAR FLUXO PARA O FICHEIRO: {ficheiro.name}")
        print(f"{'='*70}")

        # ── 0. INICIALIZAR O ESTADO ──
        state = AgenteState()
        state.arquivo_path = str(ficheiro)

        # ── 1. NÓ DE INGESTÃO (Ler o ficheiro físico) ──
        print("\n▶ [NÓ 1] A executar ingest_report...")
        state = apply_update(state, ingest_report(state))
        
        if not state.ingest_ok:
            print(f"❌ Falha na ingestão: {state.ingest_erro}")
            continue
            
        print(f"✔ Sucesso! Texto bruto extraído: {len(state.raw_text)} caracteres.")

        # ── 2. NÓ DE EXTRAÇÃO (LLM via OpenRouter) ──
        print("\n▶ [NÓ 2] A executar extract_structured (aguarde o LLM)...")
        state = apply_update(state, extract_structured(state))
        
        if not state.ingest_ok:
            print(f"❌ Falha na extração LLM: {state.ingest_erro}")
            continue
            
        print("✔ Sucesso! Dados do relatório estruturados via Pydantic.")

        # ── 3. NÓ DE BASES INTERNAS (Carregar CSVs da PROECE) ──
        print("\n▶ [NÓ 3] A executar load_internal_bases...")
        # Passamos o DATA_DIR explicitamente para ele encontrar os CSVs na mesma pasta
        state = apply_update(state, load_internal_bases(state, data_dir=DATA_DIR))
        print("✔ Sucesso! Bases oficiais carregadas na memória.")

        # ── 4. NÓ DE AUDITORIA FINANCEIRA (Novo!) ──
        print("\n▶ [NÓ 4] A executar check_financial_consistency...")
        state = apply_update(state, check_financial_consistency(state))
        print("✔ Sucesso! Auditoria financeira concluída.")

        # ── 5. VISUALIZAR O ESTADO ACUMULADO ──
        print("\n✅ RESUMO DO ESTADO (STATE) APÓS OS NÓS:")
        print(f"  📌 Relatório Extraído (LLM):")
        print(f"     - Protocolo: {state.protocolo_projeto}")
        print(f"     - Título: {state.titulo_projeto}")
        print(f"     - Período: {state.data_inicio_projeto} a {state.data_fim_projeto}")
        print(f"     - Bolsistas declarados: {len(state.bolsistas)}")
        print(f"     - Valor declarado: R$ {state.recursos.valor_total_declarado:,.2f}")
        
        print(f"\n  🏛️ Bases da PROECE Carregadas (CSVs):")
        print(f"     - Total de Fomentos no Sistema: {len(state.base_fomentos)} registos")
        print(f"     - Total de Bolsistas no Sistema: {len(state.base_bolsistas)} registos")
        
        # Vamos fazer um mini "fisco" manual só para ver se conseguimos cruzar os dados agora
        print("\n  🔍 Teste de Cruzamento de Dados (LLM vs CSV):")
        
        # Procura o fomento oficial do projeto atual
        fomento_oficial = next((f for f in state.base_fomentos if f["protocolo_projeto"] == state.protocolo_projeto), None)
        if fomento_oficial:
            print(f"     [!] Encontrado na base oficial! O valor concedido para {state.protocolo_projeto} foi de R$ {fomento_oficial['valor_aprovado']:,.2f}")
            if fomento_oficial['valor_aprovado'] != state.recursos.valor_total_declarado:
                print("         ⚠️ ATENÇÃO: O valor declarado pelo coordenador é DIFERENTE do oficial!")
            else:
                print("         ✅ Os valores batem certinho!")
        else:
            print(f"     [!] Projeto {state.protocolo_projeto} não encontrado na base de fomentos.")

        # <-- NOVO BLOCO ADICIONADO PARA VERIFICAR A AUDITORIA -->
        print("\n✅ RESULTADO DA AUDITORIA FINANCEIRA:")
        if state.check_financeiro:
            status = "🟢 STATUS: APROVADO" if state.check_financeiro.passou else "🔴 STATUS: REJEITADO (COM ERRO)"
            print(f"   {status}")
            print(f"   📋 Motivo:    {state.check_financeiro.motivo}")
            print(f"   🔎 Evidência: {state.check_financeiro.evidencia}")
        
        print("\n   🚨 Divergências Acumuladas no Estado:")
        if state.divergencias:
            for divergencia in state.divergencias:
                print(f"      - {divergencia}")
        else:
            print("      (Nenhuma divergência. O projeto está limpo até agora!)")
        # <----------------------------------------------------->

        # ── 5. NÓ DE AUDITORIA DE BOLSISTAS ──
        print("\n▶ [NÓ 5] A executar check_bolsistas_consistency...")
        state = apply_update(state, check_bolsistas_consistency(state))
        print("✔ Sucesso! Auditoria de bolsistas concluída.")

        # <-- NOVO BLOCO ADICIONADO PARA VERIFICAR OS BOLSISTAS -->
        print("\n✅ RESULTADO DA AUDITORIA DE BOLSISTAS:")
        if state.check_bolsistas:
            for i, check in enumerate(state.check_bolsistas, 1):
                status = "🟢 STATUS: APROVADO" if check.passou else "🔴 STATUS: REJEITADO (COM ERRO)"
                print(f"   Bolsista {i}:")
                print(f"   {status}")
                print(f"   📋 Motivo:    {check.motivo}")
                print(f"   🔎 Evidência: {check.evidencia}\n")
        else:
            print("   (O relatório não possuía bolsistas declarados)")

        # ── 6. NÓ DE COMPLETUDE E HORAS ──
        print("\n▶ [NÓ 6] A executar check_completeness_and_hours...")
        state = apply_update(state, check_completeness_and_hours(state))
        
        print("\n✅ RESULTADO DA AUDITORIA DE ESTRUTURA E HORAS:")
        
        # Exibe Completude (E4)
        if state.check_completude:
            status_comp = "🟢 STATUS: APROVADO" if state.check_completude.passou else "🔴 STATUS: REJEITADO (COM ERRO)"
            print(f"   [Completude de Seções]")
            print(f"   {status_comp}")
            print(f"   📋 Motivo:    {state.check_completude.motivo}")
            print(f"   🔎 Evidência: {state.check_completude.evidencia}\n")

        # Exibe Horas (E5)
        if state.check_horas:
            status_horas = "🟢 STATUS: APROVADO" if state.check_horas.passou else "🔴 STATUS: REJEITADO (COM ERRO)"
            print(f"   [Cálculo de Horas das Atividades]")
            print(f"   {status_horas}")
            print(f"   📋 Motivo:    {state.check_horas.motivo}")
            print(f"   🔎 Evidência: {state.check_horas.evidencia}\n")
            
        print("\n   🚨 Divergências Acumuladas no Estado Até Agora:")
        if state.divergencias:
            for divergencia in state.divergencias:
                print(f"      - {divergencia}")
        else:
            print("      (Nenhuma divergência. O projeto está limpo até agora!)")

        # ── 7. NÓ FINAL: COMPOR PARECER E E-MAIL ──
        print("\n▶ [NÓ 7] A executar compose_parecer...")
        state = apply_update(state, compose_parecer(state))
        print("✔ Sucesso! Ciclo completo de parecer e e-mail concluído.")

        print(f"\n{'-'*30} DOCUMENTAÇÃO GERADA PELO AGENTE {'-'*30}")
        print("\n📝 [PARECER TÉCNICO OFICIAL - MARKDOWN]:")
        print(state.parecer_md)
        
        print("\n📧 [MINUTA DE E-MAIL DE NOTIFICAÇÃO]:")
        print(state.email_txt)
        print(f"{'-'*80}")

        # ── 8. NÓ EMIT: GRAVAÇÃO DOS ARTEFACTOS ──
        print("\n▶ [NÓ 8] A executar emit_artifacts...")
        # Definimos explicitamente o DATA_DIR / "output" para organizar os ficheiros na pasta correta
        OUTPUT_DIR = ROOT_DIR / "output"
        state = apply_update(state, emit_artifacts(state, output_base_dir=OUTPUT_DIR))
        
        print(f"\n✅ PIPELINE CONCLUÍDA COM SUCESSO!")
        print(f"   Os ficheiros oficiais de auditoria para o projeto '{state.protocolo_projeto}'")
        print(f"   foram salvos na pasta: {OUTPUT_DIR.resolve()}/")
        print(f"{'='*80}\n")

        print("\n📝 HISTÓRICO DE LOGS DO AGENTE:")
        for log in state.log:
            print(f"   > {log}")
            
    print(f"\n{'='*70}\nFim do teste para {len(ficheiros_selecionados)} ficheiro(s).\n")

if __name__ == "__main__":
    # Testar com 4 ficheiros 
    testar_pipeline(quantidade_ficheiros=4)