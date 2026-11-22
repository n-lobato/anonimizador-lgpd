"""Reúne as licenças dos componentes de terceiros que vão dentro do pacote.

Uso: python build/coletar_licencas.py PASTA_DO_PACOTE

Grava, dentro de PASTA_DO_PACOTE:
- THIRD-PARTY-NOTICES.md: lista dos componentes, versões e licenças, com as
  observações que as licenças LGPL e AGPL pedem;
- LICENCAS/: os textos das licenças, uma subpasta por componente.

Só entram as bibliotecas que o programa usa de fato (requirements.txt e as
dependências delas), e não as ferramentas de build e de teste. O build falha se
faltar a licença de algum componente principal.
"""

from __future__ import annotations

import re
import shutil
import sys
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PRINCIPAIS = {"pyside6-essentials", "shiboken6", "pymupdf", "lxml", "openpyxl", "pillow"}
NAO_EMPACOTADOS = {"pyside6-addons"}  # o spec exclui os módulos extras do Qt


def _norm(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _raizes() -> list[str]:
    nomes = []
    for linha in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines():
        linha = linha.split("#")[0].strip()
        if linha and not linha.startswith("-"):
            nomes.append(re.split(r"[<>=!~\[; ]", linha)[0])
    return nomes


def _dependencias(nomes: list[str]) -> list[metadata.Distribution]:
    vistos: dict[str, metadata.Distribution] = {}
    fila = list(nomes)
    while fila:
        nome = _norm(fila.pop())
        if nome in vistos or nome in NAO_EMPACOTADOS:
            continue
        try:
            dist = metadata.distribution(nome)
        except metadata.PackageNotFoundError:
            continue
        vistos[nome] = dist
        for req in dist.requires or []:
            if "extra ==" in req:
                continue
            # dependência de outro sistema não está instalada aqui e é ignorada acima
            fila.append(re.split(r"[<>=!~\[; (]", req.strip())[0])
    return sorted(vistos.values(), key=lambda d: _norm(d.metadata["Name"]))


def _licenca(dist: metadata.Distribution) -> str:
    md = dist.metadata
    for campo in ("License-Expression", "License"):
        v = md.get(campo)
        if v and len(v) < 100 and v.strip().upper() != "UNKNOWN":
            return v.strip()
    cls = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    return "; ".join(cls) or "não declarada (ver o site do projeto)"


def _site(dist: metadata.Distribution) -> str:
    md = dist.metadata
    if md.get("Home-page"):
        return md["Home-page"]
    for url in md.get_all("Project-URL") or []:
        return url.split(",", 1)[-1].strip()
    return ""


def _copiar_licencas(dist: metadata.Distribution, destino: Path) -> int:
    n = 0
    for f in dist.files or []:
        if any(k in f.name.upper() for k in ("LICEN", "COPYING", "NOTICE", "AUTHORS")):
            origem = Path(dist.locate_file(f))
            if origem.is_file():
                destino.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, destino / origem.name)
                n += 1
    return n


def _licenca_python(destino: Path) -> bool:
    versao = f"{sys.version_info.major}.{sys.version_info.minor}"
    base = Path(sys.base_prefix)
    for c in (base / "LICENSE.txt", base / "lib" / f"python{versao}" / "LICENSE.txt",
              base / "lib" / f"python{versao}" / "LICENSE", Path(f"/usr/share/doc/python{versao}/copyright")):
        if c.is_file():
            destino.mkdir(parents=True, exist_ok=True)
            shutil.copy2(c, destino / "LICENSE.txt")
            return True
    return False


CABECALHO = """# Componentes de terceiros

O Anonimizador LGPD (GPL-3.0, autor n-lobato) é distribuído junto com os componentes
abaixo, cada um sob a própria licença. Os textos das licenças estão na pasta `LICENCAS`.
Código-fonte do programa: https://github.com/n-lobato/anonimizador-lgpd

## Observações exigidas pelas licenças

- **Qt e PySide6 (LGPL-3.0).** As bibliotecas do Qt e do PySide6 ficam em arquivos
  separados dentro do pacote e podem ser trocadas por outras versões compatíveis.
  Código-fonte: https://download.qt.io/official_releases/ e
  https://code.qt.io/cgit/pyside/pyside-setup.git/
- **PyMuPDF e MuPDF (AGPL-3.0).** O PyMuPDF inclui o MuPDF e o motor de OCR Tesseract
  (Apache-2.0). Código-fonte: https://github.com/pymupdf/PyMuPDF e
  https://mupdf.com/releases . O código deste programa também é aberto (GPL-3.0, que a
  AGPL-3.0 permite combinar), no endereço acima.
- **Dados de idioma do OCR** (`tessdata`, arquivos por e eng): projeto tessdata_fast,
  Apache-2.0, https://github.com/tesseract-ocr/tessdata_fast
- **Python** (PSF License): https://www.python.org
- Bibliotecas que trazem outras dentro de si (por exemplo, o Pillow, com libjpeg, libpng
  e outras, e o lxml, com libxml2 e libxslt) listam essas licenças nos próprios arquivos
  em `LICENCAS`.

## Bibliotecas incluídas

| Componente | Versão | Licença | Site |
| --- | --- | --- | --- |
"""


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pacote = Path(sys.argv[1])
    pasta = pacote / "LICENCAS"
    shutil.rmtree(pasta, ignore_errors=True)
    pasta.mkdir(parents=True)
    linhas = [CABECALHO.rstrip("\n")]
    sem_texto, faltando = [], []
    dists = _dependencias(_raizes())
    nomes = {_norm(d.metadata["Name"]) for d in dists}
    for d in dists:
        nome = d.metadata["Name"]
        licenca = _licenca(d)
        linhas.append(f"| {nome} | {d.version} | {licenca} | {_site(d)} |")
        if not _copiar_licencas(d, pasta / nome):
            sem_texto.append(nome)
            if _norm(nome) in PRINCIPAIS and licenca.startswith("não declarada"):
                faltando.append(nome)
    faltando += sorted(PRINCIPAIS - nomes)
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    linhas.append(f"| Python | {py} | PSF-2.0 | https://www.python.org |")
    if not _licenca_python(pasta / "Python"):
        sem_texto.append("Python")
    tess = RAIZ / "build" / "tessdata" / "LICENSE-tessdata_fast.txt"
    linhas.append("| tessdata_fast (dados do OCR) | commit 8741641 | Apache-2.0 | "
                  "https://github.com/tesseract-ocr/tessdata_fast |")
    if tess.is_file():
        (pasta / "tessdata_fast").mkdir()
        shutil.copy2(tess, pasta / "tessdata_fast" / "LICENSE")
    else:
        faltando.append("tessdata_fast (rode build/baixar_tessdata.py antes)")
    (pacote / "THIRD-PARTY-NOTICES.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"{len(dists) + 2} componentes listados em {pacote / 'THIRD-PARTY-NOTICES.md'}")
    if sem_texto:
        print("Sem arquivo de licença no pacote instalado (consta só na tabela):", ", ".join(sem_texto))
    if faltando:
        print("ERRO: falta a licença de:", ", ".join(faltando))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
