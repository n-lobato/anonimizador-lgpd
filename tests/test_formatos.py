import os
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


def _docx_com_objeto_e_macro(tmp_path, macro: bool):
    """Monta um Word com uma planilha incorporada (e miniatura), um gráfico ligado a uma
    planilha de dados e, se pedido, macros, como o Word faz."""
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Requerente: Pedro Henrique Alves, CPF 529.982.247-25.")
    base = tmp_path / "base.docx"
    d.save(base)
    with zipfile.ZipFile(base) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    objeto = (
        '<w:p><w:r><w:object w:dxaOrig="1440" w:dyaOrig="1440">'
        '<v:shape id="_x0000_i1025" type="#_x0000_t75" style="width:72pt;height:72pt">'
        '<v:imagedata r:id="rIdPrev" o:title=""/></v:shape>'
        '<o:OLEObject Type="Embed" ProgID="Excel.Sheet.12" ShapeID="_x0000_i1025" '
        'DrawAspect="Content" ObjectID="_1" r:id="rIdOle"/></w:object></w:r></w:p>')
    doc = partes["word/document.xml"].decode()
    doc = doc.replace("<w:sectPr", objeto + "<w:sectPr", 1)
    for prefixo, ns in (("v", "urn:schemas-microsoft-com:vml"), ("o", "urn:schemas-microsoft-com:office:office")):
        if f"xmlns:{prefixo}=" not in doc:
            doc = doc.replace("<w:document ", f'<w:document xmlns:{prefixo}="{ns}" ', 1)
    partes["word/document.xml"] = doc.encode()
    rels = partes["word/_rels/document.xml.rels"].decode()
    extra = ('<Relationship Id="rIdPrev" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
             'relationships/image" Target="media/image9.emf"/>'
             '<Relationship Id="rIdOle" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
             'relationships/oleObject" Target="embeddings/Microsoft_Excel_Worksheet.xlsx"/>'
             '<Relationship Id="rIdChart" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
             'relationships/chart" Target="charts/chart1.xml"/>')
    if macro:
        extra += ('<Relationship Id="rIdVba" Type="http://schemas.microsoft.com/office/2006/relationships/'
                  'vbaProject" Target="vbaProject.bin"/>')
    partes["word/_rels/document.xml.rels"] = rels.replace("</Relationships>", extra + "</Relationships>").encode()
    partes["word/media/image9.emf"] = b"miniatura com o CPF 529.982.247-25"
    partes["word/embeddings/Microsoft_Excel_Worksheet.xlsx"] = b"Pedro Henrique Alves 529.982.247-25"
    partes["word/embeddings/Dados_do_grafico.xlsx"] = b"Pedro Henrique Alves 529.982.247-25"
    partes["word/charts/chart1.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<c:chart><c:plotArea><c:barChart><c:ser><c:cat><c:strRef><c:strCache><c:pt idx="0">'
        '<c:v>Pedro Henrique Alves</c:v></c:pt></c:strCache></c:strRef></c:cat></c:ser></c:barChart>'
        '</c:plotArea></c:chart><c:externalData r:id="rId1"/></c:chartSpace>').encode()
    partes["word/charts/_rels/chart1.xml.rels"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        'package" Target="../embeddings/Dados_do_grafico.xlsx"/></Relationships>').encode()
    ct = partes["[Content_Types].xml"].decode()
    ct_extra = ('<Default Extension="emf" ContentType="image/x-emf"/>'
                '<Override PartName="/word/embeddings/Microsoft_Excel_Worksheet.xlsx" ContentType="application/'
                'vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>'
                '<Override PartName="/word/charts/chart1.xml" ContentType="application/'
                'vnd.openxmlformats-officedocument.drawingml.chart+xml"/>')
    if macro:
        partes["word/vbaProject.bin"] = b"Sub Teste() ' Pedro Henrique Alves"
        ct_extra += '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>'
        ct = ct.replace("wordprocessingml.document.main+xml", "ms-word.document.macroEnabled.main+xml")
    partes["[Content_Types].xml"] = ct.replace("</Types>", ct_extra + "</Types>").encode()
    f = tmp_path / ("caso.docm" if macro else "caso.docx")
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        for n, dados in partes.items():
            z.writestr(n, dados)
    return f


