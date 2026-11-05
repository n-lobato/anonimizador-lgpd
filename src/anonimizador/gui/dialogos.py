"""Diálogos auxiliares: lista de termos, tipos de dados e novo termo."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget, QInputDialog)

from ..config import Termos
from ..deteccao.modelo import TIPOS, descricao


def aceito(resultado) -> bool:
    """Compatível com as diferentes formas de enum do PySide6."""
    return resultado == QDialog.DialogCode.Accepted or resultado == 1


def combo_tipos(selecionado: str = "PESSOA") -> QComboBox:
    c = QComboBox()
    for t in TIPOS:
        c.addItem(descricao(t), t)
    i = c.findData(selecionado)
    c.setCurrentIndex(i if i >= 0 else 0)
    return c


class DialogoTermos(QDialog):
    """Termos que sempre (ou nunca) devem ser anonimizados."""

    def __init__(self, termos: Termos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Minha lista de termos")
        self.resize(640, 460)
        self.termos = termos
        abas = QTabWidget()

        # --- sempre
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.addWidget(QLabel("Nomes, apelidos ou expressões que devem ser anonimizados sempre que "
                            "aparecerem (ex.: nomes que o programa não reconheceu)."))
        self.tabela = QTableWidget(0, 2)
        self.tabela.setHorizontalHeaderLabels(["Termo", "Tipo"])
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        for item in termos.sempre:
            self._linha_sempre(item.get("termo", ""), item.get("tipo", "TERMO"))
        l1.addWidget(self.tabela)
        b1 = QHBoxLayout()
        add1, rem1 = QPushButton("Adicionar"), QPushButton("Remover selecionados")
        add1.clicked.connect(lambda: self._linha_sempre("", "PESSOA", editar=True))
        rem1.clicked.connect(self._remover_sempre)
        b1.addWidget(add1)
        b1.addWidget(rem1)
        b1.addStretch()
        l1.addLayout(b1)
        abas.addTab(w1, "Sempre anonimizar")

        # --- nunca
        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        l2.addWidget(QLabel("Expressões que NUNCA devem ser anonimizadas, mesmo que pareçam nomes "
                            "(ex.: nome do órgão, de uma lei ou de um logradouro público)."))
        self.lista = QListWidget()
        self.lista.addItems(termos.nunca)
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        l2.addWidget(self.lista)
        b2 = QHBoxLayout()
        add2, rem2 = QPushButton("Adicionar"), QPushButton("Remover selecionados")
        add2.clicked.connect(self._adicionar_nunca)
        rem2.clicked.connect(lambda: [self.lista.takeItem(self.lista.row(i)) for i in self.lista.selectedItems()])
        b2.addWidget(add2)
        b2.addWidget(rem2)
        b2.addStretch()
        l2.addLayout(b2)
        abas.addTab(w2, "Nunca anonimizar")

        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(abas)
        layout.addWidget(botoes)

    def _linha_sempre(self, termo: str, tipo: str, editar: bool = False) -> None:
        r = self.tabela.rowCount()
        self.tabela.insertRow(r)
        self.tabela.setItem(r, 0, QTableWidgetItem(termo))
        self.tabela.setCellWidget(r, 1, combo_tipos(tipo))
        if editar:
            self.tabela.editItem(self.tabela.item(r, 0))

    def _remover_sempre(self) -> None:
        for r in sorted({i.row() for i in self.tabela.selectedIndexes()}, reverse=True):
            self.tabela.removeRow(r)

    def _adicionar_nunca(self) -> None:
        texto, ok = QInputDialog.getText(self, "Nunca anonimizar", "Expressão:")
        if ok and texto.strip():
            self.lista.addItem(texto.strip())

    def resultado(self) -> Termos:
        sempre = []
        for r in range(self.tabela.rowCount()):
            item = self.tabela.item(r, 0)
            termo = item.text().strip() if item else ""
            if termo:
                sempre.append({"termo": termo, "tipo": self.tabela.cellWidget(r, 1).currentData()})
        nunca = [self.lista.item(i).text() for i in range(self.lista.count()) if self.lista.item(i).text().strip()]
        return Termos(sempre, nunca)


class DialogoTipos(QDialog):
    def __init__(self, ativos: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tipos de dados a procurar")
        grade = QGridLayout()
        self.caixas: dict[str, QCheckBox] = {}
        tipos = [t for t in TIPOS if t != "TERMO"]
        for i, t in enumerate(tipos):
            cb = QCheckBox(descricao(t))
            cb.setChecked(t in ativos)
            self.caixas[t] = cb
            grade.addWidget(cb, i % 11, i // 11)
        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Desmarque o que não precisa ser anonimizado. Ex.: número do processo "
                                "e CNPJ de empresas costumam ser dados públicos."))
        layout.addLayout(grade)
        layout.addWidget(botoes)

    def resultado(self) -> list[str]:
        return [t for t, cb in self.caixas.items() if cb.isChecked()]


class DialogoNovoTermo(QDialog):
    def __init__(self, parent=None, termo: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Adicionar termo")
        self.termo = QLineEdit(termo)
        self.tipo = combo_tipos("PESSOA")
        self.salvar = QCheckBox("Guardar também na minha lista (sempre anonimizar)")
        form = QFormLayout()
        form.addRow("Texto exato:", self.termo)
        form.addRow("Tipo:", self.tipo)
        form.addRow(self.salvar)
        botoes = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("O termo será procurado em todos os arquivos (sem diferenciar "
                                "maiúsculas e acentos)."))
        layout.addLayout(form)
        layout.addWidget(botoes)
        self.termo.setFocus(Qt.FocusReason.OtherFocusReason)
