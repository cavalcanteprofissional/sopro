#!/usr/bin/env python
"""Task runner do Sopro (equivalente a ``npm run``; substitui um Makefile).

Roda com o mesmo interpretador que o invocou (use o Python do ambiente virtual) e
aponta para o repositório raiz, então funciona igual no Windows, Linux e macOS.

Uso::

    python scripts/tasks.py dev        # roda o app a partir do código-fonte
    python scripts/tasks.py demo       # roda o modo demonstração
    python scripts/tasks.py test       # roda os testes
    python scripts/tasks.py bench ...  # roda o benchmark
    python scripts/tasks.py validate   # valida o pacote de domínio
    python scripts/tasks.py build      # gera o executável portátil (Windows)
    python scripts/tasks.py install    # instala as dependências completas

Argumentos extras após o nome da tarefa são repassados ao comando.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRAS = "dev,ui,audio,stt"
POWERSHELL = "powershell.exe"


def build_command(name: str, rest: list[str]) -> list[str]:
    """Devolve o argv da tarefa ``name`` (mapeada para um comando)."""
    python = sys.executable
    commands: dict[str, list[str]] = {
        "test": [python, "-m", "pytest", "-q", *rest],
        "dev": [python, "-m", "sopro", *rest],
        "demo": [python, "-m", "sopro", "--demo", *rest],
        "bench": [python, "-m", "sopro.app.benchmark_cli", *rest],
        "validate": [python, "-m", "sopro.core.glossary.validate", *rest],
        "install": [python, "-m", "pip", "install", "-e", f".[{EXTRAS}]"],
        "build": [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "build-windows.ps1"),
            *rest,
        ],
    }
    try:
        return commands[name]
    except KeyError as exc:
        raise SystemExit(f"tarefa desconhecida: {name!r}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tasks", description="Tarefas de desenvolvimento do Sopro."
    )
    parser.add_argument(
        "task",
        choices=("dev", "demo", "test", "bench", "validate", "build", "install"),
        help="tarefa a executar",
    )
    parser.add_argument("rest", nargs=argparse.REMAINDER, help="argumentos extras")
    args = parser.parse_args(argv)

    command = build_command(args.task, list(args.rest))
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.call(command, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
