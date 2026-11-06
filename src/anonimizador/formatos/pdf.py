"""PDF: tarja definitiva (o texto por baixo é apagado, não só coberto).

Usa redação do PyMuPDF: o conteúdo sob cada tarja é removido do arquivo e,
em páginas digitalizadas, os pixels da imagem também são apagados. Sobre a
tarja é escrito o código (ex.: PESSOA_1) para manter a leitura do documento.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ErroFormato, Extraido, Opcoes

# texto em linhas físicas: a detecção também junta as quebras de linha do parágrafo
JUNTAR_LINHAS = True
from .ocr import localizar_tessdata


def fitz():
    try:
        import pymupdf as _f  # type: ignore
    except ImportError:
        try:
            import fitz as _f  # type: ignore
        except ImportError as e:
            raise ErroFormato("PyMuPDF não está instalado (pip install PyMuPDF).") from e
    return _f


@dataclass
class PaginaTexto:
    texto: str
    caixas: list  # uma caixa (x0, y0, x1, y1) por caractere; None em quebras de linha
    ocr: bool = False


def _flags(f) -> int:
    return getattr(f, "TEXT_PRESERVE_WHITESPACE", 1) | getattr(f, "TEXT_MEDIABOX_CLIP", 64)


def _textpage_ocr(page, opcoes: Opcoes, completo: bool):
    pasta = localizar_tessdata(opcoes.idioma_ocr)
    if not pasta:
        raise ErroFormato("OCR indisponível: dados do idioma português (por.traineddata) não encontrados.")
    try:
        return page.get_textpage_ocr(language=opcoes.idioma_ocr, dpi=opcoes.dpi_ocr,
                                     full=completo, tessdata=pasta)
    except TypeError:  # versões antigas do PyMuPDF sem o parâmetro tessdata
        import os
        os.environ["TESSDATA_PREFIX"] = pasta
        return page.get_textpage_ocr(language=opcoes.idioma_ocr, dpi=opcoes.dpi_ocr, full=completo)


def _texto_da_pagina(page, opcoes: Opcoes, avisos: list[str], numero: int,
                     sempre_ocr: bool = False) -> PaginaTexto:
    f = fitz()
    flags = _flags(f)
    nativo = page.get_text("text", flags=flags)
    tem_imagem = bool(page.get_images(full=False))
    digitalizada = len(nativo.strip()) < 25 and tem_imagem
    tp, usou_ocr = None, False
    if sempre_ocr or digitalizada or (opcoes.forcar_ocr and tem_imagem):
        if opcoes.ocr or sempre_ocr:
            try:
                tp = _textpage_ocr(page, opcoes, completo=digitalizada or sempre_ocr)
                usou_ocr = True
            except ErroFormato as e:
                avisos.append(f"Página {numero}: {e}")
            except Exception as e:  # erro do motor de OCR
                avisos.append(f"Página {numero}: falha no OCR ({e}).")
        elif digitalizada:
            avisos.append(f"Página {numero} parece digitalizada (imagem) e o OCR está desligado: "
                          "dados nessa página NÃO foram anonimizados.")
    if tp is not None:
        dados = page.get_text("rawdict", textpage=tp)
    else:
        dados = page.get_text("rawdict", flags=flags)

    chars: list[str] = []
    caixas: list = []
    for bloco in dados.get("blocks", []):
        if bloco.get("type", 0) != 0:
            continue
        for linha in bloco.get("lines", []):
            for span in linha.get("spans", []):
                for c in span.get("chars", []):
                    chars.append(c.get("c", ""))
                    caixas.append(tuple(c["bbox"]))
            chars.append("\n")
            caixas.append(None)
        chars.append("\n")
        caixas.append(None)
    # um "caractere" pode vir vazio ou com mais de uma letra; normaliza para 1:1
    texto_final, caixas_final = [], []
    for ch, cx in zip(chars, caixas):
        if not ch:
            continue
        for sub in ch:
            texto_final.append(sub)
            caixas_final.append(cx)
    if usou_ocr and not "".join(texto_final).strip():
        avisos.append(f"Página {numero}: o OCR não reconheceu texto.")
    return PaginaTexto("".join(texto_final), caixas_final, usou_ocr)


def ler_paginas(doc, opcoes: Opcoes, avisos: list[str], sempre_ocr: bool = False) -> list[PaginaTexto]:
    return [_texto_da_pagina(p, opcoes, avisos, i + 1, sempre_ocr) for i, p in enumerate(doc)]


def _abrir(caminho: str):
    f = fitz()
    try:
        doc = f.open(caminho)
    except Exception as e:
        raise ErroFormato(f"não foi possível abrir o PDF ({e}).") from e
    if doc.needs_pass:
        raise ErroFormato("PDF protegido por senha: remova a proteção antes de anonimizar.")
    return doc


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    avisos: list[str] = []
    doc = _abrir(caminho)
    try:
        paginas = ler_paginas(doc, opcoes, avisos)
        partes = [p.texto for p in paginas]
        meta = doc.metadata or {}
        partes.append("\n".join(str(v) for k, v in meta.items() if v and k in ("title", "subject", "keywords")))
        for item in doc.get_toc():
            partes.append(str(item[1]))
        # comentários e notas: um nome que só aparece num comentário também precisa ser achado
        for page in doc:
            for annot in page.annots() or []:
                try:
                    info = annot.info
                    partes.append("\n".join(v for v in (info.get("content"), info.get("subject")) if v))
                except Exception:
                    continue
        if len(doc.embfile_names()) if hasattr(doc, "embfile_names") else 0:
            avisos.append("O PDF tem arquivos anexados; eles serão removidos da versão anonimizada.")
    finally:
        doc.close()
    return Extraido("\n\f\n".join(partes), avisos, paginas)


def _retangulos(caixas: list) -> list[tuple[float, float, float, float]]:
    rects: list[list[float]] = []
    atual: list[float] | None = None
    for cx in caixas:
        if cx is None:
            if atual:
                rects.append(atual)
            atual = None
            continue
        x0, y0, x1, y1 = cx
        if x1 <= x0 or y1 <= y0:
            continue
        if atual is None:
            atual = [x0, y0, x1, y1]
            continue
        mesma_linha = abs((y0 + y1) / 2 - (atual[1] + atual[3]) / 2) < max(y1 - y0, atual[3] - atual[1]) * 0.6
        if mesma_linha and x0 >= atual[0] - 2:
            atual = [min(atual[0], x0), min(atual[1], y0), max(atual[2], x1), max(atual[3], y1)]
        else:
            rects.append(atual)
            atual = [x0, y0, x1, y1]
    if atual:
        rects.append(atual)
    return [tuple(r) for r in rects]


def _tamanho_fonte(f, texto: str, largura: float, altura: float) -> float:
    tam = max(3.0, min(altura * 0.72, 11.0))
    while tam > 3.0 and f.get_text_length(texto, fontname="helv", fontsize=tam) > largura - 1:
        tam -= 0.25
    return tam


def tarjar_documento(doc, paginas: list[PaginaTexto], substituidor) -> int:
    """Aplica as tarjas. Devolve o número de trechos tarjados."""
    f = fitz()
    total = 0
    for page, pt in zip(doc, paginas):
        trechos = substituidor.trechos(pt.texto, colchetes=False)
        for a, b, codigo in trechos:
            rects = _retangulos(pt.caixas[a:b])
            for i, r in enumerate(rects):
                if pt.ocr:
                    # caixas do OCR costumam ser estreitas: folga para não sobrar pixel do dado
                    h = r[3] - r[1]
                    rect = f.Rect(r[0] - h * 0.08, r[1] - h * 0.1, r[2] + h * 0.5, r[3] + h * 0.1)
                else:
                    rect = f.Rect(r[0] - 0.4, r[1] - 0.4, r[2] + 0.4, r[3] + 0.4)
                texto = codigo if i == 0 else None
                kwargs = dict(fill=(0, 0, 0), text_color=(1, 1, 1), cross_out=False)
                if texto:
                    kwargs.update(text=texto, fontname="helv",
                                  fontsize=_tamanho_fonte(f, texto, rect.width, rect.height),
                                  align=getattr(f, "TEXT_ALIGN_CENTER", 1))
                page.add_redact_annot(rect, **kwargs)
            total += 1
        # anotações (comentários) podem conter nomes
        for annot in list(page.annots() or []):
            try:
                if annot.type[0] == getattr(f, "PDF_ANNOT_REDACT", 12):
                    continue
                info = annot.info
                annot.set_info(content=substituidor.substituir(info.get("content", "")),
                               title="Anonimizado", subject=substituidor.substituir(info.get("subject", "")))
                annot.update()
            except Exception:
                continue
        if trechos:
            page.apply_redactions(images=getattr(f, "PDF_REDACT_IMAGE_PIXELS", 2))
    return total


def limpar_metadados(doc, substituidor) -> None:
    try:
        toc = doc.get_toc(simple=False)
        if toc:
            doc.set_toc([[t[0], substituidor.substituir(t[1]), t[2], *t[3:]] for t in toc])
    except Exception:
        pass
    try:
        doc.scrub(attached_files=True, clean_pages=True, embedded_files=True, hidden_text=False,
                  javascript=True, metadata=True, redactions=False, remove_links=True,
                  reset_fields=True, reset_responses=True, thumbnails=True, xml_metadata=True)
    except Exception:
        try:
            doc.set_metadata({})
            doc.del_xml_metadata()
        except Exception:
            pass


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    avisos: list[str] = []
    doc = _abrir(caminho)
    try:
        paginas = cache if cache and len(cache) == doc.page_count else ler_paginas(doc, opcoes, avisos)
        tarjar_documento(doc, paginas, substituidor)
        limpar_metadados(doc, substituidor)
        doc.save(saida, garbage=4, deflate=True, clean=True)
    finally:
        doc.close()
    return avisos
