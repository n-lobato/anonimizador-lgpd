"""Mede quanto a detecção automática acerta no corpus de teste.

Uso:
    python build/avaliar.py                 # resumo dos dois grupos
    python build/avaliar.py --detalhes      # lista cada vazamento e falso positivo
    python build/avaliar.py --grupo validacao

A medição usa o mesmo caminho do programa (Sessao -> análise -> códigos
consolidados), sem a revisão manual. Ou seja: mostra o que sairia anonimizado
se o usuário aceitasse tudo sem conferir.

Para cada dado marcado no corpus:
- "coberto": todas as letras e números foram substituídos;
- "parcial": parte do dado continua legível (conta como vazamento);
- "vazou": nada foi substituído.
Falso positivo é um trecho substituído que não corresponde a nenhum dado marcado.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from anonimizador.config import Configuracao, Termos  # noqa: E402
from anonimizador.processador import Sessao  # noqa: E402
from anonimizador.registro import Substituidor  # noqa: E402

CORPUS = RAIZ / "tests" / "corpus"
MARCA = re.compile(r"\[\[(\??)([A-Z_]+)\|(.+?)\]\]", re.S)


@dataclass
class Marcado:
    ini: int
    fim: int
    tipo: str
    texto: str
    opcional: bool


def ler_marcado(conteudo: str) -> tuple[str, list[Marcado]]:
    partes, marcados, pos, n = [], [], 0, 0
    for m in MARCA.finditer(conteudo):
        partes.append(conteudo[pos:m.start()])
        n += m.start() - pos
        trecho = m.group(3)
        marcados.append(Marcado(n, n + len(trecho), m.group(2), trecho, bool(m.group(1))))
        partes.append(trecho)
        n += len(trecho)
        pos = m.end()
    partes.append(conteudo[pos:])
    return "".join(partes), marcados


@dataclass
class Resultado:
    arquivo: str
    marcado: Marcado
    status: str  # coberto | parcial | vazou
    legivel: str = ""


def avaliar_arquivo(caminho: Path) -> tuple[list[Resultado], list[tuple[str, str]]]:
    # bytes, e não read_text/write_text: no Windows o modo texto troca \n por \r\n
    # e deslocaria as posições do gabarito
    bruto = caminho.read_bytes().decode("utf-8").replace("\r\n", "\n")
    texto, marcados = ler_marcado(bruto)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / caminho.name
        f.write_bytes(texto.encode("utf-8"))
        sessao = Sessao(Configuracao(), Termos())
        sessao.carregar([f])
        sessao.analisar()
        arq = sessao.arquivos[0]
        assert not arq.erro, arq.erro
        assert arq.texto == texto
        subst = Substituidor(sessao.registro, sessao.registro.escopo(arq.chave))
        trechos = subst.trechos(texto)

    coberto = [False] * len(texto)
    for a, b, _ in trechos:
        for i in range(a, b):
            coberto[i] = True

    resultados = []
    for m in marcados:
        if m.opcional:
            continue
        pos = [i for i in range(m.ini, m.fim) if texto[i].isalnum()]
        cob = sum(coberto[i] for i in pos)
        if cob == len(pos):
            status = "coberto"
        elif cob == 0:
            status = "vazou"
        else:
            status = "parcial"
        legivel = "".join(texto[i] if not coberto[i] else "█" for i in range(m.ini, m.fim))
        resultados.append(Resultado(caminho.name, m, status, legivel))

    falsos = []
    for a, b, cod in trechos:
        if not any(a < m.fim and m.ini < b for m in marcados):
            falsos.append((texto[a:b], cod))
    return resultados, falsos


def avaliar_grupo(grupo: str):
    resultados, falsos = [], []
    for f in sorted((CORPUS / grupo).glob("*.txt")):
        r, fp = avaliar_arquivo(f)
        resultados += r
        falsos += [(f.name, t, c) for t, c in fp]
    return resultados, falsos


def tabela(resultados: list[Resultado]) -> list[tuple[str, int, int, int, int]]:
    por_tipo: dict[str, Counter] = defaultdict(Counter)
    for r in resultados:
        por_tipo[r.marcado.tipo][r.status] += 1
    linhas = []
    for tipo in sorted(por_tipo, key=lambda t: (t != "PESSOA", t)):
        c = por_tipo[tipo]
        linhas.append((tipo, sum(c.values()), c["coberto"], c["parcial"], c["vazou"]))
    return linhas


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "-"


def imprimir(grupo: str, resultados, falsos, detalhes: bool) -> None:
    print(f"\n=== {grupo} ===")
    print(f"{'Tipo':<16}{'Total':>6}{'Coberto':>9}{'Parcial':>9}{'Vazou':>7}{'Acerto':>8}")
    tot = Counter()
    for tipo, n, cob, par, vaz in tabela(resultados):
        print(f"{tipo:<16}{n:>6}{cob:>9}{par:>9}{vaz:>7}{pct(cob, n):>8}")
        tot.update(n=n, cob=cob, par=par, vaz=vaz)
    print(f"{'TOTAL':<16}{tot['n']:>6}{tot['cob']:>9}{tot['par']:>9}{tot['vaz']:>7}{pct(tot['cob'], tot['n']):>8}")
    marcados_total = tot["cob"] + tot["par"]
    print(f"Falsos positivos: {len(falsos)} "
          f"(de {marcados_total + len(falsos)} trechos substituídos que tocam o texto)")
    if detalhes:
        vaz = [r for r in resultados if r.status != "coberto"]
        if vaz:
            print("\nVazamentos:")
            for r in vaz:
                print(f"  [{r.status}] {r.arquivo}: {r.marcado.tipo} '{r.marcado.texto}' -> '{r.legivel}'")
        if falsos:
            print("\nFalsos positivos:")
            for arq, t, c in falsos:
                print(f"  {arq}: '{t}' -> {c}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grupo", choices=["desenvolvimento", "validacao"])
    ap.add_argument("--detalhes", action="store_true")
    args = ap.parse_args(argv)
    for grupo in [args.grupo] if args.grupo else ["desenvolvimento", "validacao"]:
        r, f = avaliar_grupo(grupo)
        imprimir(grupo, r, f, args.detalhes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
