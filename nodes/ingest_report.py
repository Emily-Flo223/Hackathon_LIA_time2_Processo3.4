"""
nodes/ingest_report.py — Nó 1 do agente PROECE 3.4

Responsabilidade:
  - Carrega o ficheiro do relatório (PDF ou DOCX)
  - Extrai o texto bruto e popula o estado (state.raw_text)
  - NÃO extrai campos estruturados nem verifica regras de negócio (tarefa do nó extract_structured com LLM)

Entradas  → state.arquivo_path
Saídas    → state.raw_text
            state.ingest_ok (bool)
            state.ingest_erro (str, vazio se OK)
"""

from __future__ import annotations

import logging
from pathlib import Path

from state import AgenteState

logger = logging.getLogger(__name__)

# ── Funções auxiliares de leitura ──────────────────────────────────────────────

def _load_pdf(path: Path) -> str:
    """Extrai texto de PDF usando pdfplumber (melhor para PDFs com tabelas e layout)."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except ImportError:
        # Fallback de segurança para pypdf
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)


def _load_docx(path: Path) -> str:
    """Extrai texto de DOCX."""
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


# ── Função principal do nó ─────────────────────────────────────────────────────

def ingest_report(state: AgenteState) -> AgenteState:
    """
    Nó 1 — ingest_report

    Apenas carrega o ficheiro (PDF ou DOCX), converte para texto bruto
    e guarda em state.raw_text. A extração estruturada será feita pelo nó seguinte.
    """
    path = Path(state.arquivo_path)

    # ── 1. Verifica a existência do ficheiro ──
    if not path.exists():
        state.ingest_ok = False
        state.ingest_erro = f"Ficheiro não encontrado: {path}"
        state.log.append(f"[ingest_report] ERRO: {state.ingest_erro}")
        return state

    ext = path.suffix.lower()
    state.log.append(f"[ingest_report] A carregar {path.name} ({ext})")

    try:
        # ── 2. Leitura para texto bruto ──
        if ext == ".pdf":
            state.raw_text = _load_pdf(path)
        elif ext in (".docx", ".doc"):
            state.raw_text = _load_docx(path)
        else:
            state.ingest_ok = False
            state.ingest_erro = f"Formato não suportado: {ext}"
            state.log.append(f"[ingest_report] ERRO: {state.ingest_erro}")
            return state

        # Validação básica para garantir que o texto foi extraído
        if not state.raw_text or not state.raw_text.strip():
            state.ingest_ok = False
            state.ingest_erro = "Documento vazio ou o texto não pôde ser extraído"
            state.log.append(f"[ingest_report] ERRO: {state.ingest_erro}")
            return state

        # ── 3. Estado populado com sucesso ──
        state.ingest_ok = True
        state.ingest_erro = ""
        state.log.append(
            f"[ingest_report] OK — Texto extraído com sucesso ({len(state.raw_text)} caracteres). "
            f"Extração estruturada delegada ao nó extract_structured."
        )

    except Exception as exc:
        state.ingest_ok = False
        state.ingest_erro = f"Erro inesperado durante a ingestão: {exc}"
        state.log.append(f"[ingest_report] EXCEÇÃO: {state.ingest_erro}")

    return state