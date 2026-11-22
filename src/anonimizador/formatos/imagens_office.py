"""Imagens coladas dentro de documentos do Word e do Excel.

Cada imagem em formato de pixels (PNG, JPG, TIFF, BMP) passa pelo mesmo OCR das
imagens soltas. Se o texto lido tiver algum dado pessoal, a imagem é trocada por
uma versão com tarja nos pixels. As demais perdem só os metadados (EXIF, que
pode ter a localização GPS da foto, XMP e comentários).

Limites, que o aviso ao usuário repete: o OCR não lê bem fotos tortas, borradas
ou com reflexo, e não enxerga o que não é texto (rosto, assinatura, carimbo,
digital). Formatos vetoriais do Office (EMF, WMF, SVG) e outros não são lidos.
"""

from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import Opcoes

LEGIVEIS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
CHAVES_METADADOS = ("exif", "xmp", "XML:com.adobe.xmp", "comment", "photoshop", "iptc")


@dataclass
class Analise:
    textos: dict[str, tuple[str, object]] = field(default_factory=dict)  # nome -> (texto, cache do OCR)
    nao_legiveis: list[str] = field(default_factory=list)
    falhas: list[str] = field(default_factory=list)
    sem_ocr: list[str] = field(default_factory=list)
    mensagens: list[str] = field(default_factory=list)  # avisos do OCR (ex.: motor sem idioma)

    def texto(self) -> str:
        return "\n\n".join(t for t, _ in self.textos.values() if t.strip())


def legivel(nome: str) -> bool:
    return Path(nome).suffix.lower() in LEGIVEIS


def analisar(imagens: dict[str, bytes], opcoes: Opcoes) -> Analise:
    """OCR de cada imagem. `imagens`: nome (com a extensão) -> conteúdo."""
    from . import imagem

    r = Analise()
    with tempfile.TemporaryDirectory(prefix="anon_img_") as pasta:
        for i, (nome, dados) in enumerate(imagens.items()):
            if not legivel(nome):
                r.nao_legiveis.append(nome)
                continue
            if not opcoes.ocr:
                r.sem_ocr.append(nome)
                continue
            arq = Path(pasta) / f"{i}{Path(nome).suffix.lower()}"
            arq.write_bytes(dados)
            try:
                ext = imagem.extrair(str(arq), opcoes)
            except Exception as e:  # imagem corrompida ou formato interno incomum
                r.falhas.append(nome)
                r.mensagens.append(str(e))
                continue
            if ext.avisos:  # o OCR falhou na imagem (os avisos dizem por quê)
                r.falhas.append(nome)
                r.mensagens += [a.split(": ", 1)[-1] for a in ext.avisos]
            else:
                r.textos[nome] = (ext.texto, ext.cache)
    return r


def _sem_metadados(dados: bytes, nome: str) -> bytes | None:
    """Mesma imagem sem EXIF/XMP/comentários/tags, ou None se não havia o que tirar.

    A imagem é recriada só a partir dos pixels: regravar o objeto aberto mantinha o
    comentário e o XMP do JPEG e as tags do TIFF (autor, descrição), como mostrou um teste.
    """
    from PIL import Image

    try:
        with Image.open(io.BytesIO(dados)) as im:
            tem = bool(im.getexif()) or any(k in im.info for k in CHAVES_METADADOS) \
                or bool(getattr(im, "text", None)) or bool(getattr(im, "tag_v2", None))
            if not tem:
                return None
            formato = im.format
            params: dict = {}
            if formato == "JPEG":
                from PIL import JpegImagePlugin
                params["qtables"] = im.quantization  # mesma compressão do original
                params["subsampling"] = JpegImagePlugin.get_sampling(im)
            if "icc_profile" in im.info:
                params["icc_profile"] = im.info["icc_profile"]  # perfil de cor não identifica ninguém
            if "dpi" in im.info:
                params["dpi"] = im.info["dpi"]
            im.load()
            limpa = Image.frombytes(im.mode, im.size, im.tobytes())
            if im.mode == "P":
                limpa.putpalette(im.getpalette())
                if "transparency" in im.info:
                    params["transparency"] = im.info["transparency"]
            saida = io.BytesIO()
            limpa.save(saida, format=formato, **params)
            return saida.getvalue()
    except Exception:
        return None


def tratar(nome: str, dados: bytes, analise: Analise, substituidor, opcoes: Opcoes) -> tuple[bytes, str]:
    """Devolve (conteúdo novo, ação): "tarjada", "metadados" ou "" (sem mudança)."""
    from . import imagem

    texto, cache = analise.textos.get(nome, ("", None))
    if texto and substituidor.trechos(texto):
        sufixo = Path(nome).suffix.lower()
        with tempfile.TemporaryDirectory(prefix="anon_img_") as pasta:
            entrada, saida = Path(pasta) / f"e{sufixo}", Path(pasta) / f"s{sufixo}"
            entrada.write_bytes(dados)
            imagem.anonimizar(str(entrada), str(saida), substituidor, opcoes, cache)
            return saida.read_bytes(), "tarjada"
    limpo = _sem_metadados(dados, nome)
    return (limpo, "metadados") if limpo is not None else (dados, "")


def aviso_resultado(analise: Analise, tarjadas: int) -> list[str]:
    lidas = len(analise.textos)
    if not lidas:
        return []
    return [f"{lidas} imagem(ns) do documento passaram por OCR; {tarjadas} recebeu(ram) tarja. "
            "O OCR não lê bem fotos tortas ou borradas e não enxerga rosto, assinatura, carimbo "
            "ou digital: confira as imagens, ou use a opção de remover imagens."]


def avisos_analise(analise: Analise, presentes: set[str] | None = None) -> list[str]:
    """Avisos sobre imagens que ficaram sem análise; `presentes` limita às que ficaram na cópia."""
    def so(lista):
        return [n for n in lista if presentes is None or n in presentes]
    analise = Analise(analise.textos, so(analise.nao_legiveis), so(analise.falhas), so(analise.sem_ocr),
                      analise.mensagens)
    r = []
    if analise.nao_legiveis:
        r.append(f"{len(analise.nao_legiveis)} imagem(ns) em formato que o OCR não lê (EMF, WMF, SVG, "
                 "GIF etc.) ficaram como estavam. Para tirá-las, use a opção de remover imagens.")
    if analise.sem_ocr:
        r.append(f"O OCR está desligado: {len(analise.sem_ocr)} imagem(ns) do documento NÃO foram "
                 "analisadas e ficaram como estavam.")
    if analise.falhas:
        motivo = f" Motivo: {sorted(set(analise.mensagens))[0]}" if analise.mensagens else ""
        r.append(f"ATENÇÃO: {len(analise.falhas)} imagem(ns) NÃO puderam ser lidas pelo OCR e ficaram "
                 f"como estavam, sem tarja.{motivo}")
    return r
