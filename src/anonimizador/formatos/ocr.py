"""Localização dos dados de idioma do OCR (Tesseract).

O PyMuPDF já traz o motor do Tesseract embutido; só precisa dos arquivos de
idioma (por.traineddata). A versão para Windows publicada no GitHub inclui
esses arquivos na pasta "tessdata" ao lado do executável.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_SEGUROS: dict[str, str] = {}


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


def _nome_curto(caminho: str) -> str | None:
    """Nome 8.3 do Windows (ex.: C:\\Users\\X\\ONEDRI~1\\AREADE~1), que não tem acento."""
    try:
        import ctypes
        from ctypes import wintypes
        f = ctypes.windll.kernel32.GetShortPathNameW  # type: ignore[attr-defined]
        f.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        buf = ctypes.create_unicode_buffer(1024)
        return buf.value if f(caminho, buf, 1024) else None
    except Exception:
        return None


def caminho_seguro(pasta: str) -> str:
    """No Windows, o Tesseract não abre os dados de idioma se o caminho tiver acento ou
    outro caractere fora do ASCII (ex.: "Área de Trabalho", "C:\\Users\\João"): o OCR
    volta vazio, sem erro. Nesse caso usa o nome curto da pasta ou uma cópia dos dados
    num lugar sem acento."""
    if os.name != "nt" or pasta.isascii():
        return pasta
    if pasta in _SEGUROS:
        return _SEGUROS[pasta]
    curto = _nome_curto(pasta)
    if curto and curto.isascii() and Path(curto).is_dir():
        _SEGUROS[pasta] = curto
        return curto
    for raiz in (os.environ.get("PROGRAMDATA"), os.environ.get("PUBLIC"), r"C:\ProgramData"):
        if not raiz:
            continue
        destino = Path(raiz) / "AnonimizadorLGPD" / "tessdata"
        if not str(destino).isascii():
            continue
        try:
            destino.mkdir(parents=True, exist_ok=True)
            for arq in Path(pasta).glob("*.traineddata"):
                alvo = destino / arq.name
                if not alvo.exists() or alvo.stat().st_size != arq.stat().st_size:
                    shutil.copy2(arq, alvo)
            _SEGUROS[pasta] = str(destino)
            return str(destino)
        except OSError:
            continue
    return pasta


def localizar_tessdata(idioma: str = "por") -> str | None:
    principal = idioma.split("+")[0]
    for p in _candidatos():
        try:
            if (p / f"{principal}.traineddata").is_file():
                return caminho_seguro(str(p))
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
