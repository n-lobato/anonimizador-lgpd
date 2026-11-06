"""Gera documentos de exemplo com dados FICTÍCIOS para testar o programa."""
from pathlib import Path

import docx
import pymupdf

pasta = Path(__file__).resolve().parents[1] / "exemplos"
pasta.mkdir(exist_ok=True)
for antigo in pasta.glob("*"):
    if antigo.is_file():
        antigo.unlink()

d = docx.Document()
d.core_properties.author = "Autor Fictício"
d.add_heading("EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA 2ª VARA CÍVEL DE BRASÍLIA/DF", 2)
d.add_paragraph("Processo nº 0701234-93.2026.8.07.0001")
p = d.add_paragraph()
p.add_run("MARIA APARECIDA DE SOUZA SANTOS").bold = True
p.add_run(", brasileira, casada, portadora da Carteira de Identidade nº 1.234.567 SSP/DF, inscrita no CPF "
          "sob o nº 529.982.247-25, residente e domiciliada na SQS 308, Bloco C, Apto 101, Asa Sul, "
          "Brasília/DF, CEP 70355-030, telefone (61) 99876-5432, e-mail maria.souza@exemplo.com.br, vem, "
          "por seu advogado, Dr. Thalysson Rodrigues Pereira, OAB/DF nº 45.678, propor a presente AÇÃO DE "
          "INDENIZAÇÃO em face de José Carlos da Silva Filho, nascido em 12/03/1980.")
d.add_paragraph("A testemunha Kauã Ribeiro confirmou que Maria estava no local. Aplica-se a Lei Maria da Penha.")
t = d.add_table(rows=2, cols=2)
t.style = "Table Grid"
t.cell(0, 0).text, t.cell(0, 1).text = "Parte", "Nome"
t.cell(1, 0).text, t.cell(1, 1).text = "Réu", "José Carlos da Silva Filho"
d.add_paragraph("Brasília, 5 de novembro de 2026.")
d.add_paragraph("Thalysson Rodrigues Pereira\nOAB/DF 45.678")
d.sections[0].header.paragraphs[0].text = "Autos 0701234-93.2026.8.07.0001 | Maria Aparecida de Souza Santos"
d.save(pasta / "peticao_exemplo.docx")

doc = pymupdf.open()
pg = doc.new_page()
y = 72
linhas = ["CERTIDÃO", "",
          "Certifico que ENZO GABRIEL ALMEIDA COSTA, nascido em 01/02/2019,",
          "filho de CARLOS EDUARDO COSTA e PATRÍCIA ALMEIDA COSTA, CPF 111.444.777-35,",
          "reside na Rua das Palmeiras, nº 45, Taguatinga Norte. Dou fé.", "",
          "Escrevente: Lúcia Helena Barros"]
for linha in linhas:
    pg.insert_text((60, y), linha, fontsize=11)
    y += 18
doc.set_metadata({"author": "Cartório Fictício", "title": "Certidão de Enzo Gabriel Almeida Costa"})
doc.save(pasta / "certidao_exemplo.pdf")

# versão "escaneada": a mesma certidão como imagem, para testar o OCR
pix = pg.get_pixmap(dpi=200)
img = pasta / "_tmp.png"
pix.save(img)
scan = pymupdf.open()
p2 = scan.new_page(width=pg.rect.width, height=pg.rect.height)
p2.insert_image(p2.rect, filename=str(img))
scan.save(pasta / "certidao_escaneada_exemplo.pdf")
img.unlink()

(pasta / "transcricao_exemplo.txt").write_text(
    "TERMO DE AUDIÊNCIA\n"
    "Presentes o MM. Juiz Dr. Fernando Augusto Lima e o réu JEFFERSON DA SILVA PRADO, "
    "assistido pela Defensora Pública Dra. Camila Nogueira.\n"
    "Testemunha: Valdirene Rocha (RG 2.345.678 SSP/GO).\n"
    "DEFENSORA: A senhora viu o acusado?\n"
    "VALDIRENE: Vi sim, doutora. Ele estava com o Toninho.\n", encoding="utf-8")
print("Exemplos gerados em", pasta)
