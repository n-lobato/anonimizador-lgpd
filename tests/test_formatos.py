import zipfile
from pathlib import Path

import pytest

from anonimizador.config import Configuracao, Termos
from anonimizador.processador import Sessao, listar_arquivos

from .conftest import pymupdf


def _rodar(entradas, **cfg):
    c = Configuracao(**cfg)
    s = Sessao(c, Termos())
    s.carregar(entradas)
    s.analisar()
    s.aplicar()
    return s


def test_txt(tmp_path, peticao):
    f = tmp_path / "p.txt"
    f.write_text(peticao, encoding="cp1252")
    s = _rodar([f])
    saida = s.arquivos[0].saida
    assert saida == tmp_path / "anonimizados" / "p_anonimizado.txt"
    texto = saida.read_text(encoding="cp1252")
    assert "MARIA APARECIDA" not in texto and "[PESSOA_1]" in texto


def test_docx_runs_cabecalho_tabela_e_metadados(tmp_path):
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.core_properties.author = "Autor Verdadeiro"
    d.core_properties.title = "Caso de Pedro Henrique Alves"
    p = d.add_paragraph()
    p.add_run("PEDRO HEN").bold = True
    p.add_run("RIQUE ALVES").italic = True
    p.add_run(", brasileiro, CPF 529.982.247-25, e-mail pedro@exemplo.com.br.")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "Testemunha"
    t.cell(0, 1).text = "Testemunha: Kauã Ribeiro"
    d.sections[0].header.paragraphs[0].text = "Autor: Pedro Henrique Alves"
    f = tmp_path / "caso.docx"
    d.save(f)

    s = _rodar([f])
    out = docx.Document(s.arquivos[0].saida)
    corpo = out.paragraphs[0].text
    assert corpo.startswith("[PESSOA_1], brasileiro, CPF [CPF_1], e-mail [EMAIL_1].")
    assert out.paragraphs[0].runs[0].bold  # formatação do primeiro run preservada
    assert out.tables[0].cell(0, 1).text == "Testemunha: [PESSOA_2]"
    assert "[PESSOA_1]" in out.sections[0].header.paragraphs[0].text
    assert out.core_properties.author == ""
    assert "Pedro" not in (out.core_properties.title or "")
    with zipfile.ZipFile(s.arquivos[0].saida) as z:
        tudo = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml"))
    assert b"529.982.247-25" not in tudo and "Kauã".encode() not in tudo


def test_xlsx(tmp_path):
    from openpyxl import Workbook, load_workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Nome", "CPF", "Valor"])
    ws.append(["Requerente: Lucas Ferreira Gomes", "529.982.247-25", 100])
    wb.properties.creator = "Fulano"
    f = tmp_path / "lista.xlsx"
    wb.save(f)
    s = _rodar([f])
    ws2 = load_workbook(s.arquivos[0].saida).active
    assert ws2["A2"].value == "Requerente: [PESSOA_1]"
    assert ws2["B2"].value == "[CPF_1]"
    assert ws2["C2"].value == 100


def test_listagem_de_pasta_ignora_saidas(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub" / "b.pdf").write_bytes(b"%PDF")
    (tmp_path / "c.doc").write_bytes(b"x")
    (tmp_path / "anonimizados").mkdir()
    (tmp_path / "anonimizados" / "a_anonimizado.txt").write_text("x")
    arquivos, ignorados = listar_arquivos([tmp_path])
    nomes = sorted(a.caminho.name for a in arquivos)
    assert nomes == ["a.txt", "b.pdf"]
    assert any("c.doc" in m for m in ignorados)
    arquivos, _ = listar_arquivos([tmp_path], incluir_subpastas=False)
    assert [a.caminho.name for a in arquivos] == ["a.txt"]


def test_relatorio(tmp_path, peticao):
    from openpyxl import load_workbook

    from anonimizador.relatorio import gerar
    f = tmp_path / "p.txt"
    f.write_text(peticao, encoding="utf-8")
    s = _rodar([f])
    rel = gerar(s, s.pasta_relatorio())
    wb = load_workbook(rel)
    linhas = list(wb["De-para"].iter_rows(values_only=True))
    assert ("PESSOA_1" in [l[0] for l in linhas])
    assert any(l[2] == "529.982.247-25" for l in linhas)


# ------------------------------------------------------------------ PDF
fitz = pymupdf()
precisa_pdf = pytest.mark.skipif(fitz is None, reason="PyMuPDF não instalado")


def _pdf_texto(caminho: Path, linhas):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for linha in linhas:
        page.insert_text((72, y), linha, fontsize=11)
        y += 18
    doc.set_metadata({"author": "Autor Verdadeiro", "title": "Pedro Henrique Alves"})
    doc.save(caminho)


@precisa_pdf
def test_pdf_tarja_remove_texto(tmp_path):
    f = tmp_path / "decisao.pdf"
    _pdf_texto(f, ["Requerente: Pedro Henrique Alves, CPF 529.982.247-25.",
                   "E-mail: pedro@exemplo.com.br", "Processo 0701234-93.2026.8.07.0001"])
    s = _rodar([f])
    assert not s.arquivos[0].erro, s.arquivos[0].erro
    out = fitz.open(s.arquivos[0].saida)
    texto = out[0].get_text()
    assert "Pedro" not in texto and "529.982" not in texto and "pedro@" not in texto
    assert "Requerente:" in texto  # o resto do texto continua lá
    assert "PESSOA_1" in texto  # código escrito sobre a tarja
    assert not (out.metadata or {}).get("author")


@precisa_pdf
def test_pdf_digitalizado_com_ocr(tmp_path):
    from anonimizador.formatos.ocr import localizar_tessdata
    if not localizar_tessdata("por"):
        pytest.skip("dados do Tesseract (por.traineddata) não encontrados")
    origem = fitz.open()
    pg = origem.new_page()
    pg.insert_text((60, 120), "Requerente: Pedro Henrique Alves", fontsize=20)
    pg.insert_text((60, 170), "CPF 529.982.247-25", fontsize=20)
    pix = pg.get_pixmap(dpi=200)
    img = tmp_path / "scan.png"
    pix.save(img)
    # PDF que é só imagem (como um documento escaneado)
    scan = fitz.open()
    p2 = scan.new_page(width=pg.rect.width, height=pg.rect.height)
    p2.insert_image(p2.rect, filename=str(img))
    f = tmp_path / "escaneado.pdf"
    scan.save(f)

    s = _rodar([f, img])
    for a in s.arquivos:
        assert not a.erro, a.erro
    out = fitz.open(s.arquivos[0].saida)
    pagina = out[0]  # manter a mesma referência da página para o textpage
    ocr = pagina.get_textpage_ocr(language="por", dpi=200, full=True,
                                  tessdata=localizar_tessdata("por"))
    texto = pagina.get_text(textpage=ocr)
    assert "529.982" not in texto and "Henrique" not in texto
    # o resto da página continua visível: há pixels escuros onde estava "Requerente:"
    trecho = pagina.get_pixmap(dpi=72, clip=fitz.Rect(60, 100, 150, 125))
    assert min(trecho.samples) < 100
    assert s.arquivos[1].saida.suffix == ".png"
