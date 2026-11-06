"""Garante que a detecção não piore no corpus de avaliação (tests/corpus)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "build"))
import avaliar  # noqa: E402


@pytest.mark.parametrize("grupo", ["desenvolvimento", "validacao"])
def test_nenhum_dado_marcado_vaza(grupo):
    resultados, falsos = avaliar.avaliar_grupo(grupo)
    assert resultados, "corpus vazio"
    vazados = [f"{r.arquivo}: {r.marcado.tipo} '{r.marcado.texto}' -> '{r.legivel}'"
               for r in resultados if r.status != "coberto"]
    assert not vazados, "\n".join(vazados)


def test_poucos_falsos_positivos():
    falsos = []
    for grupo in ("desenvolvimento", "validacao"):
        falsos += avaliar.avaliar_grupo(grupo)[1]
    # hoje: 1 ("Avenida Pau-Brasil", rua sem número tratada como endereço de propósito)
    assert len(falsos) <= 2, falsos


def test_marcacao_do_corpus():
    texto, marcados = avaliar.ler_marcado("A [[PESSOA|Ana Lima]], CPF [[?CPF|1]].")
    assert texto == "A Ana Lima, CPF 1."
    assert [(m.texto, m.opcional) for m in marcados] == [("Ana Lima", False), ("1", True)]
