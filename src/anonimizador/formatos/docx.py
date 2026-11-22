"""Word (.docx): substitui o texto preservando a formatação.

Trabalha direto no XML do pacote, para alcançar corpo, tabelas, caixas de
texto, cabeçalhos, rodapés, notas, comentários e alterações controladas.
Um nome pode estar dividido em vários "runs" com formatações diferentes; o
código é escrito no primeiro run e o restante do nome é apagado.
Também limpa autor, empresa e autores de comentários e revisões, anonimiza os
textos de gráficos e SmartArt e remove da cópia os objetos incorporados
(planilhas, PDFs e outros arquivos colados no documento, com as miniaturas deles)
e as macros (.docm vira .docx).
"""

from __future__ import annotations

import posixpath
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

from . import ErroFormato, Extraido, Opcoes, imagens_office

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % W_NS
W15 = "{http://schemas.microsoft.com/office/word/2012/wordml}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
DC = "{http://purl.org/dc/elements/1.1/}"
CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
EP = "{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
TIPO_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
MARCADOR = "[objeto incorporado removido]"
MARCADOR_IMAGEM = "[imagem removida]"
PARTE_VBA = re.compile(r"^word/(?:vbaProject\.bin|vbaData\.xml|_rels/vbaProject\.bin\.rels)$")
PARTE_GRAFICO = re.compile(r"^word/(?:charts/chart\d+|diagrams/(?:data|drawing)\d+)\.xml$")
CONTEINERES = {W + "object", W + "pict", W + "drawing", MC + "AlternateContent"}

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
    analise = None
    with _ler_pacote(caminho) as z:
        nomes = z.namelist()
        if "word/document.xml" not in nomes:
            raise ErroFormato("o pacote não contém word/document.xml.")
        for nome in nomes:
            if PARTE_TEXTO.match(nome):
                partes.extend(_textos_da_parte(etree.fromstring(z.read(nome), PARSER)))
            elif PARTE_GRAFICO.match(nome):
                raiz = etree.fromstring(z.read(nome), PARSER)
                partes.extend(el.text for el in raiz.iter()
                              if isinstance(el.tag, str) and el.text and el.text.strip())
        if "docProps/core.xml" in nomes:
            core = etree.fromstring(z.read("docProps/core.xml"), PARSER)
            for el in core:
                if el.tag in (DC + "title", DC + "subject", DC + "description", CP + "keywords"):
                    if el.text:
                        partes.append(el.text)
        imagens = {n: z.read(n) for n in nomes if n.startswith("word/media/")}
        if imagens and opcoes.remover_imagens:
            avisos.append(f"O documento tem {len(imagens)} imagem(ns). Elas serão REMOVIDAS da cópia, "
                          "como pedido nas opções.")
        elif imagens:
            analise = imagens_office.analisar(imagens, opcoes)
            partes.append(analise.texto())
            avisos.extend(imagens_office.avisos_analise(analise))
        objetos = [n for n in nomes if n.startswith("word/embeddings/")]
        if objetos:
            avisos.append(f"O documento tem {len(objetos)} objeto(s) incorporado(s) (planilhas, PDFs ou "
                          "outros arquivos). Eles não são analisados e serão REMOVIDOS da cópia.")
        if any(PARTE_VBA.match(n) for n in nomes):
            avisos.append("O documento tem macros. Elas serão removidas e a cópia será salva como .docx.")
        doc = z.read("word/document.xml")
        if b"<w:del " in doc or b"<w:ins " in doc:
            avisos.append("Há alterações controladas: o texto excluído também foi anonimizado, mas o "
                          "ideal é aceitar ou rejeitar as revisões antes de compartilhar.")
    return Extraido("\n".join(partes), avisos, analise)


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


# ------------------------------------------------- objetos incorporados e macros
def _origem_dos_rels(nome_rels: str) -> str:
    """word/_rels/document.xml.rels -> word/document.xml; _rels/.rels -> "" (o pacote)."""
    pasta, arq = posixpath.split(nome_rels)
    return posixpath.join(posixpath.dirname(pasta), arq[:-5]) if arq != ".rels" else ""


def _rels_da_parte(parte: str) -> str:
    pasta, arq = posixpath.split(parte)
    return posixpath.join(pasta, "_rels", arq + ".rels")


