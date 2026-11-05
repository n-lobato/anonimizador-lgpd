"""Word (.docx): substitui o texto preservando a formatação.

Trabalha direto no XML do pacote, para alcançar corpo, tabelas, caixas de
texto, cabeçalhos, rodapés, notas, comentários e alterações controladas.
Um nome pode estar dividido em vários "runs" com formatações diferentes; o
código é escrito no primeiro run e o restante do nome é apagado.
Também limpa autor, empresa e autores de comentários e revisões.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

from . import ErroFormato, Extraido, Opcoes

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
DC = "{http://purl.org/dc/elements/1.1/}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
EP = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"

PARTE_TEXTO = re.compile(
    r"^word/(?:document|header\d*|footer\d*|footnotes|endnotes|comments|commentsExtended"
    r"|glossary/document)\.xml$")
PARTE_WORD_XML = re.compile(r"^word/.*\.xml$")
TAGS_SEP = {W + "tab": "\t", W + "br": "\n", W + "cr": "\n", W + "noBreakHyphen": "-"}
ATRIBUTOS_AUTOR = {W + "author": "Anonimizado", W + "initials": "AN", W15 + "author": "Anonimizado",
                   W15 + "userId": "", W15 + "providerId": "None"}
PARSER = etree.XMLParser(remove_blank_text=False, resolve_entities=False, huge_tree=True)


def _p_de(no):
    pai = no.getparent()
    while pai is not None and pai.tag != W + "p":
        pai = pai.getparent()
    return pai


def _sequencias(p):
    """Itens (nó ou None, texto) do parágrafo: texto normal, excluído e de campos."""
    seqs = {"t": [], "del": [], "instr": []}
    for no in p.iter(W + "t", W + "delText", W + "instrText", *TAGS_SEP.keys()):
        if _p_de(no) is not p:
            continue
        if no.tag == W + "t":
            seqs["t"].append((no, no.text or ""))
        elif no.tag == W + "delText":
            seqs["del"].append((no, no.text or ""))
        elif no.tag == W + "instrText":
            seqs["instr"].append((no, no.text or ""))
        else:
            sep = TAGS_SEP[no.tag]
            seqs["t"].append((None, sep))
            seqs["del"].append((None, sep))
    return seqs


def _texto(itens) -> str:
    return "".join(t for _, t in itens)


def aplicar_trechos(itens, trechos) -> bool:
    """Reescreve os nós de texto aplicando [(ini, fim, substituto)]. Devolve se mudou."""
    if not trechos:
        return False
    mudou = False
    emitidos: set[int] = set()
    pos = 0
    for no, txt in itens:
        ini_no, fim_no = pos, pos + len(txt)
        pos = fim_no
        if no is None:
            continue
        partes, cursor = [], ini_no
        for j, (a, b, rep) in enumerate(trechos):
            if b <= ini_no or a >= fim_no:
                continue
            inicio = max(a, ini_no)
            if inicio > cursor:
                partes.append(txt[cursor - ini_no:inicio - ini_no])
            if j not in emitidos:
                partes.append(rep)
                emitidos.add(j)
            cursor = max(cursor, min(b, fim_no))
        if cursor < fim_no:
            partes.append(txt[cursor - ini_no:])
        novo = "".join(partes)
        if novo != txt:
            no.text = novo
            no.set(XML_SPACE, "preserve")
            mudou = True
    return mudou


def _ler_pacote(caminho: str) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(caminho)
    except zipfile.BadZipFile as e:
        raise ErroFormato("arquivo .docx corrompido ou não é um documento do Word.") from e


def _textos_da_parte(raiz) -> list[str]:
    saida = []
    for p in raiz.iter(W + "p"):
        seqs = _sequencias(p)
        for nome in ("t", "del", "instr"):
            s = _texto(seqs[nome])
            if s.strip():
                saida.append(s)
    return saida


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    partes: list[str] = []
    avisos: list[str] = []
    with _ler_pacote(caminho) as z:
        nomes = z.namelist()
        if "word/document.xml" not in nomes:
            raise ErroFormato("o pacote não contém word/document.xml.")
        for nome in nomes:
            if PARTE_TEXTO.match(nome):
                partes.extend(_textos_da_parte(etree.fromstring(z.read(nome), PARSER)))
        if "docProps/core.xml" in nomes:
            core = etree.fromstring(z.read("docProps/core.xml"), PARSER)
            for el in core:
                if el.tag in (DC + "title", DC + "subject", DC + "description", CP + "keywords"):
                    if el.text:
                        partes.append(el.text)
        imagens = [n for n in nomes if n.startswith("word/media/")]
        if imagens:
            avisos.append(f"O documento tem {len(imagens)} imagem(ns); textos dentro de imagens "
                          "(assinaturas, carimbos, prints) NÃO são anonimizados.")
        if any(n.startswith("word/embeddings/") for n in nomes):
            avisos.append("O documento tem objetos incorporados (planilhas, PDFs); eles não são analisados.")
        doc = z.read("word/document.xml")
        if b"<w:del " in doc or b"<w:ins " in doc:
            avisos.append("Há alterações controladas: o texto excluído também foi anonimizado, mas o "
                          "ideal é aceitar ou rejeitar as revisões antes de compartilhar.")
    return Extraido("\n".join(partes), avisos)


def _processar_parte_texto(raiz, substituidor) -> None:
    for p in raiz.iter(W + "p"):
        seqs = _sequencias(p)
        for nome in ("t", "del", "instr"):
            itens = seqs[nome]
            texto = _texto(itens)
            if texto.strip():
                if nome == "instr":
                    # códigos de campo (ex.: HYPERLINK "mailto:...") sem colchetes
                    trechos = substituidor.trechos(texto, colchetes=False)
                else:
                    trechos = substituidor.trechos(texto)
                aplicar_trechos(itens, trechos)


def _limpar_autores(raiz) -> None:
    for el in raiz.iter():
        if not isinstance(el.tag, str):
            continue
        for attr, valor in ATRIBUTOS_AUTOR.items():
            if attr in el.attrib:
                el.set(attr, valor)


def _processar_core(raiz, substituidor) -> None:
    for el in raiz:
        if el.tag in (DC + "creator", CP + "lastModifiedBy"):
            el.text = ""
        elif el.tag in (DC + "title", DC + "subject", DC + "description", CP + "keywords", CP + "category"):
            if el.text:
                el.text = substituidor.substituir(el.text)


def _processar_app(raiz) -> None:
    for el in raiz:
        if el.tag in (EP + "Company", EP + "Manager"):
            el.text = ""


def _processar_rels(raiz, substituidor) -> None:
    for rel in raiz.iter(REL + "Relationship"):
        if rel.get("TargetMode") != "External":
            continue
        alvo = rel.get("Target", "")
        if alvo.lower().startswith("file:") or re.match(r"^[a-zA-Z]:\\", alvo) or alvo.startswith("\\\\"):
            rel.set("Target", "file:///anonimizado")  # caminho local pode revelar usuário
        else:
            rel.set("Target", substituidor.substituir(alvo).replace("[", "").replace("]", ""))


def _processar_texto_generico(raiz, substituidor) -> None:
    for el in raiz.iter():
        if isinstance(el.tag, str) and el.text and el.text.strip():
            el.text = substituidor.substituir(el.text)


def _serializar(raiz) -> bytes:
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    with _ler_pacote(caminho) as zin:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx", dir=str(Path(saida).parent))
        tmp.close()
        try:
            with zipfile.ZipFile(tmp.name, "w") as zout:
                for info in zin.infolist():
                    dados = zin.read(info.filename)
                    nome = info.filename
                    try:
                        if PARTE_TEXTO.match(nome):
                            raiz = etree.fromstring(dados, PARSER)
                            _processar_parte_texto(raiz, substituidor)
                            _limpar_autores(raiz)
                            dados = _serializar(raiz)
                        elif PARTE_WORD_XML.match(nome):
                            raiz = etree.fromstring(dados, PARSER)
                            _limpar_autores(raiz)
                            dados = _serializar(raiz)
                        elif nome == "docProps/core.xml":
                            raiz = etree.fromstring(dados, PARSER)
                            _processar_core(raiz, substituidor)
                            dados = _serializar(raiz)
                        elif nome == "docProps/app.xml":
                            raiz = etree.fromstring(dados, PARSER)
                            _processar_app(raiz)
                            dados = _serializar(raiz)
                        elif nome == "docProps/custom.xml" or re.match(r"^customXml/item\d+\.xml$", nome):
                            raiz = etree.fromstring(dados, PARSER)
                            _processar_texto_generico(raiz, substituidor)
                            dados = _serializar(raiz)
                        elif nome.endswith(".rels"):
                            raiz = etree.fromstring(dados, PARSER)
                            _processar_rels(raiz, substituidor)
                            dados = _serializar(raiz)
                    except etree.XMLSyntaxError as e:
                        raise ErroFormato(f"XML inválido em {nome} ({e}).") from e
                    zout.writestr(info, dados, compress_type=info.compress_type)
            shutil.move(tmp.name, saida)
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    return []
