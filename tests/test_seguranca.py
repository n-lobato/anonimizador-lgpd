"""Arquivos maliciosos ou corrompidos: o programa recusa com mensagem clara, não trava,
não fecha e continua processando os outros arquivos do lote."""

import os
import struct
import zipfile
import zlib
from pathlib import Path

import pytest

from anonimizador.config import Configuracao, Termos
from anonimizador.processador import Sessao, listar_arquivos

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    fitz = None

FRASE = "Requerente: Pedro Henrique Alves, CPF 529.982.247-25."
BOMBA_XML = ('<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaaaaaaaa">'
             + "".join(f'<!ENTITY {b} "{("&" + a + ";") * 10}">'
                       for a, b in zip("abcdefgh", "bcdefghi"))
             + "]>")


def _rodar(arquivos, **cfg):
    s = Sessao(Configuracao(**cfg), Termos())
    s.carregar([str(a) for a in arquivos])
    s.analisar()
    s.aplicar()
    return {a.caminho.name: a for a in s.arquivos}


def _texto_ok(tmp_path) -> Path:
    f = tmp_path / "bom.txt"
    f.write_text(FRASE, encoding="utf-8")
    return f


def _png_cabecalho(largura: int, altura: int) -> bytes:
    """PNG que só declara as dimensões (a imagem em si não existe)."""
    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))
    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", ihdr) + bloco(b"IDAT", zlib.compress(b"\x00"))
            + bloco(b"IEND", b""))


def _docx_valido(tmp_path) -> dict[str, bytes]:
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph(FRASE)
    f = tmp_path / "base.docx"
    d.save(f)
    with zipfile.ZipFile(f) as z:
        return {n: z.read(n) for n in z.namelist()}


def _gravar_zip(destino: Path, partes: dict[str, bytes]) -> Path:
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in partes.items():
            z.writestr(n, d)
    return destino


# ------------------------------------------------------------ bombas ZIP e XML
@pytest.mark.parametrize("ext", ["docx", "xlsx"])
def test_bomba_zip_e_recusada(tmp_path, ext):
    """Poucos KB que viram 60 MB de zeros ao descompactar."""
    f = _gravar_zip(tmp_path / f"bomba.{ext}", {"[Content_Types].xml": b"<Types/>",
                                                  "lixo.bin": b"\0" * (60 * 1024 * 1024)})
    assert f.stat().st_size < 1024 * 1024
    r = _rodar([f, _texto_ok(tmp_path)])
    assert "bomba ZIP" in r[f.name].erro
    assert r["bom.txt"].saida is not None  # o resto do lote continua


def test_bomba_xml_no_word(tmp_path):
    partes = _docx_valido(tmp_path)
    doc = partes["word/document.xml"].decode()
    partes["word/document.xml"] = (BOMBA_XML + doc.split("?>", 1)[1].replace(
        "Requerente:", "Requerente: &i;", 1)).encode()
    f = _gravar_zip(tmp_path / "bomba_xml.docx", partes)
    r = _rodar([f, _texto_ok(tmp_path)])
    assert "bomba XML" in r[f.name].erro and r[f.name].saida is None
    assert r["bom.txt"].saida is not None


def test_bomba_xml_no_excel(tmp_path):
    from openpyxl import Workbook

    import openpyxl.xml
    assert openpyxl.xml.DEFUSEDXML, "o defusedxml precisa estar instalado"
    wb = Workbook()
    wb.active["A1"] = "texto"
    base = tmp_path / "base.xlsx"
    wb.save(base)
    with zipfile.ZipFile(base) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    folha = partes["xl/worksheets/sheet1.xml"].decode()
    corpo = folha.split("?>", 1)[1] if folha.startswith("<?xml") else folha
    partes["xl/worksheets/sheet1.xml"] = (BOMBA_XML + corpo).encode()
    f = _gravar_zip(tmp_path / "bomba_xml.xlsx", partes)
    r = _rodar([f])
    assert "bomba XML" in r[f.name].erro and r[f.name].saida is None


