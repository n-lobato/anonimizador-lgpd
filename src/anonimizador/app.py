"""Ponto de entrada: abre a janela ou, com --cli, roda na linha de comando.

Arrastar arquivos sobre o ícone do .exe (ou usar "Enviar para") abre a janela
já com esses arquivos na fila.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    nome_exe = Path(sys.executable).stem.lower()
    if "--cli" in args or nome_exe.startswith("anonimizador-cli") or any(
            a in ("-h", "--help", "--listar-tipos") for a in args):
        from .cli import main as cli_main
        return cli_main([a for a in args if a != "--cli"])
    try:
        from .gui.janela import executar
    except ImportError as e:
        print(f"Interface gráfica indisponível ({e}). Use: python -m anonimizador --cli <arquivos>")
        return 1
    return executar(args)


if __name__ == "__main__":
    sys.exit(main())
