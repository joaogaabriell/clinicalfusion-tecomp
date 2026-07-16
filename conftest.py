"""Garante que `src` e `app` sejam importaveis nos testes a partir da raiz."""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "app"))
