"""Baixa os dados de idioma do OCR (português e inglês) para build/tessdata.

Executado no GitHub Actions antes do PyInstaller. Os arquivos vêm do
repositório oficial tesseract-ocr/tessdata_fast (licença Apache-2.0).
"""
import sys
import urllib.request
from pathlib import Path

BASE = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/{}.traineddata"
destino = Path(__file__).resolve().parent / "tessdata"
destino.mkdir(exist_ok=True)
for idioma in ("por", "eng"):
    arq = destino / f"{idioma}.traineddata"
    if arq.exists() and arq.stat().st_size > 1_000_000:
        continue
    print("Baixando", idioma)
    urllib.request.urlretrieve(BASE.format(idioma), arq)
    if arq.stat().st_size < 1_000_000:
        sys.exit(f"Download incompleto: {arq}")
print("tessdata pronto em", destino)
