"""
Utilitarios compartilhados de conversao e sanitizacao de dados do ONS.
"""

from __future__ import annotations

import pandas as pd


def para_numero(s: pd.Series) -> pd.Series:
    """
    As colunas de valor chegam como texto, com campo VAZIO no lugar de
    zero/ausente e possivel virgula decimal. Converter antes de
    qualquer aritmetica.
    """
    t = s.astype("string").str.strip()
    t = t.mask(t.isin(["", "-", "nan", "None"]))
    if t.str.contains(r"\d\.\d{3},", na=False).any():
        t = t.str.replace(".", "", regex=False)
    t = t.str.replace(",", ".", regex=False)
    return pd.to_numeric(t, errors="coerce")
