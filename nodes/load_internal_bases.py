"""
nodes/load_internal_bases.py — Nó 3 do agente PROECE 3.4
"""
import csv
from pathlib import Path
from typing import Optional
from state import AgenteState

_COLUNAS_FOMENTOS = {"protocolo_projeto", "valor_aprovado", "fonte", "modalidade_fomento"}
_COLUNAS_EDITAL = {"Nome do(a) acadêmico(a)", "RGA", "Projeto vinculado / Coordenação", "Vigência da Bolsa"}

def _ler_csv(path: Path, colunas_obrigatorias: set) -> list:
    if not path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {path}")
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        ausentes = colunas_obrigatorias - set(reader.fieldnames)
        if ausentes:
            raise ValueError(f"CSV {path.name} está faltando colunas: {ausentes}")
        return [dict(row) for row in reader]

def load_internal_bases(state: AgenteState, data_dir: Optional[Path] = None) -> AgenteState:
    data_dir = Path(data_dir) if data_dir else Path(state.arquivo_path).parent
    
    # ── Carrega Fomentos ──
    fomentos = _ler_csv(data_dir / "fomentos_concedidos.csv", _COLUNAS_FOMENTOS)
    for row in fomentos:
        try: row["valor_aprovado"] = float(row["valor_aprovado"])
        except: row["valor_aprovado"] = 0.0
    state.base_fomentos = fomentos
    
    # ── Carrega Edital de Bolsistas (NOVO) ──
    bolsistas = _ler_csv(data_dir / "edital_bolsistas.csv", _COLUNAS_EDITAL)
    state.base_bolsistas = bolsistas
    
    state.log.append(f"[load_internal_bases] OK — Bases carregadas com sucesso.")
    return state