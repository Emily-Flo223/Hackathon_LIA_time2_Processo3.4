"""
nodes/extract_structured.py — Nó 2 do agente PROECE 3.4

Responsabilidade:
  - Lê os prompts de sistema e utilizador a partir da pasta /prompts.
  - Recebe o texto bruto (state.raw_text) extraído no nó 1.
  - Utiliza o LLM via OpenRouter com Structured Output (Pydantic) para extrair os dados.
"""

import sys
from pathlib import Path

# --- INÍCIO DO AJUSTE DE IMPORTAÇÃO ---
# Isto garante que o Python encontre o llm.py e state.py na pasta raiz 
# quando corremos este ficheiro isoladamente para testes.
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
# --- FIM DO AJUSTE ---

import logging
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

# Importa a função que criámos no llm.py (na raiz do projeto)
from llm import get_openrouter_llm

from state import (
    AgenteState,
    RecursoFinanceiro,
    Bolsista,
    Atividade,
    Secoes,
)

logger = logging.getLogger(__name__)

# ── Caminho para a pasta de prompts ──
PROMPTS_DIR = ROOT_DIR / "prompts"

def _load_prompt(filename: str) -> str:
    """Função auxiliar para ler o conteúdo de um ficheiro de prompt."""
    caminho = PROMPTS_DIR / filename
    if not caminho.exists():
        raise FileNotFoundError(f"Ficheiro de prompt não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read().strip()


# ══════════════════════════════════════════════════════════════════════════
# SCHEMAS PYDANTIC (Instruções para o LLM)
# ══════════════════════════════════════════════════════════════════════════

class CategoriaRecursoModel(BaseModel):
    nome: str = Field(description="Nome da categoria do recurso (ex: capital, custeio, bolsa).")
    valor: float = Field(description="Valor financeiro em reais (R$) atribuído a esta categoria.")

class RecursoModel(BaseModel):
    projeto_teve_recursos: bool = Field(description="True se o projeto declarou ter recebido recursos, False caso contrário.")
    valor_total_declarado: float = Field(description="O valor total declarado em reais (R$). Se não houver, extraia 0.0.")
    categorias: List[CategoriaRecursoModel] = Field(description="Lista de valores detalhados por categoria. Vazio se não houver.", default_factory=list)

class BolsistaModel(BaseModel):
    nome: str = Field(description="Nome completo do bolsista ou voluntário")
    cpf: str = Field(description="CPF do bolsista")
    tipo_vinculo: str = Field(description="Tipo de vínculo (ex: PIBEXT, PIVEXT)")
    periodo_declarado_inicio: str = Field(description="Data de início do período declarado")
    periodo_declarado_fim: str = Field(description="Data de fim do período declarado")
    observacao: str = Field(description="Observação ou aviso sobre o bolsista. Vazio se não houver.")

class AtividadeModel(BaseModel):
    descricao: str = Field(description="Descrição da atividade realizada")
    data_realizacao: str = Field(description="Data ou período em que a atividade ocorreu")
    local: str = Field(description="Local onde a atividade ocorreu")
    carga_horaria_h: int = Field(description="Carga horária em horas gastas na atividade")

class SecoesModel(BaseModel):
    objetivo: str = Field(description="Texto da secção 'Objetivo do Projeto'. Vazio se ausente.")
    prestacao_contas: str = Field(description="Texto da secção 'Prestação de Contas'. Vazio se ausente.")
    sintese_execucao: str = Field(description="Texto da secção 'Síntese da Execução'. Vazio se ausente.")
    resultados_alcancados: str = Field(description="Texto da secção 'Resultados Alcançados'. Vazio se ausente.")
    metodologia: str = Field(description="Texto da secção 'Metodologia Utilizada'. Vazio se ausente.")
    dificuldades_encontradas: str = Field(description="Texto da secção 'Dificuldades Encontradas'. Vazio se ausente.")
    consideracoes_finais: str = Field(description="Texto da secção 'Considerações Finais'. Vazio se ausente.")

class ReportData(BaseModel):
    """Esquema principal de extração de dados do relatório de extensão."""
    id_relatorio: str = Field(description="Número de identificação único do relatório")
    protocolo_projeto: str = Field(description="Número do protocolo do projeto")
    titulo_projeto: str = Field(description="Título da submissão/projeto")
    data_inicio_projeto: str = Field(description="Data de início do projeto")
    data_fim_projeto: str = Field(description="Data de encerramento prevista ou final do projeto")
    tipo_relatorio: str = Field(description="Tipo do relatório (ex: Parcial, Final)")
    coordenador: str = Field(description="Nome do coordenador do projeto")
    data_envio: str = Field(description="Data de envio do relatório")
    total_horas_declarado: int = Field(description="Total de horas declaradas no cabeçalho ou resumo")
    
    recursos: RecursoModel
    bolsistas: List[BolsistaModel]
    atividades: List[AtividadeModel]
    secoes: SecoesModel


# ══════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL DO NÓ
# ══════════════════════════════════════════════════════════════════════════

def extract_structured(state: AgenteState) -> AgenteState:
    """
    Nó 2 — extract_structured
    
    Carrega os prompts dos ficheiros, utiliza o OpenRouter para ler state.raw_text
    e extrair os dados estruturados de acordo com o schema ReportData.
    """
    if not state.ingest_ok:
        state.log.append("[extract_structured] Ignorado pois ingest_ok=False")
        return state

    state.log.append("[extract_structured] A iniciar extração com LLM via OpenRouter...")

    try:
        # 1. Carrega os prompts dos ficheiros .txt
        system_prompt = _load_prompt("extract_system.txt")
        user_prompt_template = _load_prompt("extract_user.txt")

        # 2. Inicializa o modelo OpenRouter
        # Pode alterar "openai/gpt-4o-mini" para outro modelo compatível com tool calling (ex: anthropic/claude-3-haiku)
        llm = get_openrouter_llm(model="openai/gpt-4o-mini", temperature=0.0)
        
        # 3. Amarra o Schema Pydantic ao modelo
        structured_llm = llm.with_structured_output(ReportData)

        # 4. Prepara o prompt do LangChain
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt_template)
        ])

        chain = prompt | structured_llm

        # 5. Invoca o modelo passando o texto bruto extraído no nó anterior
        dados_extraidos: ReportData = chain.invoke({"texto_bruto": state.raw_text})

        # ── Popula o AgenteState com os dados extraídos ──
        state.id_relatorio = dados_extraidos.id_relatorio
        state.protocolo_projeto = dados_extraidos.protocolo_projeto
        state.titulo_projeto = dados_extraidos.titulo_projeto
        state.data_inicio_projeto = dados_extraidos.data_inicio_projeto
        state.data_fim_projeto = dados_extraidos.data_fim_projeto
        state.tipo_relatorio = dados_extraidos.tipo_relatorio
        state.coordenador = dados_extraidos.coordenador
        state.data_envio = dados_extraidos.data_envio
        state.total_horas_declarado = dados_extraidos.total_horas_declarado

        state.recursos = RecursoFinanceiro(
            projeto_teve_recursos=dados_extraidos.recursos.projeto_teve_recursos,
            valor_total_declarado=dados_extraidos.recursos.valor_total_declarado,
            categorias=[{"nome": c.nome, "valor": c.valor} for c in dados_extraidos.recursos.categorias]
        )

        state.bolsistas = [
            Bolsista(
                nome=b.nome, cpf=b.cpf, tipo_vinculo=b.tipo_vinculo,
                periodo_declarado_inicio=b.periodo_declarado_inicio,
                periodo_declarado_fim=b.periodo_declarado_fim,
                observacao=b.observacao
            ) for b in dados_extraidos.bolsistas
        ]

        state.atividades = [
            Atividade(
                descricao=a.descricao, data_realizacao=a.data_realizacao,
                local=a.local, participantes_externos=0, 
                carga_horaria_h=a.carga_horaria_h
            ) for a in dados_extraidos.atividades
        ]

        state.secoes = Secoes(
            objetivo=dados_extraidos.secoes.objetivo,
            prestacao_contas=dados_extraidos.secoes.prestacao_contas,
            sintese_execucao=dados_extraidos.secoes.sintese_execucao,
            resultados_alcancados=dados_extraidos.secoes.resultados_alcancados,
            metodologia=dados_extraidos.secoes.metodologia,
            dificuldades_encontradas=dados_extraidos.secoes.dificuldades_encontradas,
            consideracoes_finais=dados_extraidos.secoes.consideracoes_finais,
            referencias_bibliograficas=[],
            objetivos_desenvolvimento_sustentavel=[]
        )

        state.log.append(f"[extract_structured] OK — Dados extraídos com sucesso. Projeto: {state.titulo_projeto}")

    except Exception as e:
        state.ingest_ok = False
        state.ingest_erro = f"Falha na extração LLM estruturada: {str(e)}"
        state.log.append(f"[extract_structured] ERRO: {state.ingest_erro}")

    return state