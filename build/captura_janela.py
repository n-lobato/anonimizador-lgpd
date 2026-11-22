"""Tira fotos da janela principal em tamanhos de tela comuns (conferência visual do layout).

Uso: python build/captura_janela.py PASTA_DE_SAIDA
"""

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
for largura, altura in ((820, 720), (1366, 705), (1366, 600), (1920, 1000)):
    j.resize(largura, altura)
    j.show()
    for _ in range(5):
        app.processEvents()
    j.grab().save(str(saida / f"janela_{largura}x{altura}.png"))
    print("captura", largura, altura, "tamanho real:", j.width(), j.height())
j.close()
