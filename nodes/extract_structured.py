"""
nodes/extract_structured.py — Nó 2 do agente PROECE 3.4

Responsabilidade:
  - Lê os prompts de sistema e utilizador a partir da pasta /prompts.
  - Recebe o texto bruto (state.raw_text) extraído no nó 1.
  - Utiliza o LLM via OpenRouter para o corpo do texto e Regex Implacável para o Cabeçalho.
"""

import sys
import re
from pathlib import Path

# --- INÍCIO DO AJUSTE DE IMPORTAÇÃO ---
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
# --- FIM DO AJUSTE ---

import logging
from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback

from llm import get_openrouter_llm

from state import (
    AgenteState,
    RecursoFinanceiro,
    Bolsista,
    Atividade,
    Secoes,
)

from utils.logger import get_structured_logger
json_logger = get_structured_logger(__name__)

logger = logging.getLogger(__name__)

PROMPTS_DIR = ROOT_DIR / "prompts"

def _load_prompt(filename: str) -> str:
    caminho = PROMPTS_DIR / filename
    if not caminho.exists():
        raise FileNotFoundError(f"Ficheiro de prompt não encontrado: {caminho}")
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read().strip()


# ══════════════════════════════════════════════════════════════════════════
# SCHEMAS PYDANTIC (Tolerantes a Falhas)
# ══════════════════════════════════════════════════════════════════════════

class CategoriaRecursoModel(BaseModel):
    nome: str = Field(default="Categoria não informada")
    valor: float = Field(default=0.0)

class RecursoModel(BaseModel):
    projeto_teve_recursos: bool = Field(default=False)
    valor_total_declarado: float = Field(default=0.0)
    categorias: List[CategoriaRecursoModel] = Field(default_factory=list)

class BolsistaModel(BaseModel):
    nome: str = Field(default="Não identificado")
    cpf: str = Field(default="Não identificado")
    tipo_vinculo: str = Field(default="Não identificado")
    periodo_declarado_inicio: str = Field(default="Não identificado")
    periodo_declarado_fim: str = Field(default="Não identificado")
    observacao: str = Field(default="")

class AtividadeModel(BaseModel):
    descricao: str = Field(default="Sem descrição")
    data_realizacao: str = Field(default="Não informada")
    local: str = Field(default="Não informado")
    carga_horaria_h: int = Field(default=0)

class SecoesModel(BaseModel):
    objetivo: str = Field(default="")
    prestacao_contas: str = Field(default="")
    sintese_execucao: str = Field(default="")
    resultados_alcancados: str = Field(default="")
    metodologia: str = Field(default="")
    dificuldades_encontradas: str = Field(default="")
    consideracoes_finais: str = Field(default="")

class ReportData(BaseModel):
    id_relatorio: str = Field(default="Não identificado")
    protocolo_projeto: str = Field(default="Não identificado")
    titulo_projeto: str = Field(default="Não identificado")
    data_inicio_projeto: str = Field(default="Não identificado")
    data_fim_projeto: str = Field(default="Não identificado")
    tipo_relatorio: str = Field(default="Não identificado")
    coordenador: str = Field(default="Não identificado")
    data_envio: str = Field(default="Não identificado")
    total_horas_declarado: int = Field(default=0)
    recursos: RecursoModel = Field(default_factory=RecursoModel)
    bolsistas: List[BolsistaModel] = Field(default_factory=list)
    atividades: List[AtividadeModel] = Field(default_factory=list)
    secoes: SecoesModel = Field(default_factory=SecoesModel)


# ══════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL DO NÓ
# ══════════════════════════════════════════════════════════════════════════

