"""Leitura e escrita de cada formato de arquivo suportado."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ErroFormato(Exception):
    """Erro esperado ao ler ou gravar um arquivo (mensagem amigável)."""


@dataclass
class Opcoes:
    ocr: bool = True
    forcar_ocr: bool = False
    idioma_ocr: str = "por"
    dpi_ocr: int = 300


@dataclass
class Extraido:
    texto: str
    avisos: list[str] = field(default_factory=list)
    cache: Any = None


def _modulos():
    from . import docx, imagem, pdf, planilha, texto_simples
    return {
        ".docx": docx, ".docm": docx,
        ".pdf": pdf,
        ".txt": texto_simples, ".md": texto_simples, ".csv": texto_simples,
        ".log": texto_simples, ".srt": texto_simples, ".vtt": texto_simples,
        ".xlsx": planilha, ".xlsm": planilha,
        ".png": imagem, ".jpg": imagem, ".jpeg": imagem, ".tif": imagem,
        ".tiff": imagem, ".bmp": imagem,
    }


EXTENSOES = (".docx", ".docm", ".pdf", ".txt", ".md", ".csv", ".log", ".srt", ".vtt",
             ".xlsx", ".xlsm", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")

NAO_SUPORTADOS = {
    ".doc": "formato antigo do Word: abra no Word e salve como .docx",
    ".rtf": "abra no Word e salve como .docx",
    ".odt": "abra no LibreOffice/Word e salve como .docx",
    ".xls": "formato antigo do Excel: salve como .xlsx",
    ".ods": "salve como .xlsx",
    ".pptx": "apresentações ainda não são suportadas: exporte como PDF",
    ".ppt": "apresentações ainda não são suportadas: exporte como PDF",
}


def modulo_para(extensao: str):
    return _modulos().get(extensao.lower())
