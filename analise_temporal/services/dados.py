from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSOLIDADO_DIR = PROJECT_ROOT / "saida" / "consolidado"
CONSOLIDATED_MOV = CONSOLIDADO_DIR / "movimentacoes.parquet"
CONSOLIDATED_RET = CONSOLIDADO_DIR / "retornos.parquet"


def _load_consolidated():
    missing = [path for path in (CONSOLIDATED_RET, CONSOLIDATED_MOV) if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            "Base consolidada nao encontrada neste repositorio. "
            "Sincronize os arquivos em saida/consolidado a partir do projeto principal. "
            f"Arquivos ausentes: {missing_text}"
        )
    return (
        pd.read_parquet(CONSOLIDATED_RET),
        pd.read_parquet(CONSOLIDATED_MOV),
    )


def reload_consolidated_base():
    return _load_consolidated()


df, df_mov = _load_consolidated()


def reload_analysis_base():
    return reload_consolidated_base()

