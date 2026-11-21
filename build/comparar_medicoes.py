"""Compara a medição de acertos entre os sistemas (Windows, Mac e Linux).

Uso: python build/comparar_medicoes.py PASTA

A PASTA deve ter os arquivos gerados por avaliar.py --json e avaliar_ocr.py --json
em cada sistema, com nomes no formato medicao-<sistema>-texto.json e
medicao-<sistema>-ocr.json. O Windows é a referência.

Regras (o build falha se alguma for quebrada):
- Texto (Word, TXT etc.): a detecção é o mesmo código Python em todo lugar, então
  o resultado tem de ser idêntico ao do Windows.
- PDF digitalizado (OCR): o OCR pode variar um pouco entre processadores (Intel e
  Apple Silicon fazem contas de ponto flutuante de jeitos diferentes). Aceita-se no
  máximo 1 dado coberto a menos que no Windows, por grupo do corpus. Qualquer
  diferença é mostrada na tela.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REFERENCIA = "windows"
TOLERANCIA_OCR = 1


def totais(grupo: dict) -> dict:
    t = {"total": 0, "coberto": 0, "parcial": 0, "vazou": 0}
    for c in grupo["tipos"].values():
        for k in t:
            t[k] += c.get(k, 0)
    return t


def main() -> int:
    pasta = Path(sys.argv[1])
    medicoes: dict[str, dict[str, dict]] = {}
    for arq in sorted(pasta.rglob("medicao-*.json")):
        _, sistema, tipo = arq.stem.split("-", 2)
        medicoes.setdefault(sistema, {})[tipo] = json.loads(arq.read_text(encoding="utf-8"))
    if REFERENCIA not in medicoes:
        print("Medição do Windows não encontrada.")
        return 1
    ref = medicoes[REFERENCIA]
    erros = []
    print(f"{'Sistema':<22}{'Medição':<9}{'Grupo':<17}{'Total':>6}{'Coberto':>9}{'Parcial':>9}{'Vazou':>7}")
    for sistema in [REFERENCIA] + sorted(s for s in medicoes if s != REFERENCIA):
        for tipo in ("texto", "ocr"):
            atual = medicoes[sistema].get(tipo)
            if atual is None:
                erros.append(f"{sistema}: medição '{tipo}' não encontrada")
                continue
            for grupo, dados in atual.items():
                t = totais(dados)
                print(f"{sistema:<22}{tipo:<9}{grupo:<17}{t['total']:>6}{t['coberto']:>9}"
                      f"{t['parcial']:>9}{t['vazou']:>7}")
            if sistema == REFERENCIA:
                continue
            if tipo == "texto":
                if atual != ref["texto"]:
                    erros.append(f"{sistema}: a detecção em texto deu resultado diferente do Windows")
            else:
                for grupo, dados in ref["ocr"].items():
                    r, a = totais(dados), totais(atual.get(grupo, {"tipos": {}}))
                    if a["coberto"] < r["coberto"] - TOLERANCIA_OCR:
                        erros.append(f"{sistema}: OCR cobriu {a['coberto']} dados em '{grupo}', "
                                     f"contra {r['coberto']} no Windows")
    if erros:
        print("\nFALHOU:")
        for e in erros:
            print("  -", e)
        return 1
    print("\nResultados equivalentes em todos os sistemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
