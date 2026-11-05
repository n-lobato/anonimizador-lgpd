"""Janela principal: arrastar e soltar, opções, progresso."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QDialog,
                               QFileDialog, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QRadioButton, QStyle, QVBoxLayout, QWidget)

from .. import AUTOR, NOME_APP, __version__
from ..config import carregar_config, carregar_termos, pasta_config, salvar_config, salvar_termos
from ..formatos import EXTENSOES
from ..formatos.ocr import ocr_disponivel, pasta_do_programa
from ..processador import Sessao
from ..relatorio import gerar
from .dialogos import DialogoTermos, DialogoTipos, aceito
from .revisao import DialogoRevisao
from .trabalhos import Trabalho

ESTILO_ZONA = """
QFrame#zona { border: 2px dashed #7a8ca8; border-radius: 10px; background: #f3f6fb; }
QFrame#zona[ativa="true"] { border-color: #1f5fbf; background: #e2ecfb; }
QLabel#zonaTitulo { font-size: 16px; font-weight: 600; color: #1f3864; }
QLabel#zonaSub { color: #4a5a75; }
"""


def abrir_no_sistema(caminho: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(caminho)])
        else:
            subprocess.Popen(["xdg-open", str(caminho)])
    except Exception:
        pass


class ZonaSoltar(QFrame):
    def __init__(self, ao_clicar, parent=None):
        super().__init__(parent)
        self.setObjectName("zona")
        self.setMinimumHeight(130)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ao_clicar = ao_clicar
        t = QLabel("Arraste aqui arquivos ou pastas")
        t.setObjectName("zonaTitulo")
        s = QLabel("Word (.docx), PDF (inclusive digitalizado), imagens, texto e Excel (.xlsx)\n"
                   "ou clique para escolher arquivos")
        s.setObjectName("zonaSub")
        for w in (t, s):
            w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay = QVBoxLayout(self)
        lay.addStretch()
        lay.addWidget(t)
        lay.addWidget(s)
        lay.addStretch()

    def destacar(self, ativa: bool) -> None:
        self.setProperty("ativa", "true" if ativa else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, ev):
        self._ao_clicar()


class JanelaPrincipal(QMainWindow):
    def __init__(self, entradas_iniciais: list[str] | None = None):
        super().__init__()
        self.cfg = carregar_config()
        self.termos = carregar_termos()
        self.trabalho: Trabalho | None = None
        self.sessao: Sessao | None = None
        self.setWindowTitle(f"{NOME_APP} {__version__}")
        self.resize(820, 720)
        self.setAcceptDrops(True)
        icone = pasta_do_programa() / "assets" / "icone.ico"
        if icone.exists():
            self.setWindowIcon(QIcon(str(icone)))
        self._montar_menu()
        self._montar_tela()
        self.setStyleSheet(ESTILO_ZONA)
        if entradas_iniciais:
            self.adicionar(entradas_iniciais)

    # ------------------------------------------------------------------ tela
    def _montar_menu(self) -> None:
        m = self.menuBar()
        arq = m.addMenu("&Arquivo")
        for rotulo, acao in [("Adicionar arquivos...", self._escolher_arquivos),
                             ("Adicionar pasta...", self._escolher_pasta), (None, None),
                             ("Sair", self.close)]:
            if rotulo is None:
                arq.addSeparator()
                continue
            a = QAction(rotulo, self)
            a.triggered.connect(acao)
            arq.addAction(a)
        fer = m.addMenu("&Ferramentas")
        for rotulo, acao in [("Minha lista de termos...", self._editar_termos),
                             ("Tipos de dados a procurar...", self._editar_tipos),
                             ("Adicionar ao menu \"Enviar para\" do Windows", self._enviar_para),
                             ("Verificar OCR", self._verificar_ocr),
                             ("Abrir pasta de configurações", lambda: abrir_no_sistema(pasta_config()))]:
            a = QAction(rotulo, self)
            a.triggered.connect(acao)
            fer.addAction(a)
        aj = m.addMenu("Aj&uda")
        a = QAction("Sobre", self)
        a.triggered.connect(self._sobre)
        aj.addAction(a)

    def _montar_tela(self) -> None:
        central = QWidget()
        lay = QVBoxLayout(central)

        self.zona = ZonaSoltar(self._escolher_arquivos)
        lay.addWidget(self.zona)

        self.lista = QListWidget()
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lista.setMinimumHeight(120)
        lay.addWidget(QLabel("Itens a processar:"))
        lay.addWidget(self.lista, 1)
        bl = QHBoxLayout()
        for rotulo, acao in [("Adicionar arquivos", self._escolher_arquivos),
                             ("Adicionar pasta", self._escolher_pasta),
                             ("Remover selecionados", self._remover),
                             ("Limpar lista", self.lista.clear)]:
            b = QPushButton(rotulo)
            b.clicked.connect(acao)
            bl.addWidget(b)
        bl.addStretch()
        lay.addLayout(bl)

        opcoes = QGroupBox("Opções")
        lo = QVBoxLayout(opcoes)
        self.cb_revisar = QCheckBox("Revisar o que foi encontrado antes de salvar (recomendado)")
        self.cb_ocr = QCheckBox("Usar OCR em PDFs digitalizados e imagens")
        self.cb_forcar = QCheckBox("Usar OCR também em páginas que já têm texto (mais lento)")
        self.cb_global = QCheckBox("Mesmo código para a mesma pessoa em todos os arquivos do lote")
        self.cb_relatorio = QCheckBox("Gerar relatório com a tabela de-para (arquivo sensível)")
        self.cb_sub = QCheckBox("Incluir subpastas")
        for cb in (self.cb_revisar, self.cb_ocr, self.cb_forcar, self.cb_global, self.cb_relatorio, self.cb_sub):
            lo.addWidget(cb)
        self.cb_ocr.toggled.connect(self.cb_forcar.setEnabled)

        destino = QHBoxLayout()
        self.rb_lado = QRadioButton("Salvar na subpasta \"anonimizados\" ao lado do original")
        self.rb_pasta = QRadioButton("Salvar em:")
        grupo = QButtonGroup(self)
        grupo.addButton(self.rb_lado)
        grupo.addButton(self.rb_pasta)
        self.ed_pasta = QLineEdit()
        b_pasta = QPushButton("...")
        b_pasta.setFixedWidth(32)
        b_pasta.clicked.connect(self._escolher_destino)
        lo.addWidget(self.rb_lado)
        destino.addWidget(self.rb_pasta)
        destino.addWidget(self.ed_pasta, 1)
        destino.addWidget(b_pasta)
        lo.addLayout(destino)
        lay.addWidget(opcoes)

        self.botao = QPushButton("Anonimizar")
        self.botao.setMinimumHeight(40)
        self.botao.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.botao.clicked.connect(self.iniciar)
        self.progresso = QProgressBar()
        self.progresso.setTextVisible(True)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(140)
        self.log.setAcceptDrops(False)
        lay.addWidget(self.botao)
        lay.addWidget(self.progresso)
        lay.addWidget(self.log)
        self.setCentralWidget(central)
        self._carregar_opcoes()

    def _carregar_opcoes(self) -> None:
        c = self.cfg
        self.cb_revisar.setChecked(c.revisar)
        self.cb_ocr.setChecked(c.ocr)
        self.cb_forcar.setChecked(c.forcar_ocr)
        self.cb_forcar.setEnabled(c.ocr)
        self.cb_global.setChecked(c.codigos_globais)
        self.cb_relatorio.setChecked(c.gerar_relatorio)
        self.cb_sub.setChecked(c.incluir_subpastas)
        self.ed_pasta.setText(c.pasta_saida)
        (self.rb_pasta if c.pasta_saida else self.rb_lado).setChecked(True)

    def _ler_opcoes(self) -> None:
        c = self.cfg
        c.revisar = self.cb_revisar.isChecked()
        c.ocr = self.cb_ocr.isChecked()
        c.forcar_ocr = self.cb_forcar.isChecked()
        c.codigos_globais = self.cb_global.isChecked()
        c.gerar_relatorio = self.cb_relatorio.isChecked()
        c.incluir_subpastas = self.cb_sub.isChecked()
        c.pasta_saida = self.ed_pasta.text().strip() if self.rb_pasta.isChecked() else ""
        salvar_config(c)

    # ------------------------------------------------------- arrastar e soltar
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()
            self.zona.destacar(True)

    def dragLeaveEvent(self, ev):
        self.zona.destacar(False)

    def dropEvent(self, ev):
        self.zona.destacar(False)
        caminhos = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        self.adicionar(caminhos)
        ev.acceptProposedAction()

    def adicionar(self, caminhos: list[str]) -> None:
        existentes = {self.lista.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.lista.count())}
        estilo = self.style()
        for c in caminhos:
            p = Path(c)
            if not p.exists() or str(p) in existentes:
                continue
            icone = estilo.standardIcon(QStyle.StandardPixmap.SP_DirIcon if p.is_dir()
                                        else QStyle.StandardPixmap.SP_FileIcon)
            item = QListWidgetItem(icone, str(p))
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.lista.addItem(item)

    def _entradas(self) -> list[str]:
        return [self.lista.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.lista.count())]

    def _escolher_arquivos(self) -> None:
        filtro = "Documentos (" + " ".join(f"*{e}" for e in EXTENSOES) + ");;Todos (*.*)"
        arquivos, _ = QFileDialog.getOpenFileNames(self, "Escolher arquivos", "", filtro)
        self.adicionar(arquivos)

    def _escolher_pasta(self) -> None:
        pasta = QFileDialog.getExistingDirectory(self, "Escolher pasta")
        if pasta:
            self.adicionar([pasta])

    def _escolher_destino(self) -> None:
        pasta = QFileDialog.getExistingDirectory(self, "Pasta de saída")
        if pasta:
            self.ed_pasta.setText(pasta)
            self.rb_pasta.setChecked(True)

    def _remover(self) -> None:
        for item in self.lista.selectedItems():
            self.lista.takeItem(self.lista.row(item))

    # ----------------------------------------------------------------- fluxo
    def _escrever(self, msg: str) -> None:
        self.log.appendPlainText(msg)

    def _ocupado(self, sim: bool) -> None:
        self.botao.setEnabled(not sim)
        self.lista.setEnabled(not sim)
        self.setAcceptDrops(not sim)

    def _progresso(self, i: int, total: int, msg: str) -> None:
        self.progresso.setMaximum(max(total, 1))
        self.progresso.setValue(i)
        self.progresso.setFormat(f"{msg}  (%v/%m)")

    def _rodar(self, funcao, ao_terminar) -> None:
        self.trabalho = Trabalho(funcao, self)
        self.trabalho.progresso.connect(self._progresso)
        self.trabalho.concluido.connect(ao_terminar)
        self.trabalho.falhou.connect(self._falhou)
        self._ocupado(True)
        self.trabalho.start()

    def _falhou(self, detalhe: str) -> None:
        self._ocupado(False)
        self._escrever(detalhe)
        QMessageBox.critical(self, "Erro", "Ocorreu um erro inesperado. Detalhes no registro abaixo.")

    def iniciar(self) -> None:
        entradas = self._entradas()
        if not entradas:
            QMessageBox.information(self, NOME_APP, "Arraste arquivos ou pastas para a janela primeiro.")
            return
        self._ler_opcoes()
        self.termos = carregar_termos()
        if self.cfg.ocr and not ocr_disponivel(self.cfg.idioma_ocr)[0]:
            self._escrever("Aviso: " + ocr_disponivel(self.cfg.idioma_ocr)[1])
        self.sessao = Sessao(self.cfg, self.termos)
        self.sessao.carregar(entradas)
        self.log.clear()
        for msg in self.sessao.ignorados:
            self._escrever(f"Ignorado: {msg}")
        if not self.sessao.arquivos:
            QMessageBox.information(self, NOME_APP, "Nenhum arquivo suportado foi encontrado.")
            return
        self._escrever(f"{len(self.sessao.arquivos)} arquivo(s) na fila.")
        self._rodar(self.sessao.analisar, self._analise_concluida)

    def _analise_concluida(self) -> None:
        self._ocupado(False)
        s = self.sessao
        for a in s.arquivos:
            if a.erro:
                self._escrever(f"Erro em {a.caminho.name}: {a.erro}")
        if not s.registro.entidades:
            QMessageBox.information(self, NOME_APP, "Nenhum dado pessoal foi detectado. Se houver nomes não "
                                    "reconhecidos, cadastre-os em Ferramentas > Minha lista de termos.")
            if not self.cfg.revisar:
                return
        if self.cfg.revisar:
            dlg = DialogoRevisao(s, self)
            if not aceito(dlg.exec()):
                self._escrever("Cancelado na revisão. Nenhum arquivo foi gravado.")
                return
        self._rodar(s.aplicar, self._aplicacao_concluida)

    def _aplicacao_concluida(self) -> None:
        self._ocupado(False)
        s = self.sessao
        ok = [a for a in s.arquivos if a.saida]
        for a in s.arquivos:
            if a.saida:
                self._escrever(f"OK: {a.saida}")
            if a.erro:
                self._escrever(f"Erro em {a.caminho.name}: {a.erro}")
            for av in a.avisos:
                self._escrever(f"   Aviso ({a.caminho.name}): {av}")
        relatorio = None
        if self.cfg.gerar_relatorio and ok:
            pasta = s.pasta_relatorio()
            if pasta:
                relatorio = gerar(s, pasta)
                self._escrever(f"Relatório (guarde em local seguro): {relatorio}")
        erros = sum(1 for a in s.arquivos if a.erro)
        avisos = sum(len(a.avisos) for a in s.arquivos)
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Concluído")
        caixa.setText(f"{len(ok)} arquivo(s) anonimizado(s)." + (f" {erros} com erro." if erros else "")
                      + (f"\n{avisos} aviso(s): veja o registro na janela." if avisos else ""))
        caixa.setInformativeText("Confira os arquivos gerados antes de compartilhá-los.")
        abrir = caixa.addButton("Abrir pasta", QMessageBox.ButtonRole.AcceptRole) if ok else None
        caixa.addButton("Fechar", QMessageBox.ButtonRole.RejectRole)
        caixa.exec()
        if abrir is not None and caixa.clickedButton() is abrir:
            abrir_no_sistema(s.pasta_relatorio() or ok[0].saida.parent)

    # --------------------------------------------------------------- menus
    def _editar_termos(self) -> None:
        dlg = DialogoTermos(carregar_termos(), self)
        if aceito(dlg.exec()):
            self.termos = dlg.resultado()
            salvar_termos(self.termos)

    def _editar_tipos(self) -> None:
        dlg = DialogoTipos(self.cfg.tipos, self)
        if aceito(dlg.exec()):
            self.cfg.tipos = dlg.resultado()
            salvar_config(self.cfg)

    def _verificar_ocr(self) -> None:
        ok, msg = ocr_disponivel(self.cfg.idioma_ocr)
        (QMessageBox.information if ok else QMessageBox.warning)(self, "OCR", msg)

    def _enviar_para(self) -> None:
        if not sys.platform.startswith("win"):
            QMessageBox.information(self, "Enviar para", "Disponível apenas no Windows.")
            return
        if not getattr(sys, "frozen", False):
            QMessageBox.information(self, "Enviar para", "Disponível na versão executável (.exe).")
            return
        destino = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "SendTo" / f"{NOME_APP}.lnk"
        alvo = sys.executable
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{destino}');"
              f"$s.TargetPath='{alvo}';$s.WorkingDirectory='{Path(alvo).parent}';"
              f"$s.IconLocation='{alvo},0';$s.Save()")
        try:
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            QMessageBox.information(self, "Enviar para", "Pronto. Clique com o botão direito em arquivos ou "
                                    f"pastas > Enviar para > {NOME_APP}.")
        except Exception as e:
            QMessageBox.warning(self, "Enviar para", f"Não foi possível criar o atalho: {e}")

    def _sobre(self) -> None:
        QMessageBox.about(self, "Sobre", (
            f"<b>{NOME_APP} {__version__}</b><br>Autor: {AUTOR}<br><br>"
            "Anonimiza dados pessoais em documentos, 100% no seu computador: nenhum arquivo é "
            "enviado para a internet.<br><br>A detecção automática não é infalível. Revise sempre o "
            "resultado antes de compartilhar.<br><br>Licença GPL-3.0. "
            "<a href='https://github.com/n-lobato/anonimizador-lgpd'>github.com/n-lobato/anonimizador-lgpd</a>"))

    def closeEvent(self, ev):
        if self.trabalho and self.trabalho.isRunning():
            self.trabalho.cancelar()
            self.trabalho.wait(3000)
        try:
            self._ler_opcoes()
        except Exception:
            pass
        ev.accept()


def executar(argv: list[str]) -> int:
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(NOME_APP)
    app.setStyle("Fusion")
    janela = JanelaPrincipal([a for a in argv if not a.startswith("-")])
    janela.show()
    return app.exec()
