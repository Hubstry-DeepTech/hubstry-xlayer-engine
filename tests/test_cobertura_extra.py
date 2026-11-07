"""
Casos adicionais para para_numero e baixar que nao constam em
test_utils_and_ons_client.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.digital_twin import ons_client
from src.digital_twin.utils import para_numero

KEY = "dataset/restricao_coff_eolica_detail_tm/ARQ_2023_01.parquet"


class FakeS3Parcial:
    """Escreve metade do conteudo no destino e so entao pode falhar."""

    def __init__(self, conteudo: bytes = b"dados", falhar: bool = False):
        self.conteudo = conteudo
        self.falhar = falhar

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        meio = len(self.conteudo) // 2
        with open(filename, "wb") as f:
            f.write(self.conteudo[:meio])
            if self.falhar:
                raise RuntimeError("falha no meio do download")
            f.write(self.conteudo[meio:])


def _valores(s: pd.Series) -> list:
    return [None if pd.isna(v) else float(v) for v in para_numero(s)]


def test_para_numero_milhar_multiplo():
    assert _valores(pd.Series(["1.234.567,89"])) == pytest.approx([1234567.89])


def test_para_numero_valores_ja_numericos():
    s = pd.Series([1, 2.5, 0, float("nan")])
    assert _valores(s) == [1.0, 2.5, 0.0, None]


def test_para_numero_mistura_preserva_posicoes_e_indice():
    s = pd.Series(["1,5", "", "-", "2"], index=[10, 20, 30, 40])
    res = para_numero(s)
    assert res.index.tolist() == [10, 20, 30, 40]
    assert _valores(s) == [1.5, None, None, 2.0]


def test_baixar_ignora_barra_inicial_da_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(ons_client, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ons_client, "_client", lambda: FakeS3Parcial())
    assert ons_client.baixar("/" + KEY) == tmp_path / KEY


def test_baixar_falha_parcial_com_forcar_preserva_arquivo_anterior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    destino = tmp_path / KEY
    destino.parent.mkdir(parents=True)
    destino.write_bytes(b"antigo")
    monkeypatch.setattr(ons_client, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ons_client, "_client", lambda: FakeS3Parcial(falhar=True))

    with pytest.raises(RuntimeError, match="meio do download"):
        ons_client.baixar(KEY, forcar=True)

    assert destino.read_bytes() == b"antigo"
    assert [p.name for p in destino.parent.iterdir()] == [destino.name]


def test_baixar_falha_parcial_sem_arquivo_previo_nao_deixa_nada(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(ons_client, "DATA_DIR", tmp_path)
    monkeypatch.setattr(ons_client, "_client", lambda: FakeS3Parcial(falhar=True))

    with pytest.raises(RuntimeError):
        ons_client.baixar(KEY)

    assert list((tmp_path / KEY).parent.iterdir()) == []
