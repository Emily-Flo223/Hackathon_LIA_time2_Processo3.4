"""
utils/logger.py — Sistema de Logging Estruturado em JSON
"""

import logging
import json
from datetime import datetime
from pathlib import Path

# Cria a pasta de logs na raiz do projeto
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
        }
        # Injeta variáveis adicionais se existirem
        if hasattr(record, "execution_id"):
            log_record["execution_id"] = record.execution_id
        if hasattr(record, "tokens"):
            log_record["tokens"] = record.tokens
        if hasattr(record, "arquivo"):
            log_record["arquivo"] = record.arquivo
            
        return json.dumps(log_record, ensure_ascii=False)

def get_structured_logger(name="proece_agent"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Evita duplicar os handlers se o logger for chamado várias vezes
    if not logger.handlers:
        fh = logging.FileHandler(LOG_DIR / "agente_execucoes.jsonl", encoding="utf-8")
        fh.setFormatter(JSONFormatter())
        logger.addHandler(fh)
        
    return logger