def extract_structured(state: AgenteState) -> AgenteState:
    if not state.ingest_ok:
        state.log.append("[extract_structured] Ignorado pois ingest_ok=False")
        return state

    state.log.append("[extract_structured] A iniciar extração com LLM via OpenRouter...")

    try:
        system_prompt = _load_prompt("extract_system_v1.0.txt")
        user_prompt_template = _load_prompt("extract_user_v1.0.txt")

        llm = get_openrouter_llm(model="openai/gpt-4o-mini", temperature=0.0)
        structured_llm = llm.with_structured_output(ReportData)

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt_template)
        ])
        chain = prompt | structured_llm

        with get_openai_callback() as cb:
            dados_extraidos: ReportData = chain.invoke({"texto_bruto": state.raw_text})
            
            # ── TEXTO NORMALIZADO PARA EVITAR QUEBRAS DE TABELA ──
            # Remove espaços, quebras de linha, tabs, vírgulas, pontos e traços
            texto_colado = re.sub(r"[\s,.:\-_/\r\n\t]", "", state.raw_text)

            # ── 1. CAÇADOR UNIVERSAL E IMPLACÁVEL DE PROTOCOLO ──
            # O .*? antes da sigla permite capturar a sigla mesmo se estiver grudada em "Protocolo" (ex: ProtocoloFAENG479201)
            padrao_strict = r".*?(INQUI|FACOM|CCHS|CCBS|FAALC|CPAQ|FAENG|CPAN|CPTL|CPNA|FADIR|FAMED|FAODO|INBIO|INMA|INFI|ESAN|FAMEZ|SIGPROJ)(\d{4,10})"
            match_strict = re.search(padrao_strict, texto_colado, re.IGNORECASE)
            
            if match_strict:
                sigla_limpa = match_strict.group(1).upper()
                numero_limpo = match_strict.group(2)
                dados_extraidos.protocolo_projeto = f"{sigla_limpa}.{numero_limpo}"
                state.log.append(f"[extract_structured] Protocolo extraído com sucesso: {dados_extraidos.protocolo_projeto}")
            else:
                dados_extraidos.protocolo_projeto = "Não identificado"
                state.log.append("[extract_structured] Aviso: Nenhum protocolo com sigla oficial foi detetado.")

            # ── 2. CAÇADOR DO ID DO RELATÓRIO (NÚMERO DO RELATÓRIO) ──
            # Procura a expressão "NumerodoRelatorio" colada aos números na string purificada
            match_id_strict = re.search(r"NumerodoRelatorio(\d+)", texto_colado, re.IGNORECASE)
            
            if match_id_strict:
                dados_extraidos.id_relatorio = match_id_strict.group(1).strip()
                state.log.append(f"[extract_structured] ID do Relatório extraído com sucesso: {dados_extraidos.id_relatorio}")
            else:
                # Se não encontrar o número interno, assume o nome limpo do arquivo físico
                dados_extraidos.id_relatorio = Path(state.arquivo_path).stem if state.arquivo_path else "Não identificado"

            # ── 3. CAÇADOR DO TIPO E TÍTULO ──
            texto_linhas = state.raw_text
            match_tipo = re.search(r"(?i)Tipo de Relatorio[^\w]*?([A-Za-zÀ-ÿ]+)", texto_linhas)
            if match_tipo:
                dados_extraidos.tipo_relatorio = match_tipo.group(1).strip()

            match_titulo = re.search(r"(?i)Titulo da Submissao[^\w]*?([^\n\r]+)", texto_linhas)
            if match_titulo:
                dados_extraidos.titulo_projeto = match_titulo.group(1).replace('\r', '').strip()
            
            nome_arquivo = Path(state.arquivo_path).name if state.arquivo_path else "desconhecido"
            json_logger.info(
                "Extração concluída", 
                extra={"arquivo": nome_arquivo, "tokens_usados": cb.total_tokens}
            )

        # ── Popula o AgenteState ──
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

        state.bolsistas = [Bolsista(nome=b.nome, cpf=b.cpf, tipo_vinculo=b.tipo_vinculo, periodo_declarado_inicio=b.periodo_declarado_inicio, periodo_declarado_fim=b.periodo_declarado_fim, observacao=b.observacao) for b in dados_extraidos.bolsistas]
        state.atividades = [Atividade(descricao=a.descricao, data_realizacao=a.data_realizacao, local=a.local, participantes_externos=0, carga_horaria_h=a.carga_horaria_h) for a in dados_extraidos.atividades]
        
        state.secoes = Secoes(
            objetivo=dados_extraidos.secoes.objetivo,
            prestacao_contas=dados_extraidos.secoes.prestacao_contas,
            sintese_execucao=dados_extraidos.secoes.sintese_execucao,
            resultados_alcancados=dados_extraidos.secoes.resultados_alcancados,
            metodologia=dados_extraidos.secoes.metodologia,
            dificuldades_encontradas=dados_extraidos.secoes.dificuldades_encontradas,
            consideracoes_finais=dados_extraidos.secoes.consideracoes_finais,
            referencias_bibliograficas=[], objetivos_desenvolvimento_sustentavel=[]
        )

        state.log.append(f"[extract_structured] OK — Dados extraídos com sucesso. Projeto: {state.titulo_projeto}")

    except Exception as e:
        state.ingest_ok = False
        state.ingest_erro = f"Falha na extração LLM estruturada: {str(e)}"
        state.log.append(f"[extract_structured] ERRO: {state.ingest_erro}")

    return state