# -*- mode: python ; coding: utf-8 -*-
# Gera dois executáveis na mesma pasta, compartilhando as bibliotecas:
#   AnonimizadorLGPD.exe   (janela)
#   anonimizador-cli.exe   (linha de comando)
# Uso: pyinstaller anonimizador.spec   (antes, rode build/baixar_tessdata.py)
from pathlib import Path

raiz = Path(SPECPATH)
datas = [(str(raiz / "assets"), "assets")]
tess = raiz / "build" / "tessdata"
if tess.is_dir():
    datas.append((str(tess), "tessdata"))

a = Analysis(
    [str(raiz / "iniciar.py")],
    pathex=[str(raiz / "src")],
    datas=datas,
    hiddenimports=["anonimizador.formatos.docx", "anonimizador.formatos.pdf",
                   "anonimizador.formatos.imagem", "anonimizador.formatos.planilha",
                   "anonimizador.formatos.texto_simples", "anonimizador.gui.janela"],
    excludes=["tkinter", "spacy", "torch", "matplotlib", "numpy.distutils", "onnxruntime",
              "pymupdf4llm", "pymupdf_layout", "pymupdf.layout", "networkx", "pytest",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
              "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
              "PySide6.QtDataVisualization", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure)
icone = str(raiz / "assets" / "icone.ico")
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AnonimizadorLGPD",
          console=False, icon=icone, upx=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name="anonimizador-cli",
          console=True, icon=icone, upx=False)
coll = COLLECT(gui, cli, a.binaries, a.datas, name="AnonimizadorLGPD", upx=False)
