"""
Testes unitarios para para_numero (src/digital_twin/utils.py) e
baixar com S3 simulado (src/digital_twin/ons_client.py).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest

from src.digital_twin import ons_client
from src.digital_twin.utils import para_numero


class FakeS3Client:
    """Cliente S3 simulado para testar download atomico e cache."""

    def __init__(self, conteudo: bytes = b"parquet-simulado", falhar: bool = False):
        self.conteudo = conteudo
        self.falhar = falhar
        self.chamadas: List[Tuple[str, str, str]] = []

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self.chamadas.append((bucket, key, filename))
        if self.falhar:
            raise RuntimeError("falha simulada de rede no S3")
        Path(filename).write_bytes(self.conteudo)


def test_para_numero_virgula_decimal_e_milhar():
    s = pd.Series(["10,5", "1.234,56", "0,0", "  42  "])
    res = para_numero(s)
    esperado = [10.5, 1234.56, 0.0, 42.0]
    assert np.allclose(res.to_numpy(dtype=float), esperado)


def test_para_numero_ponto_decimal():
    s = pd.Series(["100.25", "0.5", "-3.14"])
    res = para_numero(s)
    esperado = [100.25, 0.5, -3.14]
    assert np.allclose(res.to_numpy(dtype=float), esperado)


def test_para_numero_valores_vazios_e_invalidos():
    s = pd.Series(["", "   ", "-", "nan", "None", None, pd.NA, "invalido"])
    res = para_numero(s)
    assert res.isna().all()


def test_baixar_faz_download_e_usa_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ons_client, "DATA_DIR", tmp_path)
    fake_s3 = FakeS3Client(conteudo=b"dados-ons-2025-01")
    monkeypatch.setattr(ons_client, "_client", lambda: fake_s3)

    key = "dataset/restricao_coff_eolica_tm/RESTRICAO_COFF_EOLICA_2025_01.parquet"

    # 1. Primeira chamada baixa do S3 e grava no destino preservando o prefixo
    caminho1 = ons_client.baixar(key)
    assert caminho1 == tmp_path / key
    assert caminho1.exists()
    assert caminho1.read_bytes() == b"dados-ons-2025-01"
    assert len(fake_s3.chamadas) == 1
    assert fake_s3.chamadas[0][0] == ons_client.BUCKET
    assert fake_s3.chamadas[0][1] == key

    # 2. Segunda chamada usa o cache local sem acionar o S3 novamente
    caminho2 = ons_client.baixar(key, forcar=False)
    assert caminho2 == caminho1
    assert len(fake_s3.chamadas) == 1

    # 3. Com forcar=True, refaz o download no S3
    fake_s3.conteudo = b"dados-ons-atualizados"
    caminho3 = ons_client.baixar(key, forcar=True)
    assert caminho3 == caminho1
    assert caminho3.read_bytes() == b"dados-ons-atualizados"
    assert len(fake_s3.chamadas) == 2


def test_baixar_remove_temporario_em_caso_de_erro(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ons_client, "DATA_DIR", tmp_path)
    fake_s3 = FakeS3Client(falhar=True)
    monkeypatch.setattr(ons_client, "_client", lambda: fake_s3)

    key = "dataset/cmo_tm/CMO_2025.parquet"
    with pytest.raises(RuntimeError, match="falha simulada"):
        ons_client.baixar(key)

    destino = tmp_path / key
    assert not destino.exists()
    arquivos_restantes = list(destino.parent.glob("*"))
    assert arquivos_restantes == []
