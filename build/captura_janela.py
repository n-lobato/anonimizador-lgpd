"""Tira fotos da janela principal em tamanhos de tela comuns (conferência visual do layout).

Uso: python build/captura_janela.py PASTA_DE_SAIDA
"""

import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtWidgets import QApplication  # noqa: E402

from anonimizador.gui.janela import JanelaPrincipal  # noqa: E402

saida = Path(sys.argv[1])
saida.mkdir(parents=True, exist_ok=True)
app = QApplication(sys.argv[:1])
app.setStyle("Fusion")
j = JanelaPrincipal([])
j.show()
for _ in range(5):
    app.processEvents()
livre = j.screen().availableGeometry()
moldura = j.frameGeometry()
print(f"inicial: área livre da tela {livre.width()}x{livre.height()} em ({livre.x()},{livre.y()}); "
      f"janela com moldura {moldura.width()}x{moldura.height()} em ({moldura.x()},{moldura.y()}); "
      f"cabe: {livre.contains(moldura)}")
j.grab().save(str(saida / "janela_inicial.png"))
for largura, altura in ((820, 720), (1366, 705), (1366, 600), (1920, 1000)):
    j.resize(largura, altura)
    j.show()
    for _ in range(5):
        app.processEvents()
    arq = saida / f"janela_{largura}x{altura}.png"
    j.grab().save(str(arq))
    print("captura", largura, altura, "tamanho real:", j.width(), j.height())
    if os.environ.get("CAPTURA_NO_LOG") and largura == 1366:
        # artefatos nem sempre podem ser baixados de fora; o log sempre pode
        print(f"BASE64 {arq.name} " + base64.b64encode(arq.read_bytes()).decode())
j.close()
