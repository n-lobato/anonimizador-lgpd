"""Testa o programa já empacotado, do jeito que o usuário recebe (Windows, Mac ou Linux).

Uso:
    python build/testar_pacote.py preparar PASTA
        Cria os arquivos de amostra (precisa do PyMuPDF; roda no ambiente de build).
    python build/testar_pacote.py conferir CAMINHO_DA_CLI PASTA [--janela CAMINHO_DA_JANELA]
        Usa só a biblioteca padrão do Python, para rodar também numa máquina limpa.

O que "conferir" verifica:
1. A versão empacotada encontra o CPF e o nome no texto, no PDF com texto e no
   PDF digitalizado (este último prova que o OCR está funcionando no pacote).
2. Depois de anonimizar, uma nova análise dos arquivos gerados não acha mais o
   CPF em nenhum deles, nem o nome no texto.
3. Com --janela, a janela abre e continua aberta por alguns segundos.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

NOME = "Pedro Henrique Alves"
CPF = "529.982.247-25"
FRASE = f"Requerente: {NOME}, brasileiro, inscrito no CPF sob o nº {CPF}, residente em Brasília."
ARQUIVOS = ("teste.txt", "documento.pdf", "escaneado.pdf")


def preparar(pasta: Path) -> None:
    import pymupdf

    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "teste.txt").write_text(FRASE + "\n", encoding="utf-8")
    doc = pymupdf.open()
    pg = doc.new_page()
    pg.insert_textbox(pymupdf.Rect(60, 80, 540, 300), FRASE, fontsize=12, fontname="helv")
    doc.save(pasta / "documento.pdf")
    # digitalizado: a mesma página vira uma imagem, sem nenhum texto por baixo
    pix = pg.get_pixmap(dpi=200)
    escaneado = pymupdf.open()
    nova = escaneado.new_page(width=pg.rect.width, height=pg.rect.height)
    nova.insert_image(nova.rect, pixmap=pix)
    escaneado.save(pasta / "escaneado.pdf")
    print("Amostras criadas em", pasta)


def rodar(cli: Path, *args: str) -> str:
    r = subprocess.run([str(cli), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    print(f"$ {cli.name} {' '.join(args)}  -> código {r.returncode}")
    print(r.stdout[-3000:])
    if r.stderr.strip():
        print("stderr:", r.stderr[-2000:])
    if r.returncode not in (0,):
        raise SystemExit(f"FALHOU: a CLI terminou com código {r.returncode}")
    return r.stdout


def achados(saida: str, tipo: str) -> int:
    return len(re.findall(rf"^\s+{tipo}_\d+\s", saida, flags=re.M))


def conferir(cli: Path, pasta: Path, janela: Path | None) -> None:
    cli = cli.resolve()
    if not cli.is_file():
        raise SystemExit(f"CLI não encontrada: {cli}")
    trabalho = pasta.resolve().parent / (pasta.name + "_teste")
    shutil.rmtree(trabalho, ignore_errors=True)
    shutil.copytree(pasta, trabalho)
    saida = trabalho / "anonimizados"

    for nome in ARQUIVOS:
        txt = rodar(cli, "--apenas-analisar", str(trabalho / nome))
        if achados(txt, "CPF") < 1:
            raise SystemExit(f"FALHOU: o CPF não foi encontrado em {nome}"
                             + (" (o OCR do pacote não funcionou)" if nome == "escaneado.pdf" else ""))
        if achados(txt, "PESSOA") < 1:
            raise SystemExit(f"FALHOU: o nome não foi encontrado em {nome}")

    rodar(cli, "--sem-relatorio", "-o", str(saida), *(str(trabalho / n) for n in ARQUIVOS))
    gerados = sorted(p for p in saida.rglob("*") if p.is_file())
    print("Gerados:", [p.name for p in gerados])
    if len(gerados) != len(ARQUIVOS):
        raise SystemExit(f"FALHOU: esperava {len(ARQUIVOS)} arquivos anonimizados")
    texto = next(p for p in gerados if p.suffix == ".txt").read_text(encoding="utf-8")
    if CPF in texto or "Pedro" in texto:
        raise SystemExit("FALHOU: o texto anonimizado ainda tem o CPF ou o nome")

    # o programa pula arquivos terminados em "_anonimizado"; copia com outro nome para reanalisar
    reanalise = trabalho / "reanalise"
    reanalise.mkdir()
    for arq in gerados:
        copia = reanalise / arq.name.replace("_anonimizado", "_gerado")
        shutil.copy2(arq, copia)
        txt = rodar(cli, "--apenas-analisar", "--tipos", "CPF", str(copia))
        if achados(txt, "CPF"):
            raise SystemExit(f"FALHOU: o CPF continua legível em {arq.name}")
    print("Anonimização pelo pacote: OK")

    if janela:
        janela = janela.resolve()
        p = subprocess.Popen([str(janela)])
        time.sleep(12)
        if p.poll() is not None:
            raise SystemExit(f"FALHOU: a janela fechou sozinha (código {p.returncode})")
        p.terminate()
        try:
            p.wait(10)
        except subprocess.TimeoutExpired:
            p.kill()
        print("Janela abriu e ficou aberta: OK")


def main(argv: list[str]) -> None:
    if len(argv) >= 2 and argv[0] == "preparar":
        preparar(Path(argv[1]))
    elif len(argv) >= 3 and argv[0] == "conferir":
        janela = Path(argv[argv.index("--janela") + 1]) if "--janela" in argv else None
        conferir(Path(argv[1]), Path(argv[2]), janela)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