@pytest.mark.parametrize("macro", [False, True])
def test_docx_remove_objetos_incorporados_e_macros(tmp_path, macro):
    docx = pytest.importorskip("docx")
    f = _docx_com_objeto_e_macro(tmp_path, macro)
    s = _rodar([f])
    a = s.arquivos[0]
    assert not a.erro and a.saida.suffix == ".docx"
    with zipfile.ZipFile(a.saida) as z:
        nomes = z.namelist()
        tudo = b"".join(z.read(n) for n in nomes)
        ct = z.read("[Content_Types].xml").decode()
        rels = z.read("word/_rels/document.xml.rels").decode()
        grafico = z.read("word/charts/chart1.xml").decode()
    assert not any(n.startswith("word/embeddings/") for n in nomes)
    assert "word/media/image9.emf" not in nomes  # miniatura do objeto
    assert "word/vbaProject.bin" not in nomes
    assert b"529.982.247-25" not in tudo and b"Pedro" not in tudo
    assert "rIdOle" not in rels and "rIdPrev" not in rels and "vbaProject" not in rels
    assert "macroEnabled" not in ct and "embeddings" not in ct and 'Extension="bin"' not in ct
    assert "externalData" not in grafico and "[PESSOA_1]" in grafico
    out = docx.Document(a.saida)  # o arquivo continua abrindo
    textos = [p.text for p in out.paragraphs]
    assert "Requerente: [PESSOA_1], CPF [CPF_1]." in textos
    assert any("[objeto incorporado removido]" in t for t in textos)
    assert any("REMOVIDO" in av or "removido" in av for av in a.avisos)


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


def test_xlsx_formulas_links_e_cabecalho(tmp_path):
    """Textos dentro de fórmulas, links e cabeçalhos também são dados pessoais."""
    from openpyxl import Workbook, load_workbook
    wb = Workbook()
    ws = wb.active
    ws["A1"] = '=CONCATENATE("Requerente: Lucas Ferreira Gomes", " - fim")'
    ws["A2"] = '=IF(B1>0,"CPF 529.982.247-25","")'
    ws["A3"] = "contato"
    ws["A3"].hyperlink = "mailto:lucas.gomes@exemplo.com.br"
    ws["A4"] = "=SUM(1,2)"
    ws.oddHeader.center.text = "Processo de Lucas Ferreira Gomes"
    f = tmp_path / "formulas.xlsx"
    wb.save(f)
    s = _rodar([f])
    ws2 = load_workbook(s.arquivos[0].saida).active
    tudo = " ".join(str(ws2[c].value) for c in ("A1", "A2", "A4"))
    assert "Lucas" not in tudo and "529.982" not in tudo
    assert ws2["A1"].value.startswith('=CONCATENATE("Requerente: [PESSOA_1]"')
    assert ws2["A2"].value == '=IF(B1>0,"CPF [CPF_1]","")'
    assert ws2["A4"].value == "=SUM(1,2)"
    assert "lucas" not in ws2["A3"].hyperlink.target.lower()
    assert "Lucas" not in ws2.oddHeader.center.text


