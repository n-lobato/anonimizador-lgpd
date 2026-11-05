"""Planilhas Excel (.xlsx)."""

from __future__ import annotations

import zipfile

from . import ErroFormato, Extraido, Opcoes


def _abrir(caminho: str):
    try:
        import openpyxl
        keep_vba = caminho.lower().endswith(".xlsm")
        return openpyxl.load_workbook(caminho, keep_vba=keep_vba)
    except Exception as e:
        raise ErroFormato(f"não foi possível abrir a planilha ({e}).") from e


def _celulas_texto(wb):
    for ws in wb.worksheets:
        for linha in ws.iter_rows():
            for cel in linha:
                if isinstance(cel.value, str) and not cel.value.startswith("="):
                    yield cel


def _avisos_estrutura(caminho: str) -> list[str]:
    try:
        with zipfile.ZipFile(caminho) as z:
            nomes = z.namelist()
    except zipfile.BadZipFile:
        return []
    avisos = []
    if any(n.startswith("xl/drawings/") for n in nomes) or any(n.startswith("xl/charts/") for n in nomes):
        avisos.append("A planilha tem gráficos, imagens ou formas: eles podem não ser preservados na cópia "
                      "anonimizada e não foram analisados.")
    return avisos


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    wb = _abrir(caminho)
    partes = [c.value for c in _celulas_texto(wb)]
    for ws in wb.worksheets:
        partes.append(ws.title)
        for linha in ws.iter_rows():
            for cel in linha:
                if cel.comment is not None:
                    partes.append(cel.comment.text or "")
    return Extraido("\n".join(partes), _avisos_estrutura(caminho))


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    wb = _abrir(caminho)
    for cel in _celulas_texto(wb):
        novo = substituidor.substituir(cel.value)
        if novo != cel.value:
            cel.value = novo
    for ws in wb.worksheets:
        novo_titulo = substituidor.substituir(ws.title)[:31]
        if novo_titulo != ws.title:
            ws.title = novo_titulo.replace("[", "(").replace("]", ")")
        for linha in ws.iter_rows():
            for cel in linha:
                if cel.comment is not None:
                    from openpyxl.comments import Comment
                    cel.comment = Comment(substituidor.substituir(cel.comment.text or ""), "Anonimizado")
    p = wb.properties
    p.creator = None
    p.lastModifiedBy = None
    for attr in ("title", "subject", "description", "keywords", "category"):
        valor = getattr(p, attr, None)
        if isinstance(valor, str):
            setattr(p, attr, substituidor.substituir(valor))
    wb.save(saida)
    return _avisos_estrutura(caminho)
