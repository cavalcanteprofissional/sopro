"""Ponto de entrada usado pelo build de distribuição (docs/09 §3.2)."""

from __future__ import annotations

from sopro.app.run import main

if __name__ == "__main__":
    raise SystemExit(main())