def _xlsx_com_vinculo_dinamica_e_macro(tmp_path, macro: bool):
    """Planilha com uma fórmula ligada a outra pasta de trabalho, uma tabela dinâmica com
    cache, um objeto incorporado e, se pedido, macros, como o Excel grava."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan1"
    ws["A1"] = "Nome"
    ws["A2"] = "Valor"
    ws["B2"] = 10
    base = tmp_path / "base.xlsx"
    wb.save(base)
    with zipfile.ZipFile(base) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    folha = partes["xl/worksheets/sheet1.xml"].decode()
    folha = folha.replace("</sheetData>",
                          '<row r="5"><c r="A5" t="str"><f>[1]Cadastro!A1</f><v>Pedro Henrique Alves</v></c>'
                          '</row></sheetData>', 1)
    partes["xl/worksheets/sheet1.xml"] = folha.encode()
    partes["xl/externalLinks/externalLink1.xml"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<externalLink xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="{r}">'
        '<externalBook r:id="rId1"><sheetNames><sheetName val="Cadastro"/></sheetNames><sheetDataSet>'
        '<sheetData sheetId="0"><row r="1"><cell r="A1" t="str"><v>Pedro Henrique Alves</v></cell>'
        '<cell r="B1" t="str"><v>529.982.247-25</v></cell></row></sheetData></sheetDataSet>'
        '</externalBook></externalLink>').encode()
    partes["xl/externalLinks/_rels/externalLink1.xml.rels"] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{r}/externalLinkPath" '
        'Target="file:///C:/Users/pedro.alves/cadastro.xlsx" TargetMode="External"/></Relationships>').encode()
    partes["xl/pivotCache/pivotCacheRecords1.xml"] = b"<pivotCacheRecords>Pedro Henrique Alves</pivotCacheRecords>"
    partes["xl/embeddings/oleObject1.bin"] = b"Pedro Henrique Alves 529.982.247-25"
    livro = partes["xl/workbook.xml"].decode()
    if "xmlns:r=" not in livro.split(">", 1)[0]:  # o openpyxl declara o "r" só em cada <sheet>
        livro = livro.replace("<workbook ", f'<workbook xmlns:r="{r}" ', 1)
    livro = livro.replace("</sheets>", '</sheets><externalReferences><externalReference r:id="rIdExt"/>'
                          "</externalReferences>", 1)
    partes["xl/workbook.xml"] = livro.encode()
    rels = partes["xl/_rels/workbook.xml.rels"].decode()
    extra = f'<Relationship Id="rIdExt" Type="{r}/externalLink" Target="externalLinks/externalLink1.xml"/>'
    if macro:
        extra += ('<Relationship Id="rIdVba" Type="http://schemas.microsoft.com/office/2006/relationships/'
                  'vbaProject" Target="vbaProject.bin"/>')
    partes["xl/_rels/workbook.xml.rels"] = rels.replace("</Relationships>", extra + "</Relationships>").encode()
    ct = partes["[Content_Types].xml"].decode()
    ct_extra = ('<Override PartName="/xl/externalLinks/externalLink1.xml" ContentType="application/'
                'vnd.openxmlformats-officedocument.spreadsheetml.externalLink+xml"/>')
    if macro:
        partes["xl/vbaProject.bin"] = b"Sub Teste() ' Pedro Henrique Alves"
        ct_extra += '<Default Extension="bin" ContentType="application/vnd.ms-office.vbaProject"/>'
        ct = ct.replace("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
                        "application/vnd.ms-excel.sheet.macroEnabled.main+xml")
    partes["[Content_Types].xml"] = ct.replace("</Types>", ct_extra + "</Types>").encode()
    f = tmp_path / ("cadastro.xlsm" if macro else "cadastro.xlsx")
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        for n, dados in partes.items():
            z.writestr(n, dados)
    return f


@pytest.mark.parametrize("macro", [False, True])
def test_xlsx_remove_vinculos_caches_objetos_e_macros(tmp_path, macro):
    from openpyxl import load_workbook
    f = _xlsx_com_vinculo_dinamica_e_macro(tmp_path, macro)
    s = _rodar([f])
    a = s.arquivos[0]
    assert not a.erro and a.saida.suffix == ".xlsx"
    with zipfile.ZipFile(a.saida) as z:
        nomes = z.namelist()
        tudo = b"".join(z.read(n) for n in nomes)
    assert not any(n.startswith(("xl/externalLinks/", "xl/pivotCache/", "xl/embeddings/")) for n in nomes)
    assert "xl/vbaProject.bin" not in nomes
    assert b"Pedro" not in tudo and b"529.982" not in tudo and b"pedro.alves" not in tudo
    assert b"macroEnabled" not in tudo
    ws = load_workbook(a.saida).active
    assert ws["A5"].value == "[PESSOA_1]"  # a fórmula ligada à outra planilha virou o valor, anonimizado
    assert ws["B2"].value == 10
    assert any("valor salvo" in av for av in a.avisos)


def test_formula_aspas_escapadas():
    from anonimizador.formatos.planilha import literais, substituir_formula

    class Sub:
        def substituir(self, t):
            return t.replace('Ana "Tita" Souza', "[PESSOA_1]")
    f = '="Sra. Ana ""Tita"" Souza"&A1'
    assert literais(f) == ['Sra. Ana "Tita" Souza']
    assert substituir_formula(f, Sub()) == '="Sra. [PESSOA_1]"&A1'


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



def test_relatorio_fica_fora_da_pasta_de_saida(tmp_path, peticao):
    """Quem compacta a pasta "anonimizados" para enviar não pode levar o de-para junto."""
    from anonimizador.processador import PASTA_RELATORIO
    from anonimizador.relatorio import gerar
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "p.txt").write_text(peticao, encoding="utf-8")
    s = _rodar([docs])
    saida = s.arquivos[0].saida.parent
    rel = gerar(s, s.pasta_relatorio())
    assert rel.parent == (docs / PASTA_RELATORIO).resolve()
    assert saida.resolve() not in rel.parents
    # a pasta do relatório não entra numa nova rodada sobre a mesma pasta
    arquivos, _ = listar_arquivos([docs])
    assert [a.caminho.name for a in arquivos] == ["p.txt"]


def test_relatorio_com_saida_acima_dos_originais(tmp_path, peticao):
    from anonimizador.config import pasta_config
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "p.txt").write_text(peticao, encoding="utf-8")
    s = _rodar([docs], pasta_saida=str(tmp_path))
    destino = s.pasta_relatorio()
    assert destino == pasta_config() / "relatorios"


def test_relatorio_nao_vira_formula(tmp_path):
    from openpyxl import Workbook, load_workbook

    from anonimizador.relatorio import _como_texto
    wb = Workbook()
    wb.active.append(["=HYPERLINK(\"http://exemplo.invalid\",\"clique\")", "ok"])
    _como_texto(wb.active)
    f = tmp_path / "r.xlsx"
    wb.save(f)
    with zipfile.ZipFile(f) as z:
        assert "<f>" not in z.read("xl/worksheets/sheet1.xml").decode()
    assert load_workbook(f).active["A1"].value.startswith("=HYPERLINK")


def test_relatorio_desligado_por_padrao_e_migracao(tmp_path):
    import json

    from anonimizador import config
    assert Configuracao().gerar_relatorio is False
    arq = config.pasta_config() / "config.json"
    arq.write_text(json.dumps({"gerar_relatorio": True, "ocr": False}), encoding="utf-8")
    cfg = config.carregar_config()
    assert cfg.gerar_relatorio is False and cfg.ocr is False and config.MIGROU_RELATORIO
    config.salvar_config(cfg)
    cfg.gerar_relatorio = True
    config.salvar_config(cfg)
    assert config.carregar_config().gerar_relatorio is True  # escolha feita depois é respeitada


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


@precisa_pdf
def test_pdf_nao_sobra_dado_em_nenhum_lugar_do_arquivo(tmp_path):
    """Varre o PDF anonimizado inteiro: conteúdo, texto invisível, anotações e metadados."""
    nome, cpf = "Pedro Henrique Alves", "529.982.247-25"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"Requerente: {nome}, CPF {cpf}.", fontsize=11)
    # camada de texto invisível, como a que scanners com OCR gravam sobre a imagem
    page.insert_text((72, 120), f"Testemunha: {nome}", fontsize=11, render_mode=3)
    nota = page.add_text_annot((300, 300), f"Conferir com {nome}")
    nota.set_info(title="Autor Verdadeiro")
    nota.update()
    doc.set_metadata({"author": "Autor Verdadeiro", "title": nome, "subject": cpf,
                      "keywords": nome, "creator": "Autor Verdadeiro"})
    doc.set_xml_metadata(f"<x:xmpmeta xmlns:x='adobe:ns:meta/'><dc>{nome}</dc></x:xmpmeta>")
    doc.set_toc([[1, f"Depoimento de {nome}", 1]])
    f = tmp_path / "completo.pdf"
    doc.save(f)

    s = _rodar([f])
    assert not s.arquivos[0].erro, s.arquivos[0].erro
    out = fitz.open(s.arquivos[0].saida)

    texto = "".join(p.get_text() for p in out)
    assert "Pedro" not in texto and "529.982" not in texto
    assert texto.count("Requerente:") == 1 and "Testemunha:" in texto

    meta = out.metadata or {}
    for campo in ("author", "title", "subject", "keywords", "creator"):
        assert "Pedro" not in (meta.get(campo) or "") and "Autor Verdadeiro" not in (meta.get(campo) or "")
    assert "Pedro" not in (out.get_xml_metadata() or "")
    assert all("Pedro" not in t[1] for t in out.get_toc())
    for annot in out[0].annots() or []:
        info = annot.info
        assert "Pedro" not in info.get("content", "") and "Autor Verdadeiro" not in info.get("title", "")

    # nenhum objeto ou fluxo do arquivo (já descomprimido) pode conter o dado
    for xref in range(1, out.xref_length()):
        objeto = out.xref_object(xref, compressed=False) or ""
        assert "Pedro" not in objeto and "529.982" not in objeto, objeto[:200]
        if out.xref_is_stream(xref):
            dados = out.xref_stream(xref) or b""
            assert b"Pedro" not in dados and b"529.982" not in dados


@precisa_pdf
def test_pdf_nome_que_so_aparece_em_comentario(tmp_path):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Decisão sobre o pedido de vista.", fontsize=11)
    nota = page.add_text_annot((300, 300), "Requerente: Kauã Ribeiro, CPF 529.982.247-25")
    nota.update()
    f = tmp_path / "comentario.pdf"
    doc.save(f)
    s = _rodar([f])
    assert not s.arquivos[0].erro, s.arquivos[0].erro
    out = fitz.open(s.arquivos[0].saida)
    conteudos = [a.info.get("content", "") for a in out[0].annots() or []]
    assert conteudos and all("Kauã" not in c and "529.982" not in c for c in conteudos)


@precisa_pdf
def test_pdf_nome_quebrado_entre_linhas_recebe_tarja(tmp_path):
    f = tmp_path / "quebrado.pdf"
    _pdf_texto(f, ["Foram eleitos para o conselho fiscal os condôminos Ubiratan",
                   "Silveira e Thaís Regina Prado, com mandato de dois anos."])
    s = _rodar([f])
    assert not s.arquivos[0].erro, s.arquivos[0].erro
    texto = fitz.open(s.arquivos[0].saida)[0].get_text()
    assert "Ubiratan" not in texto and "Silveira" not in texto and "Thaís" not in texto
    assert "conselho fiscal" in texto


# ------------------------------------------------- imagens coladas no Word e no Excel
def _png_simples() -> bytes:
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), "white").save(buf, format="PNG")
    return buf.getvalue()


def _jpeg_com_gps() -> bytes:
    import io

    from PIL import Image
    im = Image.new("RGB", (60, 40), "white")
    exif = Image.Exif()
    exif[0x010F] = "Fabricante"  # Make
    exif[0x8825] = {1: "S", 2: (15.0, 47.0, 0.0)}  # GPSInfo: latitude de Brasília
    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif.tobytes())
    return buf.getvalue()


def _imagem_com_cpf() -> bytes:
    """Foto de documento: texto com nome e CPF desenhado como pixels (precisa do PyMuPDF)."""
    pg = fitz.open().new_page(width=420, height=140)
    pg.insert_text((20, 50), "Requerente: Pedro Henrique Alves", fontsize=18)
    pg.insert_text((20, 95), "CPF 529.982.247-25", fontsize=18)
    return pg.get_pixmap(dpi=200).tobytes("png")


def _ocr_disponivel():
    from anonimizador.formatos.ocr import localizar_tessdata
    if fitz is None or not localizar_tessdata("por"):
        pytest.skip("OCR indisponível (PyMuPDF ou por.traineddata)")


def _ler_com_ocr(dados: bytes, tmp_path) -> str:
    from anonimizador.formatos import Opcoes, imagem
    arq = tmp_path / "conferir.png"
    arq.write_bytes(dados)
    return imagem.extrair(str(arq), Opcoes()).texto


def test_docx_imagem_com_cpf_recebe_tarja(tmp_path):
    _ocr_disponivel()
    import io
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Segue cópia do documento.")
    d.add_picture(io.BytesIO(_imagem_com_cpf()))
    f = tmp_path / "com_foto.docx"
    d.save(f)
    s = _rodar([f])
    a = s.arquivos[0]
    assert not a.erro, a.erro
    with zipfile.ZipFile(a.saida) as z:
        midia = [n for n in z.namelist() if n.startswith("word/media/")]
        assert len(midia) == 1
        texto = _ler_com_ocr(z.read(midia[0]), tmp_path)
    assert "529.982" not in texto and "Henrique" not in texto
    assert any("recebeu(ram) tarja" in av and "; 1 " in av for av in a.avisos)


def test_xlsx_imagem_com_cpf_recebe_tarja(tmp_path):
    _ocr_disponivel()
    import io

    from openpyxl import Workbook, load_workbook
    from openpyxl.drawing.image import Image as ImagemXL
    wb = Workbook()
    wb.active["A1"] = "Documento anexo"
    wb.active.add_image(ImagemXL(io.BytesIO(_imagem_com_cpf())), "B2")
    f = tmp_path / "com_foto.xlsx"
    wb.save(f)
    s = _rodar([f])
    a = s.arquivos[0]
    assert not a.erro, a.erro
    imgs = load_workbook(a.saida).active._images
    assert len(imgs) == 1
    texto = _ler_com_ocr(imgs[0]._data(), tmp_path)
    assert "529.982" not in texto and "Henrique" not in texto


def test_docx_e_xlsx_remover_imagens(tmp_path):
    import io
    docx = pytest.importorskip("docx")
    from openpyxl import Workbook, load_workbook
    from openpyxl.drawing.image import Image as ImagemXL
    d = docx.Document()
    d.add_paragraph("Antes da foto.")
    d.add_picture(io.BytesIO(_png_simples()))
    d.sections[0].header.paragraphs[0].add_run().add_picture(io.BytesIO(_png_simples()))
    fd = tmp_path / "fotos.docx"
    d.save(fd)
    wb = Workbook()
    wb.active.add_image(ImagemXL(io.BytesIO(_png_simples())), "A1")
    fx = tmp_path / "fotos.xlsx"
    wb.save(fx)

    s = _rodar([fd, fx], remover_imagens=True)
    for a in s.arquivos:
        assert not a.erro, a.erro
        assert any("removida(s) da cópia" in av for av in a.avisos)
    with zipfile.ZipFile(s.arquivos[0].saida) as z:
        assert not any(n.startswith("word/media/") for n in z.namelist())
        assert "media/" not in z.read("word/_rels/document.xml.rels").decode()
    out = docx.Document(s.arquivos[0].saida)
    assert any("[imagem removida]" in p.text for p in out.paragraphs)
    assert "[imagem removida]" in out.sections[0].header.paragraphs[0].text
    assert load_workbook(s.arquivos[1].saida).active._images == []


def test_imagem_sem_dados_perde_so_os_metadados(tmp_path):
    """Foto de celular colada no Word pode levar a localização GPS no EXIF."""
    import io
    docx = pytest.importorskip("docx")
    from PIL import Image
    d = docx.Document()
    d.add_paragraph("Foto do local.")
    d.add_picture(io.BytesIO(_jpeg_com_gps()))
    f = tmp_path / "foto_gps.docx"
    d.save(f)
    s = _rodar([f], ocr=False)  # mesmo sem OCR, os metadados saem
    a = s.arquivos[0]
    assert not a.erro, a.erro
    with zipfile.ZipFile(a.saida) as z:
        midia = [n for n in z.namelist() if n.startswith("word/media/")]
        with Image.open(io.BytesIO(z.read(midia[0]))) as im:
            assert not im.getexif() and im.size == (60, 40)
    assert any("OCR está desligado" in av for av in a.avisos)


def _limpar_caches_ocr():
    from anonimizador.formatos import ocr, pdf
    ocr._SEGUROS.clear()
    pdf._MOTOR_OK.clear()


@pytest.mark.skipif(os.name != "nt", reason="o problema do caminho com acento é só do Windows")
def test_ocr_funciona_em_pasta_com_acento(tmp_path, monkeypatch):
    """O Tesseract do Windows não abria os dados de idioma em caminho com acento (ex.:
    "Área de Trabalho"): o OCR voltava vazio, sem erro."""
    _ocr_disponivel()
    import shutil

    from anonimizador.formatos import Opcoes, imagem
    from anonimizador.formatos.ocr import localizar_tessdata
    original = localizar_tessdata("por")
    pasta = tmp_path / "Área de Trabalho" / "tessdata"
    pasta.mkdir(parents=True)
    for f in Path(original).glob("*.traineddata"):
        shutil.copy2(f, pasta)
    monkeypatch.setenv("TESSDATA_PREFIX", str(pasta))
    _limpar_caches_ocr()
    try:
        assert localizar_tessdata("por").isascii()
        arq = tmp_path / "doc.png"
        arq.write_bytes(_imagem_com_cpf())
        assert "529.982" in imagem.extrair(str(arq), Opcoes()).texto.replace(" ", "")
    finally:
        _limpar_caches_ocr()


def test_ocr_que_nao_carrega_o_idioma_avisa(tmp_path, monkeypatch):
    """Se o motor não consegue ler, o programa avisa em vez de dizer que não achou nada."""
    _ocr_disponivel()
    import io
    docx = pytest.importorskip("docx")
    pasta = tmp_path / "tessdata_quebrado"
    pasta.mkdir()
    (pasta / "por.traineddata").write_bytes(b"isto nao e um modelo do tesseract")
    monkeypatch.setenv("TESSDATA_PREFIX", str(pasta))
    _limpar_caches_ocr()
    try:
        d = docx.Document()
        d.add_picture(io.BytesIO(_imagem_com_cpf()))
        f = tmp_path / "foto.docx"
        d.save(f)
        s = _rodar([f])
        avisos = " ".join(s.arquivos[0].avisos)
        assert "NÃO puderam ser lidas" in avisos and "não conseguiu carregar" in avisos
    finally:
        _limpar_caches_ocr()


def test_imagem_pequena_e_ampliada_para_o_ocr(tmp_path):
    from PIL import Image

    from anonimizador.formatos.imagem import _ampliada
    pequena, grande = tmp_path / "p.png", tmp_path / "g.png"
    Image.new("RGBA", (587, 529), (255, 255, 255, 0)).save(pequena)
    Image.new("RGB", (2000, 1000), "white").save(grande)
    import io
    with Image.open(io.BytesIO(_ampliada(str(pequena)))) as im:
        assert im.size == (587 * 3, 529 * 3) and im.mode == "RGB"
    assert _ampliada(str(grande)) is None
