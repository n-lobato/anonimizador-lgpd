"""Mede o anonimizador em PDF digitalizado (só imagem), usando o corpus de teste.

Uso:
    python build/avaliar_ocr.py                 # resumo
    python build/avaliar_ocr.py --detalhes      # lista cada dado que continuou legível
    python build/avaliar_ocr.py --dpi 150       # digitalização em resolução menor

Para cada documento do corpus:
1. o texto é impresso num PDF e cada página vira uma imagem (como um escaneado limpo);
2. o PDF passa pelo programa do jeito normal: OCR, detecção e tarja nos pixels;
3. o resultado é lido de novo com OCR, para ver o que ainda dá para ler.

Um dado conta como "coberto" quando nenhuma das suas partes (palavras do nome,
números) aparece na leitura do arquivo anonimizado. Partes que o OCR não
conseguiu ler nem no original ficam de fora da conta e são informadas à parte.

Limitações: a digitalização é perfeita (sem sujeira, inclinação ou carimbo),
então documentos reais tendem a dar resultado pior. E o que o OCR não lê no
resultado pode, mesmo assim, estar legível para uma pessoa.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "build"))

import avaliar  # noqa: E402
from anonimizador.config import Configuracao, Termos  # noqa: E402
from anonimizador.deteccao.dados_nomes import PALAVRAS_COMUNS, PARTICULAS  # noqa: E402
from anonimizador.formatos.ocr import localizar_tessdata  # noqa: E402
from anonimizador.formatos.pdf import fitz  # noqa: E402
from anonimizador.processador import Sessao  # noqa: E402
from anonimizador.texto import normalizar  # noqa: E402

LINHAS_POR_PAGINA = 50
COLUNAS = 92


def imprimir_como_escaneado(texto: str, destino: Path, dpi: int) -> None:
    f = fitz()
    linhas = []
    for par in texto.split("\n"):
        linhas += textwrap.wrap(par, COLUNAS) or [""]
    impresso = f.open()
    for i in range(0, len(linhas), LINHAS_POR_PAGINA):
        pg = impresso.new_page()  # A4
        y = 60
        for linha in linhas[i:i + LINHAS_POR_PAGINA]:
            pg.insert_text((50, y), linha, fontsize=10.5, fontname="helv")
            y += 14.5
    escaneado = f.open()
    for pg in impresso:
        pix = pg.get_pixmap(dpi=dpi)
        nova = escaneado.new_page(width=pg.rect.width, height=pg.rect.height)
        nova.insert_image(nova.rect, stream=pix.tobytes("png"))
    escaneado.save(destino)


def ler_com_ocr(caminho: Path) -> str:
    f = fitz()
    pasta = localizar_tessdata("por")
    doc = f.open(caminho)
    partes = []
    for pg in doc:
        tp = pg.get_textpage_ocr(language="por", dpi=300, full=True, tessdata=pasta)
        partes.append(pg.get_text(textpage=tp))
    doc.close()
    return "\n".join(partes)


def partes_do_dado(m: avaliar.Marcado) -> list[str]:
    """Pedaços que, se ainda legíveis, indicam vazamento: palavras do nome e números."""
    n = normalizar(m.texto)
    partes = []
    digitos = re.sub(r"\D", "", n)
    if len(digitos) >= 5:
        partes.append("#" + digitos)
    for w in re.findall(r"[a-z0-9]+", n):
        if w.isdigit():
            if len(digitos) < 5 and len(w) >= 3:
                partes.append(w)
            continue
        if len(w) >= 3 and w not in PARTICULAS and (m.tipo == "PESSOA" or w not in PALAVRAS_COMUNS):
            partes.append(w)
    return partes


def presente(parte: str, texto_norm: str, so_digitos: str) -> bool:
    if parte.startswith("#"):
        return parte[1:] in so_digitos
    return re.search(r"(?<![a-z0-9])" + re.escape(parte) + r"(?![a-z0-9])", texto_norm) is not None


def avaliar_documento(caminho: Path, dpi: int):
    texto, marcados = avaliar.ler_marcado(caminho.read_bytes().decode("utf-8").replace("\r\n", "\n"))
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / (caminho.stem + ".pdf")
        imprimir_como_escaneado(texto, pdf, dpi)
        sessao = Sessao(Configuracao(gerar_relatorio=False), Termos())
        sessao.carregar([pdf])
        sessao.analisar()
        sessao.aplicar()
        arq = sessao.arquivos[0]
        if arq.erro:
            raise RuntimeError(f"{caminho.name}: {arq.erro}")
        lido_antes = normalizar(arq.texto)
        lido_depois = normalizar(ler_com_ocr(arq.saida))
    dig_antes, dig_depois = re.sub(r"\D", "", lido_antes), re.sub(r"\D", "", lido_depois)
    resultados = []
    for m in marcados:
        if m.opcional:
            continue
        partes = partes_do_dado(m)
        legiveis = [p for p in partes if presente(p, lido_antes, dig_antes)]
        sobrou = [p for p in legiveis if presente(p, lido_depois, dig_depois)]
        if not legiveis:
            status = "ilegível no original"
        elif not sobrou:
            status = "coberto"
        elif len(sobrou) == len(legiveis):
            status = "vazou"
        else:
            status = "parcial"
        resultados.append((caminho.name, m, status, sobrou))
    return resultados


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grupo", choices=["desenvolvimento", "validacao"])
    ap.add_argument("--detalhes", action="store_true")
    ap.add_argument("--dpi", type=int, default=200, help="resolução da digitalização simulada (padrão 200)")
    args = ap.parse_args(argv)
    if not localizar_tessdata("por"):
        print("Dados do OCR em português não encontrados (rode build/baixar_tessdata.py).")
        return 1
    grupos = [args.grupo] if args.grupo else ["desenvolvimento", "validacao"]
    for grupo in grupos:
        resultados = []
        for f in sorted((avaliar.CORPUS / grupo).glob("*.txt")):
            resultados += avaliar_documento(f, args.dpi)
        por_tipo: dict[str, Counter] = defaultdict(Counter)
        for _, m, status, _ in resultados:
            por_tipo[m.tipo][status] += 1
        print(f"\n=== {grupo} (PDF digitalizado a {args.dpi} dpi) ===")
        print(f"{'Tipo':<16}{'Total':>6}{'Coberto':>9}{'Parcial':>9}{'Vazou':>7}{'Ilegível':>10}{'Acerto':>8}")
        tot = Counter()
        for tipo in sorted(por_tipo, key=lambda t: (t != "PESSOA", t)):
            c = por_tipo[tipo]
            n = c["coberto"] + c["parcial"] + c["vazou"]
            print(f"{tipo:<16}{n:>6}{c['coberto']:>9}{c['parcial']:>9}{c['vazou']:>7}"
                  f"{c['ilegível no original']:>10}{avaliar.pct(c['coberto'], n):>8}")
            tot.update(c)
        n = tot["coberto"] + tot["parcial"] + tot["vazou"]
        print(f"{'TOTAL':<16}{n:>6}{tot['coberto']:>9}{tot['parcial']:>9}{tot['vazou']:>7}"
              f"{tot['ilegível no original']:>10}{avaliar.pct(tot['coberto'], n):>8}")
        if args.detalhes:
            for arq, m, status, sobrou in resultados:
                if status != "coberto":
                    print(f"  [{status}] {arq}: {m.tipo} '{m.texto}'" + (f" -> legível: {sobrou}" if sobrou else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
