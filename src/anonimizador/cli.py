"""Uso pela linha de comando (sem revisão manual)."""

from __future__ import annotations

import argparse
import sys

from . import NOME_APP, __version__
from .config import carregar_config, carregar_termos
from .deteccao.modelo import TIPOS, descricao
from .processador import Sessao
from .relatorio import gerar


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="anonimizador-cli",
        description=f"{NOME_APP} {__version__}: anonimiza dados pessoais em arquivos e pastas.")
    p.add_argument("entradas", nargs="+", help="arquivos ou pastas")
    p.add_argument("-o", "--saida", help="pasta de saída (padrão: subpasta 'anonimizados' ao lado do original)")
    p.add_argument("--sem-ocr", action="store_true", help="não usar OCR em páginas digitalizadas")
    p.add_argument("--forcar-ocr", action="store_true", help="usar OCR também em páginas com texto")
    p.add_argument("--sem-relatorio", action="store_true", help="não gerar a tabela de-para")
    p.add_argument("--por-arquivo", action="store_true", help="numerar os códigos separadamente em cada arquivo")
    p.add_argument("--sem-subpastas", action="store_true", help="não entrar nas subpastas")
    p.add_argument("--tipos", help="tipos a detectar, separados por vírgula (ex.: PESSOA,CPF,RG)")
    p.add_argument("--apenas-analisar", action="store_true", help="só lista o que seria anonimizado")
    p.add_argument("--listar-tipos", action="store_true", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--listar-tipos" in argv:
        for t in TIPOS:
            print(f"{t:16} {descricao(t)}")
        return 0
    args = _parser().parse_args([a for a in argv if a != "--cli"])
    cfg = carregar_config()
    cfg.revisar = False
    if args.saida:
        cfg.pasta_saida = args.saida
    if args.sem_ocr:
        cfg.ocr = False
    if args.forcar_ocr:
        cfg.forcar_ocr = True
    if args.sem_relatorio:
        cfg.gerar_relatorio = False
    if args.por_arquivo:
        cfg.codigos_globais = False
    if args.sem_subpastas:
        cfg.incluir_subpastas = False
    if args.tipos:
        cfg.tipos = [t.strip().upper() for t in args.tipos.split(",") if t.strip().upper() in TIPOS]

    sessao = Sessao(cfg, carregar_termos())
    sessao.carregar(args.entradas)
    for msg in sessao.ignorados:
        print(f"[ignorado] {msg}")
    if not sessao.arquivos:
        print("Nenhum arquivo suportado encontrado.")
        return 1

    def progresso(i, total, msg):
        print(f"[{i}/{total}] {msg}", flush=True)

    sessao.analisar(progresso)
    for e in sessao.registro.ordenadas():
        print(f"  {e.codigo:14} {descricao(e.tipo):28} {e.total:4}x  {e.rotulo}")
    if args.apenas_analisar:
        return 0
    sessao.aplicar(progresso)
    erros = 0
    for a in sessao.arquivos:
        if a.erro:
            erros += 1
            print(f"[erro] {a.caminho.name}: {a.erro}")
        elif a.saida:
            print(f"[ok] {a.saida}")
        for av in a.avisos:
            print(f"   aviso: {av}")
    if cfg.gerar_relatorio and any(a.saida for a in sessao.arquivos):
        pasta = sessao.pasta_relatorio()
        if pasta:
            print(f"Relatório: {gerar(sessao, pasta)}")
    return 2 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
