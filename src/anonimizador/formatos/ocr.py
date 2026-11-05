"""Localização dos dados de idioma do OCR (Tesseract).

O PyMuPDF já traz o motor do Tesseract embutido; só precisa dos arquivos de
idioma (por.traineddata). A versão para Windows publicada no GitHub inclui
esses arquivos na pasta "tessdata" ao lado do executável.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def pasta_do_programa() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[3]


def _candidatos() -> list[Path]:
    c: list[Path] = []
    if os.environ.get("TESSDATA_PREFIX"):
        p = Path(os.environ["TESSDATA_PREFIX"])
        c += [p, p / "tessdata"]
    base = pasta_do_programa()
    c += [base / "tessdata", base / "tesseract" / "tessdata", base / "build" / "tessdata"]
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).parent
        c += [exe / "tessdata", exe / "_internal" / "tessdata"]
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        raiz = os.environ.get(var)
        if raiz:
            c += [Path(raiz) / "Tesseract-OCR" / "tessdata",
                  Path(raiz) / "Programs" / "Tesseract-OCR" / "tessdata"]
    c += [Path("/usr/share/tesseract-ocr/5/tessdata"), Path("/usr/share/tesseract-ocr/4.00/tessdata"),
          Path("/usr/share/tessdata"), Path("/usr/local/share/tessdata"),
          Path("/opt/homebrew/share/tessdata")]
    return c


def localizar_tessdata(idioma: str = "por") -> str | None:
    principal = idioma.split("+")[0]
    for p in _candidatos():
        try:
            if (p / f"{principal}.traineddata").is_file():
                return str(p)
        except OSError:
            continue
    return None


def ocr_disponivel(idioma: str = "por") -> tuple[bool, str]:
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        try:
            import fitz  # noqa: F401
        except ImportError:
            return False, "PyMuPDF não está instalado."
    pasta = localizar_tessdata(idioma)
    if not pasta:
        return False, (f"Dados de idioma '{idioma}.traineddata' não encontrados. Instale o Tesseract "
                       "OCR com o idioma Português ou use a versão do GitHub, que já os inclui.")
    return True, f"OCR pronto (idioma {idioma}, dados em {pasta})."
