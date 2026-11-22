"""Limites contra arquivos montados para travar o programa ou esgotar a memória.

Documentos chegam de terceiros (parte contrária, clientes, e-mail). Um .docx ou .xlsx
é um ZIP: um arquivo de poucos KB pode virar gigabytes ao ser descompactado (a
chamada "bomba ZIP"). Imagens podem declarar dimensões enormes. Os limites abaixo
ficam muito acima de qualquer documento real e só barram o que é anormal.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from . import ErroFormato

MB = 1024 * 1024
ZIP_TOTAL_MAX = 1024 * MB      # soma descompactada de todas as partes do pacote
ZIP_PARTE_MAX = 300 * MB       # uma parte (ex.: uma imagem ou o texto do documento)
ZIP_PARTES_MAX = 20_000        # quantidade de partes
ZIP_TAXA_MAX = 200             # quanto uma parte grande pode crescer ao descompactar
ZIP_TAXA_A_PARTIR = 10 * MB    # partes menores que isso não entram na conta da taxa
PIXELS_MAX = 150_000_000       # ~ 12.000 x 12.000; uma página A4 a 600 dpi tem 35 milhões
TEXTO_MAX = 300 * MB           # arquivos de texto puro
PAGINAS_PDF_MAX = 10_000


def conferir_zip(caminho: str | Path) -> None:
    """Recusa pacotes corrompidos ou que se expandem de forma anormal, antes de abrir."""
    try:
        with zipfile.ZipFile(caminho) as z:
            infos = z.infolist()
    except (zipfile.BadZipFile, OSError, ValueError) as e:
        raise ErroFormato("arquivo corrompido ou que não é um documento do Office válido.") from e
    if len(infos) > ZIP_PARTES_MAX:
        raise ErroFormato(f"arquivo suspeito: tem {len(infos)} partes internas (limite {ZIP_PARTES_MAX}).")
    total = 0
    for i in infos:
        total += i.file_size
        if i.file_size > ZIP_PARTE_MAX:
            raise ErroFormato(f"arquivo suspeito: uma parte interna ocupa {i.file_size // MB} MB "
                              f"descompactada (limite {ZIP_PARTE_MAX // MB} MB).")
        if i.file_size > ZIP_TAXA_A_PARTIR and i.file_size > ZIP_TAXA_MAX * max(i.compress_size, 1):
            raise ErroFormato("arquivo suspeito: uma parte interna cresce de forma anormal ao ser "
                              "descompactada (possível \"bomba ZIP\").")
        if total > ZIP_TOTAL_MAX:
            raise ErroFormato(f"arquivo suspeito: descompactado, passaria de {ZIP_TOTAL_MAX // MB} MB.")


def conferir_imagem(caminho_ou_dados) -> None:
    """Lê só o cabeçalho da imagem e recusa dimensões absurdas antes de decodificá-la."""
    import io

    from PIL import Image
    origem = io.BytesIO(caminho_ou_dados) if isinstance(caminho_ou_dados, (bytes, bytearray)) \
        else caminho_ou_dados
    try:
        with Image.open(origem) as im:
            largura, altura = im.size
    except Image.DecompressionBombError as e:
        raise ErroFormato("imagem suspeita: dimensões grandes demais para ser aberta com segurança.") from e
    except Exception as e:
        raise ErroFormato("imagem corrompida ou em formato não reconhecido.") from e
    if largura * altura > PIXELS_MAX:
        raise ErroFormato(f"imagem suspeita: {largura} x {altura} pixels (limite de "
                          f"{PIXELS_MAX // 1_000_000} milhões de pixels).")


def conferir_tamanho_texto(caminho: str | Path) -> None:
    tamanho = Path(caminho).stat().st_size
    if tamanho > TEXTO_MAX:
        raise ErroFormato(f"arquivo de texto grande demais ({tamanho // MB} MB; limite {TEXTO_MAX // MB} MB).")


def proteger_pillow() -> None:
    """O Pillow só avisa (não recusa) entre 89 e 178 milhões de pixels; aqui ele recusa acima do limite."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = PIXELS_MAX // 2  # o Pillow recusa a partir do dobro deste valor


def explicar_xml(e: BaseException) -> str | None:
    """Procura, na cadeia de causas do erro, um problema de XML malicioso ou corrompido."""
    vistos = set()
    while e is not None and id(e) not in vistos:
        vistos.add(id(e))
        tipo = f"{type(e).__module__}.{type(e).__name__}"
        if "amplification" in str(e) or any(t in tipo for t in (
                "EntitiesForbidden", "DTDForbidden", "ExternalReferenceForbidden")):
            return ("arquivo suspeito: o conteúdo interno usa construções de XML que podem travar o "
                    "computador (possível \"bomba XML\"). O arquivo não foi processado.")
        e = e.__cause__ or e.__context__
    return None
