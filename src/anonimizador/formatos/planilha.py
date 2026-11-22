"""Planilhas Excel (.xlsx)."""

from __future__ import annotations

import re
import zipfile

from . import ErroFormato, Extraido, Opcoes

# texto entre aspas dentro de uma fórmula; no Excel, aspas dentro do texto são escritas como ""
LITERAL = re.compile(r'"((?:[^"]|"")*)"')
CABECALHOS = ("oddHeader", "oddFooter", "evenHeader", "evenFooter", "firstHeader", "firstFooter")


def _abrir(caminho: str):
    try:
        import openpyxl
        keep_vba = caminho.lower().endswith(".xlsm")
        return openpyxl.load_workbook(caminho, keep_vba=keep_vba)
    except Exception as e:
        raise ErroFormato(f"não foi possível abrir a planilha ({e}).") from e


def _formula(valor) -> str | None:
    """Texto da fórmula da célula (normal ou matricial), ou None se não for fórmula."""
    if isinstance(valor, str):
        return valor if valor.startswith("=") else None
    texto = getattr(valor, "text", None)  # ArrayFormula
    return texto if isinstance(texto, str) else None


def literais(formula: str) -> list[str]:
    return [m.group(1).replace('""', '"') for m in LITERAL.finditer(formula)]


def substituir_formula(formula: str, substituidor) -> str:
    """Anonimiza só os textos entre aspas; referências e funções ficam como estão."""
    def troca(m):
        original = m.group(1).replace('""', '"')
        novo = substituidor.substituir(original)
        return '"' + novo.replace('"', '""') + '"' if novo != original else m.group(0)
    return LITERAL.sub(troca, formula)


def _celulas(wb):
    for ws in wb.worksheets:
        for linha in ws.iter_rows():
            yield from linha


def _partes_cabecalho(ws):
    for nome in CABECALHOS:
        hf = getattr(ws, nome, None)
        for lado in ("left", "center", "right"):
            parte = getattr(hf, lado, None) if hf is not None else None
            if parte is not None and isinstance(getattr(parte, "text", None), str) and parte.text:
                yield parte


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
    if any(n.startswith("xl/externalLinks/") for n in nomes):
        avisos.append("A planilha tem vínculos com outros arquivos: os caminhos e valores guardados desses "
                      "vínculos não foram analisados.")
    if any(n.startswith("xl/pivotCache/") for n in nomes):
        avisos.append("A planilha tem tabelas dinâmicas: os dados guardados no cache delas não foram "
                      "analisados e podem conter os valores originais.")
    return avisos


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    wb = _abrir(caminho)
    partes: list[str] = []
    for cel in _celulas(wb):
        f = _formula(cel.value)
        if f is not None:
            partes.extend(literais(f))
        elif isinstance(cel.value, str):
            partes.append(cel.value)
        if cel.comment is not None:
            partes.append(cel.comment.text or "")
        if cel.hyperlink is not None:
            for attr in ("target", "display", "tooltip", "location"):
                v = getattr(cel.hyperlink, attr, None)
                if isinstance(v, str):
                    partes.append(v)
    for ws in wb.worksheets:
        partes.append(ws.title)
        partes.extend(p.text for p in _partes_cabecalho(ws))
    return Extraido("\n".join(partes), _avisos_estrutura(caminho))


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    wb = _abrir(caminho)
    for cel in _celulas(wb):
        f = _formula(cel.value)
        if f is not None:
            nova = substituir_formula(f, substituidor)
            if nova != f:
                if isinstance(cel.value, str):
                    cel.value = nova
                else:
                    cel.value.text = nova
        elif isinstance(cel.value, str):
            novo = substituidor.substituir(cel.value)
            if novo != cel.value:
                cel.value = novo
        if cel.comment is not None:
            from openpyxl.comments import Comment
            cel.comment = Comment(substituidor.substituir(cel.comment.text or ""), "Anonimizado")
        if cel.hyperlink is not None:
            for attr in ("target", "display", "tooltip", "location"):
                v = getattr(cel.hyperlink, attr, None)
                if isinstance(v, str) and v:
                    setattr(cel.hyperlink, attr, substituidor.substituir(v))
    for ws in wb.worksheets:
        novo_titulo = substituidor.substituir(ws.title)[:31]
        if novo_titulo != ws.title:
            ws.title = novo_titulo.replace("[", "(").replace("]", ")")
        for parte in _partes_cabecalho(ws):
            parte.text = substituidor.substituir(parte.text)
    p = wb.properties
    p.creator = None
    p.lastModifiedBy = None
    for attr in ("title", "subject", "description", "keywords", "category"):
        valor = getattr(p, attr, None)
        if isinstance(valor, str):
            setattr(p, attr, substituidor.substituir(valor))
    wb.save(saida)
    return _avisos_estrutura(caminho)
