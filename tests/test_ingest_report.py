"""
tests/test_ingest_report.py — Testes do Nó 1 (ingest_report)

Execução:
    cd agente_proece/
    python3 tests/test_ingest_report.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "nodes"))

from state import AgenteState
from nodes.ingest_report import ingest_report

# Aponta para a pasta onde o gerador criou os ficheiros
DATA_DIR = ROOT / "data"

def make_state(arquivo: str) -> AgenteState:
    s = AgenteState()
    s.arquivo_path = arquivo
    return s

def test_arquivo_nao_encontrado():
    state = make_state("/caminho/inexistente/relatorio.pdf")
    result = ingest_report(state)
    assert result.ingest_ok is False
    assert "não encontrado" in result.ingest_erro.lower()
    print("\n✔ test_arquivo_nao_encontrado — PASSOU")

def test_formato_nao_suportado():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"conteudo de teste")
        tmp_path = f.name

    state = make_state(tmp_path)
    result = ingest_report(state)
    assert result.ingest_ok is False
    assert "formato" in result.ingest_erro.lower()
    print("\n✔ test_formato_nao_suportado — PASSOU")

def test_pdf_carrega_corretamente():
    matches = sorted(DATA_DIR.glob("*.pdf"))
    if not matches:
        print("\n⚠ test_pdf_carrega_corretamente — IGNORADO (nenhum PDF encontrado na diretoria 'data')")
        return
        
    arquivo = matches[0]
    state = make_state(str(arquivo))
    result = ingest_report(state)

    assert result.ingest_ok is True, f"ingest_ok=False — erro: {result.ingest_erro}"
    assert result.raw_text is not None and len(result.raw_text) > 0, "O texto bruto não foi extraído do PDF"
    assert "extract_structured" in result.log[-1]

    print(f"\n✔ test_pdf_carrega_corretamente — PASSOU (ficheiro: {arquivo.name})")

def test_docx_carrega_corretamente():
    matches = sorted(DATA_DIR.glob("*.docx"))
    if not matches:
        print("\n⚠ test_docx_carrega_corretamente — IGNORADO (nenhum DOCX encontrado na diretoria 'data')")
        return
        
    arquivo = matches[0]
    state = make_state(str(arquivo))
    result = ingest_report(state)

    assert result.ingest_ok is True, f"ingest_ok=False — erro: {result.ingest_erro}"
    assert result.raw_text is not None and len(result.raw_text) > 0, "O texto bruto não foi extraído do DOCX"

    print(f"\n✔ test_docx_carrega_corretamente — PASSOU (ficheiro: {arquivo.name})")

if __name__ == "__main__":
    tests = [
        test_arquivo_nao_encontrado,
        test_formato_nao_suportado,
        test_pdf_carrega_corretamente,
        test_docx_carrega_corretamente,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"\n✘ {t.__name__} — FALHOU: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✘ {t.__name__} — EXCEÇÃO: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Resultado: {passed} passou(aram), {failed} falhou(aram)")