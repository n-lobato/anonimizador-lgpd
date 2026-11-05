"""Relatório em Excel com a tabela de-para (código -> dado original)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .deteccao.modelo import descricao

AVISO = ("ATENÇÃO: este arquivo contém os dados pessoais ORIGINAIS e permite desfazer a "
         "anonimização. Guarde-o em local protegido e não o envie junto com os documentos "
         "anonimizados.")


def gerar(sessao, pasta: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Leia-me"
    ws["A1"] = "Relatório de anonimização"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A3"] = AVISO
    ws["A3"].font = Font(bold=True, color="C00000")
    ws["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[3].height = 60
    ws.column_dimensions["A"].width = 100
    ws["A5"] = f"Gerado em {datetime.now():%d/%m/%Y %H:%M}"
    ws["A6"] = f"Arquivos processados: {sum(1 for a in sessao.arquivos if a.saida)}"
    ws["A7"] = ("Códigos: mesmos em todo o lote" if sessao.cfg.codigos_globais
                else "Códigos: numerados separadamente em cada arquivo")

    cab = PatternFill("solid", fgColor="1F3864")
    fonte_cab = Font(bold=True, color="FFFFFF")

    def cabecalho(planilha, titulos, larguras):
        planilha.append(titulos)
        for i, (c, largura) in enumerate(zip(planilha[1], larguras)):
            c.fill, c.font = cab, fonte_cab
            planilha.column_dimensions[c.column_letter].width = largura
        planilha.freeze_panes = "A2"

    ws2 = wb.create_sheet("De-para")
    cabecalho(ws2, ["Código", "Tipo", "Dado original", "Outras formas encontradas", "Ocorrências",
                    "Aplicado", "Origem", "Escopo"], [16, 22, 40, 50, 12, 10, 30, 40])
    for e in sessao.registro.ordenadas():
        outras = [v for v in e.variantes.values() if v != e.rotulo]
        ws2.append([e.codigo, descricao(e.tipo), e.rotulo, "; ".join(outras), e.total,
                    "sim" if e.ativo else "não", e.origem,
                    "todo o lote" if e.escopo == "*" else Path(e.escopo).name])

    ws3 = wb.create_sheet("Arquivos")
    cabecalho(ws3, ["Arquivo original", "Arquivo anonimizado", "Situação", "Avisos"], [60, 60, 14, 90])
    for a in sessao.arquivos:
        ws3.append([str(a.caminho), str(a.saida or ""), a.status,
                    " | ".join(a.avisos + ([a.erro] if a.erro else []))])
    for msg in sessao.ignorados:
        ws3.append([msg, "", "ignorado", ""])

    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"relatorio_anonimizacao_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    wb.save(destino)
    return destino
