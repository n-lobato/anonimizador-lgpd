"""Execução em segundo plano, para a janela não travar."""

from __future__ import annotations

import traceback
from typing import Callable

from PySide6.QtCore import QThread, Signal


class Trabalho(QThread):
    progresso = Signal(int, int, str)
    concluido = Signal()
    falhou = Signal(str)

    def __init__(self, funcao: Callable, parent=None):
        super().__init__(parent)
        self._funcao = funcao
        self._cancelar = False

    def cancelar(self) -> None:
        self._cancelar = True

    def run(self) -> None:
        try:
            self._funcao(self.progresso.emit, lambda: self._cancelar)
            self.concluido.emit()
        except Exception:
            self.falhou.emit(traceback.format_exc())
