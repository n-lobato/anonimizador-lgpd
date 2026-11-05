"""Imagens digitalizadas (PNG, JPG, TIFF, BMP): OCR + tarja nos pixels."""

from __future__ import annotations

from pathlib import Path

from . import ErroFormato, Extraido, Opcoes
from .pdf import fitz, ler_paginas, tarjar_documento


def _como_pdf(caminho: str):
    f = fitz()
    try:
        img = f.open(caminho)
        dados = img.convert_to_pdf()
        img.close()
    except Exception as e:
        raise ErroFormato(f"não foi possível abrir a imagem ({e}).") from e
    return f.open("pdf", dados)


def _exigir_ocr(opcoes: Opcoes) -> None:
    if not opcoes.ocr:
        raise ErroFormato("imagens só podem ser analisadas com o OCR ligado.")


def extrair(caminho: str, opcoes: Opcoes) -> Extraido:
    _exigir_ocr(opcoes)
    avisos: list[str] = []
    doc = _como_pdf(caminho)
    try:
        paginas = ler_paginas(doc, opcoes, avisos, sempre_ocr=True)
    finally:
        doc.close()
    return Extraido("\n\f\n".join(p.texto for p in paginas), avisos, paginas)


def anonimizar(caminho: str, saida: str, substituidor, opcoes: Opcoes, cache=None) -> list[str]:
    _exigir_ocr(opcoes)
    from PIL import Image

    avisos: list[str] = []
    f = fitz()
    with Image.open(caminho) as original:
        largura_px = original.size[0]
        dpi = original.info.get("dpi")
    doc = _como_pdf(caminho)
    try:
        paginas = cache if cache and len(cache) == doc.page_count else ler_paginas(doc, opcoes, avisos, True)
        tarjar_documento(doc, paginas, substituidor)
        quadros = []
        for page in doc:
            zoom = largura_px / page.rect.width if page.rect.width else 1
            pix = page.get_pixmap(matrix=f.Matrix(zoom, zoom), alpha=False)
            quadros.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    finally:
        doc.close()

    ext = Path(saida).suffix.lower()
    params = {}
    if dpi:
        params["dpi"] = dpi
    if ext in (".jpg", ".jpeg"):
        params["quality"] = 95
    if len(quadros) > 1 and ext in (".tif", ".tiff"):
        quadros[0].save(saida, save_all=True, append_images=quadros[1:], **params)
    else:
        if len(quadros) > 1:
            avisos.append("Imagem com várias páginas: apenas a primeira foi salva.")
        quadros[0].save(saida, **params)  # metadados EXIF não são copiados
    return avisos