def _alvo(origem: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(origem), target))


def _ids_r(el) -> set[str]:
    return {v for k, v in el.attrib.items() if k.startswith("{%s}" % R_NS)}


def _anexado(el, raiz) -> bool:
    while el is not None:
        if el is raiz:
            return True
        el = el.getparent()
    return False


def _conteiner(el):
    """O bloco mais externo que representa o objeto no texto (w:object, desenho etc.)."""
    achado, atual = None, el
    while atual is not None and atual.tag not in (W + "r", W + "p", W + "body"):
        if atual.tag in CONTEINERES:
            achado = atual
        atual = atual.getparent()
    return achado


def _trocar_por_marcador(bloco, marcador: str) -> None:
    pai = bloco.getparent()
    if pai.tag not in (W + "r", W + "p"):
        pai.remove(bloco)  # ex.: marcador de lista com figura; não há onde pôr texto
        return
    t = etree.Element(W + "t")
    t.text = marcador
    if pai.tag == W + "r":
        novo = t
    else:
        novo = etree.Element(W + "r")
        novo.append(t)
    pai.replace(bloco, novo)


def limpar_pacote(partes: dict[str, bytes], remover_imagens: bool = False) -> list[str]:
    """Tira do pacote os objetos incorporados e as macros. Altera `partes` (nome -> bytes).

    O objeto sai junto com a relação que aponta para ele, com o trecho do documento
    que o exibe (trocado por um marcador) e com a miniatura, que é uma imagem do
    conteúdo do objeto. Em gráficos, sai só o vínculo com a planilha de dados.
    """
    objetos = {n for n in partes if n.startswith("word/embeddings/")}
    macros = {n for n in partes if PARTE_VBA.match(n)}
    imagens = {n for n in partes if n.startswith("word/media/")} if remover_imagens else set()
    remover = objetos | macros | imagens
    if not remover:
        return []

    rels = {n: etree.fromstring(partes[n], PARSER) for n in partes
            if n.endswith(".rels") and n not in remover}
    ids_removidos: dict[str, dict[str, str]] = {}  # parte -> {id da relação: parte removida}
    for nome, raiz in rels.items():
        origem = _origem_dos_rels(nome)
        for rel in list(raiz.iter(REL + "Relationship")):
            alvo = _alvo(origem, rel.get("Target", ""))
            if rel.get("TargetMode") != "External" and alvo in remover:
                ids_removidos.setdefault(origem, {})[rel.get("Id")] = alvo
                rel.getparent().remove(rel)

    marcadores = 0
    imagens_no_texto = 0
    for origem, mapa in ids_removidos.items():
        ids = set(mapa)
        if not origem.endswith(".xml") or origem not in partes:
            continue
        raiz = etree.fromstring(partes[origem], PARSER)
        sem_uso: set[str] = set()
        for el in list(raiz.iter()):
            if not isinstance(el.tag, str) or not (_ids_r(el) & ids) or not _anexado(el, raiz):
                continue
            bloco = _conteiner(el)
            if bloco is None:
                el.getparent().remove(el)  # ex.: c:externalData de um gráfico
                continue
            ids_bloco = set()
            for sub in bloco.iter():
                if isinstance(sub.tag, str):
                    ids_bloco |= _ids_r(sub)
            sem_uso |= ids_bloco
            e_objeto = any(mapa.get(i) in objetos for i in ids_bloco)
            _trocar_por_marcador(bloco, MARCADOR if e_objeto else MARCADOR_IMAGEM)
            if e_objeto:
                marcadores += 1
            else:
                imagens_no_texto += 1
        ainda_usados = set()
        for el in raiz.iter():
            if isinstance(el.tag, str):
                ainda_usados |= _ids_r(el)
        partes[origem] = _serializar(raiz)
        raiz_rels = rels.get(_rels_da_parte(origem))
        if raiz_rels is not None:
            for rel in list(raiz_rels.iter(REL + "Relationship")):
                if rel.get("Id") in sem_uso - ainda_usados:
                    rel.getparent().remove(rel)  # miniatura do objeto removido

    # imagens que ficaram sem nenhuma referência (as miniaturas) também saem
    referenciadas = {_alvo(_origem_dos_rels(n), rel.get("Target", ""))
                     for n, raiz in rels.items() for rel in raiz.iter(REL + "Relationship")
                     if rel.get("TargetMode") != "External"}
    remover |= {n for n in partes if n.startswith("word/media/") and n not in referenciadas}

    for nome, raiz in rels.items():
        partes[nome] = _serializar(raiz)
    if "[Content_Types].xml" in partes:
        ct = etree.fromstring(partes["[Content_Types].xml"], PARSER)
        for o in list(ct.iter(CT + "Override")):
            nome = o.get("PartName", "").lstrip("/")
            if nome in remover:
                ct.remove(o)
            elif macros and nome == "word/document.xml" and "macroEnabled" in o.get("ContentType", ""):
                o.set("ContentType", TIPO_DOCX)
        if macros and not any(n.lower().endswith(".bin") for n in partes if n not in remover):
            for d in list(ct.iter(CT + "Default")):
                if d.get("Extension", "").lower() == "bin":
                    ct.remove(d)
        partes["[Content_Types].xml"] = _serializar(ct)
    for nome in remover:
        partes.pop(nome, None)

    avisos = []
    if objetos:
        avisos.append(f"{len(objetos)} objeto(s) incorporado(s) (planilhas, PDFs ou outros arquivos) "
                      f"removido(s) da cópia, junto com as miniaturas. No texto ficou "
                      f"\"{MARCADOR}\" ({marcadores} ocorrência(s)).")
    if macros:
        avisos.append("As macros foram removidas e a cópia foi salva como .docx.")
    if imagens:
        avisos.append(f"{len(imagens)} imagem(ns) removida(s) da cópia, como pedido nas opções. No texto "
                      f"ficou \"{MARCADOR_IMAGEM}\" ({imagens_no_texto} ocorrência(s)).")
    return avisos


