"""
state.py — Estado compartilhado do agente PROECE 3.4
Usa dataclasses da stdlib (equivalente ao TypedDict do LangGraph).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Annotated  # <-- Adicionado Annotated
import operator                              # <-- Adicionado operator


# ── sub-estruturas extraídas do relatório ──────────────────────────────────────

@dataclass
class RecursoFinanceiro:
    projeto_teve_recursos: bool
    valor_total_declarado: float
    categorias: list[dict]  # lista bruta


@dataclass
class Bolsista:
    nome: str
    cpf: str
    tipo_vinculo: str
    periodo_declarado_inicio: str
    periodo_declarado_fim: str
    observacao: str = ""


@dataclass
class Atividade:
    descricao: str
    data_realizacao: str
    local: str
    participantes_externos: int
    carga_horaria_h: int

@dataclass
class Secoes:
    resultados_alcancados: str
    metodologia: str
    consideracoes_finais: str
    sintese_execucao: str
    prestacao_contas: str
    
    # Opcionais (com valor padrão) vão todos para o fim
    objetivo: str = ""
    dificuldades_encontradas: str = ""
    referencias_bibliograficas: list[str] = field(default_factory=list)
    objetivos_desenvolvimento_sustentavel: list[str] = field(default_factory=list)


# ── resultado de cada verificação ─────────────────────────────────────────────

@dataclass
class CheckResult:
    passou: bool
    motivo: str
    evidencia: str = ""


# ── estado principal do agente ─────────────────────────────────────────────────

@dataclass
class AgenteState:
    # --- Nó 0: entrada bruta ---
    arquivo_path: str = ""          # caminho do arquivo .json/.pdf/.docx
    raw_text: str = ""              # texto extraído (para PDF/DOCX)
    raw_json: Optional[dict] = None # JSON carregado (para .json)

    # --- Nó 1: ingest_report (dados normalizados) ---
    id_relatorio: str = ""
    protocolo_projeto: str = ""
    titulo_projeto: str = ""
    tipo_relatorio: str = ""        # "Parcial" | "Final"
    coordenador: str = ""
    data_envio: str = ""
    recursos: Optional[RecursoFinanceiro] = None
    bolsistas: list[Bolsista] = field(default_factory=list)
    atividades: list[Atividade] = field(default_factory=list)
    total_horas_declarado: int = 0
    secoes: Optional[Secoes] = None
    ingest_ok: bool = False
    ingest_erro: str = ""

    # --- Nó 2: extract_structured (confirmação do schema) ---
    extract_ok: bool = False

    # --- Bases internas (carregadas no Nó 3) ---
    base_fomentos: list[dict] = field(default_factory=list)
    base_bolsistas: list[dict] = field(default_factory=list)

    # --- Resultados das verificações paralelas (Nós 4-6) ---
    check_financeiro: Optional[CheckResult] = None
    check_bolsistas: Annotated[list[CheckResult], operator.add] = field(default_factory=list) # <-- Atualizado
    check_completude: Optional[CheckResult] = None
    check_horas: Optional[CheckResult] = None

    # --- Nó 7: compose_parecer ---
    decisao: str = ""               # APROVAR | DEVOLVER PARA AJUSTES | DEVOLVER PARA REELABORAÇÃO
    divergencias: Annotated[list[str], operator.add] = field(default_factory=list) # <-- Atualizado
    parecer_md: str = ""
    parecer_json: Optional[dict] = None
    email_txt: str = ""

    # --- Metadados de execução ---
    execution_id: str = ""
    log: Annotated[list[str], operator.add] = field(default_factory=list) # <-- Atualizado