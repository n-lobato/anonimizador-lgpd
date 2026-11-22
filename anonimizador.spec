# -*- mode: python ; coding: utf-8 -*-
# Gera dois executáveis na mesma pasta, compartilhando as bibliotecas:
#   AnonimizadorLGPD(.exe)   (janela)
#   anonimizador-cli(.exe)   (linha de comando)
# No Mac, a pasta vira o aplicativo "Anonimizador LGPD.app" (os dois executáveis
# ficam em Contents/MacOS).
# Uso: pyinstaller anonimizador.spec   (antes, rode build/baixar_tessdata.py)
import re
import sys
from pathlib import Path

raiz = Path(SPECPATH)
datas = [(str(raiz / "assets"), "assets")]
tess = raiz / "build" / "tessdata"
if tess.is_dir():
    datas.append((str(tess), "tessdata"))

excluir = ["tkinter", "spacy", "torch", "matplotlib", "numpy.distutils", "onnxruntime",
           "pymupdf4llm", "pymupdf_layout", "pymupdf.layout", "networkx", "pytest",
           "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
           "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
           "PySide6.QtDataVisualization", "PySide6.QtPdf"]
if sys.platform == "darwin":
    # o programa não usa o numpy; no Mac com chip Apple a versão dele exige o macOS 14
    excluir.append("numpy")

a = Analysis(
    [str(raiz / "iniciar.py")],
    pathex=[str(raiz / "src")],
    datas=datas,
    hiddenimports=["anonimizador.formatos.docx", "anonimizador.formatos.pdf",
                   "anonimizador.formatos.imagem", "anonimizador.formatos.planilha",
                   "anonimizador.formatos.texto_simples", "anonimizador.formatos.limites",
                   "anonimizador.formatos.imagens_office", "anonimizador.gui.janela",
                   # o openpyxl só usa o defusedxml (proteção contra XML malicioso) se ele estiver no pacote
                   "defusedxml", "defusedxml.ElementTree"],
    excludes=excluir,
    noarchive=False,
)
pyz = PYZ(a.pure)
mac = sys.platform == "darwin"
icone = str(raiz / "assets" / ("icone.png" if mac else "icone.ico"))
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="AnonimizadorLGPD",
          console=False, icon=icone, upx=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name="anonimizador-cli",
          console=True, icon=icone, upx=False)
coll = COLLECT(gui, cli, a.binaries, a.datas, name="AnonimizadorLGPD", upx=False)

if mac:
    versao = re.search(r'__version__ = "(.+)"',
                       (raiz / "src" / "anonimizador" / "__init__.py").read_text(encoding="utf-8")).group(1)
    app = BUNDLE(
        coll,
        name="Anonimizador LGPD.app",
        icon=icone,
        bundle_identifier="io.github.n-lobato.anonimizador-lgpd",
        version=versao,
        info_plist={
            "CFBundleDisplayName": "Anonimizador LGPD",
            "CFBundleShortVersionString": versao,
            "CFBundleVersion": versao,
            "NSHighResolutionCapable": True,
            "NSHumanReadableCopyright": "© 2026 n-lobato. Software livre (GNU GPL v3).",
            # permite soltar arquivos e pastas sobre o ícone do programa no Dock
            "CFBundleDocumentTypes": [{
                "CFBundleTypeName": "Documento",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "LSItemContentTypes": ["public.data", "public.folder"],
            }],
        },
    )
