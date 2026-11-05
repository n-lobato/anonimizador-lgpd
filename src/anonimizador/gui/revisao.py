"""Tela de revisão: o usuário confere tudo o que foi detectado antes de gravar."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..config import salvar_termos
from ..deteccao.modelo import descricao
from ..registro import GLOBAL
from ..texto import Localizador
from .dialogos import DialogoNovoTermo, aceito

COL_MARCA, COL_CODIGO, COL_TIPO, COL_TEXTO, COL_OCORR, COL_CONF, COL_ORIGEM, COL_ARQ = range(8)
ID = Qt.ItemDataRole.UserRole
ORDEM = getattr(ID, "value", ID) + 1  # papel extra para ordenar números


class ItemNumero(QTableWidgetItem):
    def __lt__(self, outro):
        try:
            return float(self.data(ORDEM)) < float(outro.data(ORDEM))
        except (TypeError, ValueError):
            return super().__lt__(outro)


class DialogoRevisao(QDialog):
    def __init__(self, sessao, parent=None):
        super().__init__(parent)
        self.sessao = sessao
        self.registro = sessao.registro
        self.setWindowTitle("Revisar antes de anonimizar")
        self.resize(1150, 700)

        n_arq = sum(1 for a in sessao.arquivos if not a.erro)
        self.resumo = QLabel()
        self.resumo.setWordWrap(True)

        self.filtro_tipo = QComboBox()
        self.filtro_tipo.addItem("Todos os tipos", "")
        for t in sorted({e.tipo for e in self.registro.entidades.values()}, key=descricao):
            self.filtro_tipo.addItem(descricao(t), t)
        self.busca = QLineEdit()
        self.busca.setPlaceholderText("Filtrar pelo texto...")
        self.filtro_tipo.currentIndexChanged.connect(self._filtrar)
        self.busca.textChanged.connect(self._filtrar)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(["Anonimizar", "Código", "Tipo", "Texto encontrado",
                                               "Ocorrências", "Confiança", "Origem", "Arquivo"])
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        cab = self.tabela.horizontalHeader()
        cab.setSectionResizeMode(COL_TEXTO, QHeaderView.ResizeMode.Stretch)
        for c in (COL_MARCA, COL_CODIGO, COL_TIPO, COL_OCORR, COL_CONF):
            cab.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.setColumnHidden(COL_ARQ, self.registro.por_arquivo is False)
        self.tabela.itemChanged.connect(self._marcacao_mudou)
        self.tabela.itemSelectionChanged.connect(self._mostrar_contexto)

        self.contexto = QPlainTextEdit()
        self.contexto.setReadOnly(True)
        self.contexto.setPlaceholderText("Selecione uma linha para ver onde o dado aparece.")

        botoes_tabela = QHBoxLayout()
        for rotulo, acao, dica in [
            ("Marcar visíveis", lambda: self._marcar(True), ""),
            ("Desmarcar visíveis", lambda: self._marcar(False), ""),
            ("Unir selecionados", self._unir,
             "Junta linhas que são a mesma pessoa (ou o mesmo dado) em um único código."),
            ("Adicionar termo...", self._adicionar, "Inclui algo que o programa não detectou."),
            ("Nunca anonimizar", self._nunca,
             "Desmarca e guarda na sua lista para não sugerir de novo."),
            ("Sempre anonimizar", self._sempre, "Guarda na sua lista para detectar nas próximas vezes."),
        ]:
            b = QPushButton(rotulo)
            b.setToolTip(dica)
            b.clicked.connect(acao)
            botoes_tabela.addWidget(b)
        botoes_tabela.addStretch()

        topo = QHBoxLayout()
        topo.addWidget(self.filtro_tipo)
        topo.addWidget(self.busca, 1)

        esquerda = QWidget()
        le = QVBoxLayout(esquerda)
        le.setContentsMargins(0, 0, 0, 0)
        le.addLayout(topo)
        le.addWidget(self.tabela)
        le.addLayout(botoes_tabela)
        direita = QWidget()
        ld = QVBoxLayout(direita)
        ld.setContentsMargins(0, 0, 0, 0)
        ld.addWidget(QLabel("<b>Onde aparece</b>"))
        ld.addWidget(self.contexto)
        divisor = QSplitter()
        divisor.addWidget(esquerda)
        divisor.addWidget(direita)
        divisor.setSizes([780, 370])

        self.ok = QPushButton("Anonimizar")
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.accept)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        rodape = QHBoxLayout()
        rodape.addWidget(QLabel(
            f"{n_arq} arquivo(s). Linhas em amarelo têm confiança menor: confira com atenção. "
            "Atenção: nomes não reconhecidos não aparecem aqui; use \"Adicionar termo\"."))
        rodape.addStretch()
        rodape.addWidget(cancelar)
        rodape.addWidget(self.ok)

        layout = QVBoxLayout(self)
        layout.addWidget(self.resumo)
        layout.addWidget(divisor, 1)
        layout.addLayout(rodape)
        self._preencher()

    # ----------------------------------------------------------------- tabela
    def _preencher(self) -> None:
        self.registro.numerar()
        self.tabela.blockSignals(True)
        self.tabela.setSortingEnabled(False)
        ents = self.registro.ordenadas()
        self.tabela.setRowCount(len(ents))
        for r, e in enumerate(ents):
            marca = QTableWidgetItem()
            marca.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            marca.setCheckState(Qt.CheckState.Checked if e.ativo else Qt.CheckState.Unchecked)
            marca.setData(ID, e.id)
            outras = [v for v in e.variantes.values() if v != e.rotulo]
            texto = QTableWidgetItem(e.rotulo)
            if outras:
                texto.setToolTip("Também aparece como:\n" + "\n".join(outras))
            ocorr = ItemNumero(str(e.total))
            ocorr.setData(ORDEM, e.total)
            conf = ItemNumero(f"{e.confianca:.0%}")
            conf.setData(ORDEM, e.confianca)
            arq = "" if e.escopo == GLOBAL else Path(e.escopo).name
            itens = [marca, QTableWidgetItem(e.codigo), QTableWidgetItem(descricao(e.tipo)), texto,
                     ocorr, conf, QTableWidgetItem(e.origem), QTableWidgetItem(arq)]
            for c, it in enumerate(itens):
                if c != COL_MARCA:
                    it.setData(ID, e.id)
                if e.confianca < 0.75:
                    it.setBackground(QColor(255, 244, 200))
                self.tabela.setItem(r, c, it)
        self.tabela.setSortingEnabled(True)
        self.tabela.blockSignals(False)
        self._filtrar()
        self._atualizar_resumo()

    def _atualizar_resumo(self) -> None:
        ents = list(self.registro.entidades.values())
        ativos = sum(1 for e in ents if e.ativo)
        ocorr = sum(e.total for e in ents if e.ativo)
        self.resumo.setText(
            f"<b>{len(ents)}</b> dado(s) pessoal(is) encontrado(s). <b>{ativos}</b> marcado(s) para "
            f"anonimizar ({ocorr} ocorrência(s)). Desmarque o que <b>não</b> deve ser substituído.")
        self.ok.setText(f"Anonimizar ({ativos})")

    def _filtrar(self) -> None:
        tipo = self.filtro_tipo.currentData()
        busca = self.busca.text().strip().lower()
        for r in range(self.tabela.rowCount()):
            e = self._entidade(r)
            if e is None:
                continue
            visivel = (not tipo or e.tipo == tipo) and (
                not busca or busca in e.rotulo.lower() or busca in e.codigo.lower())
            self.tabela.setRowHidden(r, not visivel)

    def _entidade(self, linha: int):
        it = self.tabela.item(linha, COL_MARCA)
        return self.registro.entidades.get(it.data(ID)) if it else None

    def _selecionadas(self):
        linhas = sorted({i.row() for i in self.tabela.selectedIndexes()})
        return [e for e in (self._entidade(r) for r in linhas) if e]

    def _marcacao_mudou(self, item: QTableWidgetItem) -> None:
        if item.column() != COL_MARCA:
            return
        e = self.registro.entidades.get(item.data(ID))
        if e:
            e.ativo = item.checkState() == Qt.CheckState.Checked
            self._atualizar_resumo()

    def _marcar(self, valor: bool) -> None:
        self.tabela.blockSignals(True)
        for r in range(self.tabela.rowCount()):
            if self.tabela.isRowHidden(r):
                continue
            e = self._entidade(r)
            if e:
                e.ativo = valor
                self.tabela.item(r, COL_MARCA).setCheckState(
                    Qt.CheckState.Checked if valor else Qt.CheckState.Unchecked)
        self.tabela.blockSignals(False)
        self._atualizar_resumo()

    def _mostrar_contexto(self) -> None:
        sel = self._selecionadas()
        if not sel:
            self.contexto.clear()
            return
        e = sel[0]
        linhas = [f"{e.codigo}  ({descricao(e.tipo)})", ""]
        if len(e.variantes) > 1:
            linhas.append("Formas: " + "; ".join(e.variantes.values()))
            linhas.append("")
        for arq, trecho in self.registro.contextos(e, self.sessao.textos, limite=8):
            linhas.append(f"[{Path(arq).name}]")
            linhas.append(trecho)
            linhas.append("")
        self.contexto.setPlainText("\n".join(linhas))

    # ----------------------------------------------------------------- ações
    def _unir(self) -> None:
        sel = self._selecionadas()
        if len(sel) < 2:
            QMessageBox.information(self, "Unir", "Selecione duas ou mais linhas (Ctrl+clique).")
            return
        if len({e.escopo for e in sel}) > 1:
            QMessageBox.warning(self, "Unir", "Só é possível unir dados do mesmo arquivo.")
            return
        sel.sort(key=lambda e: (-len(e.rotulo), e.ordem))
        for e in sel:
            e.pai = None
        self.registro.unir([e.id for e in sel])
        self.registro.recontar(self.sessao.textos)
        self._preencher()

    def _adicionar(self) -> None:
        dlg = DialogoNovoTermo(self)
        if not aceito(dlg.exec()):
            return
        termo = dlg.termo.text().strip()
        tipo = dlg.tipo.currentData()
        if not termo:
            return
        loc = Localizador({termo: 1})
        arquivos = [a for a, t in self.sessao.textos.items() if loc.encontrar(t)]
        if not arquivos:
            QMessageBox.information(self, "Adicionar termo", f"\"{termo}\" não aparece nos arquivos analisados.")
            return
        for arq in arquivos if self.registro.por_arquivo else [None]:
            ent = self.registro.adicionar_manual(termo, tipo, arq)
            ent.ativo = True
        if dlg.salvar.isChecked():
            self.sessao.termos.sempre.append({"termo": termo, "tipo": tipo})
            salvar_termos(self.sessao.termos)
        self.registro.recontar(self.sessao.textos)
        self._preencher()

    def _nunca(self) -> None:
        sel = self._selecionadas()
        if not sel:
            return
        for e in sel:
            e.ativo = False
            if e.rotulo not in self.sessao.termos.nunca:
                self.sessao.termos.nunca.append(e.rotulo)
        salvar_termos(self.sessao.termos)
        self._preencher()

    def _sempre(self) -> None:
        sel = self._selecionadas()
        existentes = {d.get("termo", "").lower() for d in self.sessao.termos.sempre}
        novos = 0
        for e in sel:
            e.ativo = True
            if e.rotulo.lower() not in existentes:
                self.sessao.termos.sempre.append({"termo": e.rotulo, "tipo": e.tipo})
                novos += 1
        if novos:
            salvar_termos(self.sessao.termos)
            QMessageBox.information(self, "Sempre anonimizar", f"{novos} termo(s) guardado(s) na sua lista.")
        self._preencher()
