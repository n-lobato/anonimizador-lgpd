"""Arquivos de texto puro (TXT, MD, CSV, legendas de transcrição)."""

from __future__ import annotations

from . import ErroFormato, Extraido, Opcoes

CODIFICACOES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def _ler(caminho: str) -> tuple[str, str]:
    with open(caminho, "rb") as fh:
        dados = fh.read()
    for cod in CODIFICACOES:
        try:
            return dados.decode(cod), cod
        except UnicodeDecodeError:
            continue
    raise ErroFormato("codificação de texto não reconhecida.")


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    texto, cod = _ler(caminho)
    return Extraido(texto, [], cod)


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    texto, cod = _ler(caminho)
    with open(saida, "w", encoding=cod, newline="") as fh:
        fh.write(substituidor.substituir(texto))
    return []