# ------------------------------------------------------------ arquivos corrompidos
@pytest.mark.parametrize("ext", ["docx", "xlsx", "pdf", "png"])
def test_arquivo_corrompido_vira_erro_claro(tmp_path, ext):
    f = tmp_path / f"estragado.{ext}"
    f.write_bytes(os.urandom(4096))
    r = _rodar([f, _texto_ok(tmp_path)])
    assert r[f.name].erro, "devia ter dado erro"
    assert "Traceback" not in r[f.name].erro
    assert r["bom.txt"].saida is not None


def test_word_cortado_ao_meio(tmp_path):
    partes = _docx_valido(tmp_path)
    inteiro = _gravar_zip(tmp_path / "inteiro.docx", partes).read_bytes()
    f = tmp_path / "cortado.docx"
    f.write_bytes(inteiro[: len(inteiro) // 2])
    r = _rodar([f])
    assert "corrompido" in r[f.name].erro


# ------------------------------------------------------------ imagens enormes
def test_imagem_com_dimensoes_absurdas(tmp_path):
    f = tmp_path / "gigante.png"
    f.write_bytes(_png_cabecalho(40_000, 40_000))  # 1,6 bilhão de pixels
    r = _rodar([f, _texto_ok(tmp_path)])
    assert "imagem suspeita" in r[f.name].erro
    assert r["bom.txt"].saida is not None


def test_imagem_absurda_dentro_do_word_nao_trava(tmp_path):
    partes = _docx_valido(tmp_path)
    partes["word/media/image1.png"] = _png_cabecalho(40_000, 40_000)
    f = _gravar_zip(tmp_path / "foto_gigante.docx", partes)
    r = _rodar([f])
    a = r[f.name]
    assert not a.erro, a.erro  # o texto do documento é anonimizado normalmente
    assert any("imagem suspeita" in av for av in a.avisos)


# ------------------------------------------------------------ tamanhos e páginas
def test_texto_grande_demais(tmp_path, monkeypatch):
    from anonimizador.formatos import limites
    monkeypatch.setattr(limites, "TEXTO_MAX", 1024)
    f = tmp_path / "grande.txt"
    f.write_text("x" * 5000, encoding="utf-8")
    r = _rodar([f])
    assert "grande demais" in r[f.name].erro


def test_pdf_com_paginas_demais(tmp_path, monkeypatch):
    if fitz is None:
        pytest.skip("PyMuPDF indisponível")
    from anonimizador.formatos import limites
    monkeypatch.setattr(limites, "PAGINAS_PDF_MAX", 3)
    doc = fitz.open()
    for _ in range(5):
        doc.new_page().insert_text((72, 72), FRASE)
    f = tmp_path / "longo.pdf"
    doc.save(f)
    r = _rodar([f])
    assert "páginas" in r[f.name].erro


# ------------------------------------------------------------ atalhos em pastas
def test_pasta_nao_segue_atalho_para_fora(tmp_path):
    pasta = tmp_path / "processos"
    fora = tmp_path / "fora"
    pasta.mkdir()
    fora.mkdir()
    (pasta / "dentro.txt").write_text(FRASE, encoding="utf-8")
    (fora / "segredo.txt").write_text(FRASE, encoding="utf-8")
    try:
        (pasta / "atalho_pasta").symlink_to(fora, target_is_directory=True)
        (pasta / "atalho_arquivo.txt").symlink_to(fora / "segredo.txt")
    except (OSError, NotImplementedError):
        pytest.skip("este sistema não permite criar links simbólicos sem privilégio")
    arquivos, ignorados = listar_arquivos([pasta])
    assert [a.caminho.name for a in arquivos] == ["dentro.txt"]
    assert any("2 atalho(s)" in m for m in ignorados)