def _serializar(raiz) -> bytes:
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", standalone=True)


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    with _ler_pacote(caminho) as zin:
        infos = zin.infolist()
        partes = {i.filename: zin.read(i.filename) for i in infos}
    try:
        avisos = limpar_pacote(partes, opcoes.remover_imagens)
    except etree.XMLSyntaxError as e:
        raise ErroFormato(f"XML inválido ao remover objetos incorporados ({e}).") from e
    if not opcoes.remover_imagens:
        midia = {n: partes[n] for n in partes if n.startswith("word/media/")}
        if midia:
            analise = cache if isinstance(cache, imagens_office.Analise) \
                else imagens_office.analisar(midia, opcoes)
            tarjadas = 0
            for nome, dados in midia.items():
                novo, acao = imagens_office.tratar(nome, dados, analise, substituidor, opcoes)
                partes[nome] = novo
                tarjadas += acao == "tarjada"
            avisos += imagens_office.aviso_resultado(analise, tarjadas)
            if not isinstance(cache, imagens_office.Analise):  # sem análise prévia, avisa agora
                avisos += imagens_office.avisos_analise(analise, presentes=set(midia))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx", dir=str(Path(saida).parent))
    tmp.close()
    try:
        with zipfile.ZipFile(tmp.name, "w") as zout:
            for info in infos:
                nome = info.filename
                if nome not in partes:
                    continue  # objeto incorporado, miniatura ou macro removidos
                dados = partes[nome]
                try:
                    if PARTE_TEXTO.match(nome):
                        raiz = etree.fromstring(dados, PARSER)
                        _processar_parte_texto(raiz, substituidor)
                        _limpar_autores(raiz)
                        dados = _serializar(raiz)
                    elif PARTE_GRAFICO.match(nome):
                        raiz = etree.fromstring(dados, PARSER)
                        _processar_texto_generico(raiz, substituidor)
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
        with zipfile.ZipFile(tmp.name) as conferir:
            sobrou = [n for n in conferir.namelist()
                      if n.startswith("word/embeddings/") or PARTE_VBA.match(n)]
        if sobrou:  # nunca deve acontecer; se acontecer, não entrega o arquivo
            raise ErroFormato(f"não foi possível remover da cópia: {', '.join(sobrou)}")
        shutil.move(tmp.name, saida)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return avisos
