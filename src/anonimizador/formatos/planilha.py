"""Planilhas Excel (.xlsx e .xlsm).

A cópia anonimizada sai sem o que guarda dados fora das células: vínculos com
outras planilhas (as fórmulas que dependiam deles viram o valor salvo), caches
de tabelas dinâmicas (a tabela vira valores fixos), objetos incorporados e
macros (.xlsm vira .xlsx).
"""

from __future__ import annotations

import io
import re
import zipfile

from . import ErroFormato, Extraido, Opcoes, imagens_office

# texto entre aspas dentro de uma fórmula; no Excel, aspas dentro do texto são escritas como ""
LITERAL = re.compile(r'"((?:[^"]|"")*)"')
# referência a outra pasta de trabalho dentro de uma fórmula, ex.: [1]Plan1!A1
EXTERNO = re.compile(r"\[\d+\]")
PROIBIDOS_NA_COPIA = ("xl/vbaProject.bin", "xl/externalLinks/", "xl/pivotCache/", "xl/pivotTables/",
                      "xl/embeddings/")
CABECALHOS = ("oddHeader", "oddFooter", "evenHeader", "evenFooter", "firstHeader", "firstFooter")


def _abrir(caminho: str, valores: bool = False):
    """Abre sem macros e sem vínculos externos; com valores=True, traz os valores salvos
    no lugar das fórmulas (usado para as fórmulas que dependiam de vínculos)."""
    try:
        import openpyxl
        return openpyxl.load_workbook(caminho, keep_vba=False, keep_links=False, data_only=valores)
    except Exception as e:
        raise ErroFormato(f"não foi possível abrir a planilha ({e}).") from e


def _estrutura(caminho: str) -> dict[str, bool]:
    try:
        with zipfile.ZipFile(caminho) as z:
            nomes = z.namelist()
    except zipfile.BadZipFile:
        nomes = []
    def tem(prefixo):
        return any(n.startswith(prefixo) for n in nomes)
    return {"macros": "xl/vbaProject.bin" in nomes, "vinculos": tem("xl/externalLinks/"),
            "dinamicas": tem("xl/pivotCache/") or tem("xl/pivotTables/"), "objetos": tem("xl/embeddings/"),
            "desenhos": tem("xl/drawings/") or tem("xl/charts/")}


def _usa_vinculo(formula: str) -> bool:
    return bool(EXTERNO.search(LITERAL.sub('""', formula)))


def _valores_salvos(caminho: str) -> dict[tuple[str, str], object]:
    """Valor salvo de cada célula cuja fórmula depende de outra pasta de trabalho."""
    wb_f, wb_v = _abrir(caminho), _abrir(caminho, valores=True)
    saida = {}
    for ws in wb_f.worksheets:
        for linha in ws.iter_rows():
            for cel in linha:
                f = _formula(cel.value)
                if f is not None and _usa_vinculo(f):
                    saida[(ws.title, cel.coordinate)] = wb_v[ws.title][cel.coordinate].value
    return saida


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


def _imagens(wb) -> dict[str, tuple[object, bytes]]:
    """Imagens coladas nas abas: nome com extensão -> (objeto do openpyxl, conteúdo)."""
    saida = {}
    for ws in wb.worksheets:
        for i, img in enumerate(getattr(ws, "_images", [])):
            try:
                dados = img._data()
            except Exception:
                continue
            fmt = (getattr(img, "format", "") or "").lower()
            ext = {"jpeg": ".jpg", "jpg": ".jpg", "gif": ".gif"}.get(fmt, ".png")
            saida[f"{ws.title}/imagem{i + 1}{ext}"] = (img, dados)
    return saida


def _avisos_estrutura(caminho: str) -> list[str]:
    e = _estrutura(caminho)
    avisos = []
    if e["desenhos"]:
        avisos.append("A planilha tem gráficos ou formas: eles podem não ser preservados na cópia "
                      "anonimizada e os textos deles não foram analisados. Imagens coladas passam por OCR "
                      "(ou são removidas, se a opção estiver marcada).")
    if e["vinculos"]:
        avisos.append("A planilha tem vínculos com outros arquivos. Eles são removidos da cópia, e as "
                      "fórmulas que dependiam deles viram o valor salvo (também anonimizado).")
    if e["dinamicas"]:
        avisos.append("A planilha tem tabelas dinâmicas. Na cópia elas viram valores fixos: o cache com os "
                      "dados de origem é removido.")
    if e["objetos"]:
        avisos.append("A planilha tem objetos incorporados (outros arquivos colados nela). Eles são removidos "
                      "da cópia.")
    if e["macros"]:
        avisos.append("A planilha tem macros. Elas são removidas e a cópia é salva como .xlsx.")
    return avisos


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    wb = _abrir(caminho)
    partes: list[str] = []
    if _estrutura(caminho)["vinculos"]:
        partes.extend(str(v) for v in _valores_salvos(caminho).values() if isinstance(v, str))
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
    analise = None
    imagens = _imagens(wb)
    if imagens and not opcoes.remover_imagens:
        analise = imagens_office.analisar({n: d for n, (_, d) in imagens.items()}, opcoes)
        partes.append(analise.texto())
    return Extraido("\n".join(partes), _avisos_estrutura(caminho), analise)


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    estrutura = _estrutura(caminho)
    wb = _abrir(caminho)
    salvos = _valores_salvos(caminho) if estrutura["vinculos"] else {}
    for (aba, coord), valor in salvos.items():
        wb[aba][coord].value = substituidor.substituir(valor) if isinstance(valor, str) else valor
    for nome in [n for n, d in list(wb.defined_names.items()) if _usa_vinculo(str(d.value or ""))]:
        del wb.defined_names[nome]
    for ws in wb.worksheets:
        ws._pivots = []  # a tabela continua nas células, como valores; sai o cache com a origem
    avisos_imagens: list[str] = []
    imagens = _imagens(wb)
    if imagens and opcoes.remover_imagens:
        for ws in wb.worksheets:
            ws._images = []
        avisos_imagens.append(f"{len(imagens)} imagem(ns) removida(s) da cópia, como pedido nas opções.")
    elif imagens:
        analise = cache if isinstance(cache, imagens_office.Analise) \
            else imagens_office.analisar({n: d for n, (_, d) in imagens.items()}, opcoes)
        tarjadas = 0
        for nome, (img, dados) in imagens.items():
            novo, acao = imagens_office.tratar(nome, dados, analise, substituidor, opcoes)
            if acao:
                img.ref = io.BytesIO(novo)
            tarjadas += acao == "tarjada"
        avisos_imagens += imagens_office.aviso_resultado(analise, tarjadas)
        avisos_imagens += imagens_office.avisos_analise(analise)
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
    with zipfile.ZipFile(saida) as z:
        sobrou = [n for n in z.namelist() if n.startswith(PROIBIDOS_NA_COPIA)]
    if sobrou:  # nunca deve acontecer; se acontecer, não entrega o arquivo
        raise ErroFormato(f"não foi possível remover da cópia: {', '.join(sobrou)}")
    avisos = _avisos_estrutura(caminho) + avisos_imagens
    if salvos:
        avisos.append(f"{len(salvos)} fórmula(s) que dependiam de outras planilhas viraram o valor salvo.")
    return avisos
