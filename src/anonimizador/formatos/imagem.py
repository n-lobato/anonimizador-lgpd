"""Imagens digitalizadas (PNG, JPG, TIFF, BMP): OCR + tarja nos pixels."""

from __future__ import annotations

from pathlib import Path

from . import ErroFormato, Extraido, Opcoes

# texto em linhas físicas: a detecção também junta as quebras de linha do parágrafo
JUNTAR_LINHAS = True
from .pdf import fitz, ler_paginas, tarjar_documento


# Imagens pequenas (ex.: foto de identidade colada no Word com 600 pixels de largura)
# têm letras de poucos pixels, e o OCR erra. Ampliar com boa interpolação antes do
# OCR melhorou a leitura em testes com uma identidade real (o CPF só foi achado
# assim). A página continua do mesmo tamanho; muda só a resolução da imagem nela.
LADO_MINIMO = 1600
AMPLIACAO_MAXIMA = 3


def _ampliada(caminho: str) -> bytes | None:
    """PNG ampliado da imagem, se ela for pequena; None para usar a original."""
    import io
    import math

    from PIL import Image
    try:
        with Image.open(caminho) as im:
            if getattr(im, "n_frames", 1) > 1 or max(im.size) >= LADO_MINIMO:
                return None
            k = min(AMPLIACAO_MAXIMA, math.ceil(LADO_MINIMO / max(im.size)))
            dpi = im.info.get("dpi") or (96, 96)
            if im.mode not in ("RGB", "L"):
                fundo = Image.new("RGB", im.size, "white")
                rgba = im.convert("RGBA")
                fundo.paste(rgba, mask=rgba.getchannel("A"))
                im2 = fundo
            else:
                im2 = im.copy()
            im2 = im2.resize((im.size[0] * k, im.size[1] * k), Image.LANCZOS)
            buf = io.BytesIO()
            im2.save(buf, format="PNG", dpi=(float(dpi[0]) * k, float(dpi[1]) * k))
            return buf.getvalue()
    except Exception:
        return None


def _como_pdf(caminho: str):
    from .limites import conferir_imagem
    conferir_imagem(caminho)  # antes de decodificar: recusa dimensões absurdas
    f = fitz()
    try:
        ampliada = _ampliada(caminho)
        img = f.open("png", ampliada) if ampliada else f.open(caminho)
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
