"""
tests/test_load_internal_bases.py — Testes do Nó 2 (load_internal_bases)

Execução:
    cd agente_proece/
    python3 tests/test_load_internal_bases.py
"""

import sys
import csv
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "nodes"))

from state import AgenteState
from nodes.load_internal_bases import load_internal_bases

DATA_DIR = ROOT / "data"


def make_state() -> AgenteState:
    s = AgenteState()
    s.arquivo_path = str(DATA_DIR / "relatorios" / "relatorio_02_OK.json")
    return s


# ── Caso 1: carregamento normal ───────────────────────────────────────────────

def test_carrega_fomentos_e_bolsistas():
    """Deve carregar os dois CSVs sem erro."""
    state = make_state()
    result = load_internal_bases(state, data_dir=DATA_DIR)

    assert len(result.base_fomentos) > 0, "base_fomentos vazia"
    assert len(result.base_bolsistas) > 0, "base_bolsistas vazia"

    print(
        f"\n✔ test_carrega_fomentos_e_bolsistas — PASSOU "
        f"(fomentos={len(result.base_fomentos)}, bolsistas={len(result.base_bolsistas)})"
    )


# ── Caso 2: colunas obrigatórias nos fomentos ─────────────────────────────────

def test_fomentos_tem_colunas_obrigatorias():
    state = make_state()
    result = load_internal_bases(state, data_dir=DATA_DIR)

    for row in result.base_fomentos:
        assert "protocolo_projeto" in row
        assert "valor_aprovado" in row
        assert isinstance(row["valor_aprovado"], float), \
            f"valor_aprovado deve ser float, got {type(row['valor_aprovado'])}"

    print("\n✔ test_fomentos_tem_colunas_obrigatorias — PASSOU")


# ── Caso 3: colunas obrigatórias nos bolsistas ────────────────────────────────

def test_bolsistas_tem_colunas_obrigatorias():
    state = make_state()
    result = load_internal_bases(state, data_dir=DATA_DIR)

    for row in result.base_bolsistas:
        assert "cpf" in row
        assert "protocolo_projeto" in row
        assert "data_inicio_vinculo" in row
        assert "data_fim_vinculo" in row

    print("\n✔ test_bolsistas_tem_colunas_obrigatorias — PASSOU")


# ── Caso 4: valor_aprovado normalizado para float ────────────────────────────

def test_valor_aprovado_e_float():
    state = make_state()
    result = load_internal_bases(state, data_dir=DATA_DIR)

    valores = [row["valor_aprovado"] for row in result.base_fomentos]
    assert all(isinstance(v, float) for v in valores)
    assert all(v > 0 for v in valores)

    print("\n✔ test_valor_aprovado_e_float — PASSOU")


# ── Caso 5: protocolo do relatório E1 existe na base ─────────────────────────

def test_protocolo_e1_encontrado_na_base():
    """FAENG.126999 (relatório E1) deve estar na base de fomentos."""
    state = make_state()
    result = load_internal_bases(state, data_dir=DATA_DIR)

    protocolos = {row["protocolo_projeto"] for row in result.base_fomentos}
    assert "FAENG.814825" in protocolos, \
        f"FAENG.814825 não encontrado. Disponíveis: {sorted(protocolos)}"

    print("\n✔ test_protocolo_e1_encontrado_na_base — PASSOU")


# ── Caso 6: log registra quantidades ─────────────────────────────────────────

def test_log_registra_quantidades():
    state = make_state()
    result = load_internal_bases(state, data_dir=DATA_DIR)

    log_texto = "\n".join(result.log)
    assert "fomentos carregados" in log_texto
    assert "bolsistas carregados" in log_texto

    print("\n✔ test_log_registra_quantidades — PASSOU")


# ── Caso 7: CSV com coluna faltando levanta ValueError ───────────────────────

def test_csv_coluna_faltando_levanta_erro():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # fomentos sem valor_aprovado
        fomentos_path = tmp_path / "fomentos_concedidos.csv"
        with open(fomentos_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["protocolo_projeto", "fonte"])
            writer.writeheader()
            writer.writerow({"protocolo_projeto": "TEST.001", "fonte": "CNPq"})

        # bolsistas mínimo válido
        bolsistas_path = tmp_path / "bolsistas_selecionados.csv"
        with open(bolsistas_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "cpf", "nome", "tipo_vinculo", "protocolo_projeto",
                "data_inicio_vinculo", "data_fim_vinculo",
            ])
            writer.writeheader()

        state = AgenteState()
        try:
            load_internal_bases(state, data_dir=tmp_path)
            assert False, "Deveria ter levantado ValueError"
        except ValueError as e:
            assert "valor_aprovado" in str(e), f"Mensagem inesperada: {e}"

    print("\n✔ test_csv_coluna_faltando_levanta_erro — PASSOU")


# ── Caso 8: data_dir inexistente levanta FileNotFoundError ───────────────────

def test_data_dir_inexistente_levanta_erro():
    state = AgenteState()
    try:
        load_internal_bases(state, data_dir=Path("/caminho/inexistente"))
        assert False, "Deveria ter levantado FileNotFoundError"
    except FileNotFoundError as e:
        assert "fomentos_concedidos.csv" in str(e) or "não encontrado" in str(e)

    print("\n✔ test_data_dir_inexistente_levanta_erro — PASSOU")


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_carrega_fomentos_e_bolsistas,
        test_fomentos_tem_colunas_obrigatorias,
        test_bolsistas_tem_colunas_obrigatorias,
        test_valor_aprovado_e_float,
        test_protocolo_e1_encontrado_na_base,
        test_log_registra_quantidades,
        test_csv_coluna_faltando_levanta_erro,
        test_data_dir_inexistente_levanta_erro,
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