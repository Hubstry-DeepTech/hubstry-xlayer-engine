"""
Hubstry X-Layer Engine — Cliente de dados do ONS
================================================
Le dados reais do Portal de Dados Abertos do ONS a partir do bucket
publico no Registry of Open Data on AWS.

  Bucket : ons-aws-prod-opendata
  Regiao : sa-east-1
  Acesso : anonimo (UNSIGNED / --no-sign-request)
  Licenca: CC-BY 4.0

Estrutura verificada por listagem em 29/08/2026:

  dataset/restricao_coff_eolica_detail_tm/
      RESTRICAO_COFF_EOLICA_DETAIL_<ANO>_<MES>.parquet   (2023 em diante)
      RESTRICAO_COFF_EOLICA_DETAIL_<ANO>_<MES>.csv       (2021 em diante)
      RESTRICAO_COFF_EOLICA_DETAIL_<ANO>_<MES>.xlsx
      DicionarioDados_*.json  /  DicionarioDados_*.pdf

Parquet e cerca de 18x menor que o CSV equivalente (9 MB contra
160 MB em 2023_01). Sempre preferir Parquet. Meses anteriores a 2023
so tem CSV e XLSX.

NAO COMMITAR OS ARQUIVOS BAIXADOS. O CSV mensal ultrapassa o limite
rigido de 100 MB do GitHub e o Parquet infla o repositorio de forma
irreversivel. Manter data/ no .gitignore.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

import boto3
import pandas as pd
from botocore import UNSIGNED
from botocore.config import Config

BUCKET = "ons-aws-prod-opendata"
REGION = "sa-east-1"

# Prefixos confirmados por listagem. Sufixos como _tm fazem parte do
# caminho real no bucket e NAO coincidem com o slug do CKAN.
PREFIXOS = {
    "coff_eolica_detail": "dataset/restricao_coff_eolica_detail_tm/",
    "cmo_semanal": "dataset/cmo_se/",
}

DATA_DIR = Path(os.environ.get("XLAYER_DATA_DIR", "data/ons"))


def _client():
    """Cliente anonimo: ignora credenciais locais e politicas de IAM."""
    return boto3.client("s3", region_name=REGION,
                        config=Config(signature_version=UNSIGNED))


# ----------------------------------------------------------------------
# Descoberta
# ----------------------------------------------------------------------

@dataclass
class Objeto:
    key: str
    tamanho: int

    @property
    def nome(self) -> str:
        return self.key.rsplit("/", 1)[-1]

    @property
    def extensao(self) -> str:
        return self.nome.rsplit(".", 1)[-1].lower() if "." in self.nome else ""


def listar(prefixo: str, contendo: Optional[str] = None) -> List[Objeto]:
    s3 = _client()
    paginador = s3.get_paginator("list_objects_v2")
    achados: List[Objeto] = []
    for pagina in paginador.paginate(Bucket=BUCKET, Prefix=prefixo):
        for obj in pagina.get("Contents", []):
            if obj["Size"] == 0:
                continue
            if contendo and contendo not in obj["Key"]:
                continue
            achados.append(Objeto(key=obj["Key"], tamanho=obj["Size"]))
    return sorted(achados, key=lambda o: o.key)


def procurar_prefixos(termo: str, limite: int = 40) -> List[str]:
    """Descobre prefixos novos sem depender da CLI."""
    s3 = _client()
    paginador = s3.get_paginator("list_objects_v2")
    vistos: Set[str] = set()
    for pagina in paginador.paginate(Bucket=BUCKET, Prefix="dataset/", Delimiter="/"):
        for cp in pagina.get("CommonPrefixes", []):
            p = cp["Prefix"]
            if termo.lower() in p.lower():
                vistos.add(p)
            if len(vistos) >= limite:
                return sorted(vistos)
    return sorted(vistos)


# ----------------------------------------------------------------------
# Download com cache local
# ----------------------------------------------------------------------

def baixar(key: str, forcar: bool = False) -> Path:
    destino = DATA_DIR / key.rsplit("/", 1)[-1]
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not forcar:
        return destino
    _client().download_file(BUCKET, key, str(destino))
    return destino


def dicionario_de_dados(chave_prefixo: str = "coff_eolica_detail") -> dict:
    """
    Baixa e devolve o dicionario de dados em JSON.
    Rode isto ANTES de escrever qualquer codigo que dependa de nomes
    de coluna.
    """
    objs = listar(PREFIXOS[chave_prefixo], contendo="DicionarioDados")
    jsons = [o for o in objs if o.extensao == "json"]
    if not jsons:
        raise FileNotFoundError("dicionario de dados em JSON nao encontrado")
    caminho = baixar(jsons[0].key)
    return json.loads(caminho.read_text(encoding="utf-8-sig"))


# ----------------------------------------------------------------------
# Carga
# ----------------------------------------------------------------------

def carregar_mes(ano: int, mes: int,
                 chave_prefixo: str = "coff_eolica_detail") -> pd.DataFrame:
    """
    Carrega um mes de restricao de operacao. Prefere Parquet; cai para
    CSV quando o Parquet nao existe (meses anteriores a 2023).
    """
    prefixo = PREFIXOS[chave_prefixo]
    sufixo = f"_{ano}_{mes:02d}."
    objs = listar(prefixo, contendo=sufixo)
    if not objs:
        raise FileNotFoundError(f"nenhum arquivo para {ano}-{mes:02d} em {prefixo}")

    parquets = [o for o in objs if o.extensao == "parquet"]
    if parquets:
        return pd.read_parquet(baixar(parquets[0].key))

    csvs = [o for o in objs if o.extensao == "csv"]
    if not csvs:
        raise FileNotFoundError(f"nem parquet nem csv para {ano}-{mes:02d}")
    print(f"  AVISO: {ano}-{mes:02d} sem parquet; baixando CSV de "
          f"{csvs[0].tamanho / 1e6:.0f} MB")
    # Separador e decimal a confirmar contra o arquivo real.
    return pd.read_csv(baixar(csvs[0].key), sep=";", decimal=",",
                       encoding="utf-8", low_memory=False)


def carregar_periodo(meses: Iterable[Tuple[int, int]], **kw) -> pd.DataFrame:
    partes = [carregar_mes(a, m, **kw) for a, m in meses]
    return pd.concat(partes, ignore_index=True)


# ----------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Bucket: {BUCKET} ({REGION}), acesso anonimo\n")

    print("Prefixos com 'restricao':")
    for p in procurar_prefixos("restricao"):
        print(f"  {p}")

    print("\nPrefixos com 'cmo':")
    for p in procurar_prefixos("cmo"):
        print(f"  {p}")

    print("\nDicionario de dados (coff_eolica_detail):")
    try:
        dic = dicionario_de_dados()
        print(json.dumps(dic, indent=2, ensure_ascii=False)[:3000])
    except Exception as exc:
        print(f"  falhou: {exc}")

    print("\nAmostra de 2023-01:")
    try:
        df = carregar_mes(2023, 1)
        print(f"  linhas: {len(df):,}   colunas: {len(df.columns)}")
        print(f"  colunas: {list(df.columns)}")
        print(df.head(3).to_string())
    except Exception as exc:
        print(f"  falhou: {exc}")
