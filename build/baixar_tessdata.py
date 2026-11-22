"""Baixa os dados de idioma do OCR (português e inglês) para build/tessdata.

Executado no GitHub Actions antes do PyInstaller. Os arquivos vêm do
repositório oficial tesseract-ocr/tessdata_fast (licença Apache-2.0), numa
versão fixa (commit) e com a impressão digital (SHA-256) conferida: se o
arquivo baixado não for exatamente o esperado, o build para. Assim um arquivo
trocado no servidor não entra no programa sem ninguém perceber.

Para atualizar os dados no futuro, troque COMMIT e os SHA-256 abaixo pelos da
nova versão (o SHA-256 sai de "Get-FileHash arquivo" no Windows ou
"sha256sum arquivo" no Linux).
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

COMMIT = "87416418657359cb625c412a48b6e1d6d41c29bd"  # tessdata_fast, 01/08/2024
BASE = f"https://github.com/tesseract-ocr/tessdata_fast/raw/{COMMIT}/{{}}.traineddata"
SHA256 = {
    "por": "c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb",
    "eng": "7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2",
}


def sha256(arquivo: Path) -> str:
    h = hashlib.sha256()
    with open(arquivo, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


destino = Path(__file__).resolve().parent / "tessdata"
destino.mkdir(exist_ok=True)
for idioma, esperado in SHA256.items():
    arq = destino / f"{idioma}.traineddata"
    if arq.exists() and sha256(arq) == esperado:
        continue
    print("Baixando", idioma)
    urllib.request.urlretrieve(BASE.format(idioma), arq)
    obtido = sha256(arq)
    if obtido != esperado:
        arq.unlink()
        sys.exit(f"SHA-256 diferente do esperado em {idioma}.traineddata: {obtido}")

# texto da licença (Apache-2.0) do mesmo commit, para ir junto no pacote
licenca = destino / "LICENSE-tessdata_fast.txt"
if not licenca.exists():
    urllib.request.urlretrieve(f"https://github.com/tesseract-ocr/tessdata_fast/raw/{COMMIT}/LICENSE", licenca)
if "Apache License" not in licenca.read_text(encoding="utf-8", errors="replace"):
    licenca.unlink()
    sys.exit("O arquivo LICENSE do tessdata_fast não é a licença Apache esperada.")
print("tessdata pronto e conferido em", destino)
