import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def test_janela_e_revisao_abrem(tmp_path, peticao):
    from PySide6.QtWidgets import QApplication

    from anonimizador.config import Configuracao, Termos
    from anonimizador.gui.dialogos import DialogoTermos, DialogoTipos
    from anonimizador.gui.janela import JanelaPrincipal
    from anonimizador.gui.revisao import DialogoRevisao
    from anonimizador.processador import Sessao

    app = QApplication.instance() or QApplication([])
    f = tmp_path / "p.txt"
    f.write_text(peticao, encoding="utf-8")
    j = JanelaPrincipal([str(f)])
    assert j.lista.count() == 1
    s = Sessao(Configuracao(), Termos())
    s.carregar([f])
    s.analisar()
    d = DialogoRevisao(s)
    assert d.tabela.rowCount() == len(s.registro.entidades)
    d._marcar(False)
    assert not any(e.ativo for e in s.registro.entidades.values())
    d.tabela.selectRow(0)
    d._mostrar_contexto()
    assert d.contexto.toPlainText()
    DialogoTermos(Termos([{"termo": "Zeca", "tipo": "PESSOA"}], ["Tribunal"])).resultado()
    DialogoTipos(["CPF"]).resultado()
    j.close()
    app.processEvents()
