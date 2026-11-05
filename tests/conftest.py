import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

PETICAO = """EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA 2ª VARA CÍVEL DE BRASÍLIA/DF

Processo nº 0701234-93.2026.8.07.0001

MARIA APARECIDA DE SOUZA SANTOS, brasileira, casada, portadora da Carteira de Identidade nº 1.234.567 SSP/DF, inscrita no CPF sob o nº 529.982.247-25, residente e domiciliada na SQS 308, Bloco C, Apto 101, Asa Sul, Brasília/DF, CEP 70355-030, telefone (61) 99876-5432, e-mail maria.souza@gmail.com, vem, por seu advogado, Dr. Thalysson Rodrigues Pereira, OAB/DF nº 45.678, propor a presente ação em face de José Carlos da Silva Filho, nascido em 12/03/1980.

A testemunha Kauã Ribeiro confirmou. Conforme a Lei Maria da Penha e o Tribunal de Justiça do Distrito Federal.

MARIA: Confirmo, excelência.
"""


@pytest.fixture(autouse=True)
def config_isolada(tmp_path, monkeypatch):
    pasta = tmp_path / "config"
    pasta.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(pasta))
    monkeypatch.setenv("APPDATA", str(pasta))
    yield


@pytest.fixture
def peticao():
    return PETICAO


def pymupdf():
    try:
        import pymupdf as f
        return f
    except ImportError:
        try:
            import fitz as f
            return f
        except ImportError:
            return None
