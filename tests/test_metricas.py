"""Tests de las metricas de evaluacion (sin red, sin API keys, sin LangChain).

Ejecutar:
    python tests/test_metricas.py
"""

import sys
from pathlib import Path

# Permite importar src/ aunque el script se ejecute desde tests/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.metricas import precision_at_k, promedio, recall_at_k, recall_chunks_at_k


def main() -> None:
    # Recall@k: presencia del documento esperado.
    assert recall_at_k("requests.md", ["pandas.md", "requests.md"]) == 1.0
    assert recall_at_k("requests.md", ["pandas.md", "pathlib.md"]) == 0.0
    assert recall_at_k("requests.md", []) == 0.0

    # Precision@k: fraccion de recuperados que pertenecen al documento esperado.
    assert precision_at_k("requests.md", ["requests.md", "requests.md", "pandas.md"]) == 2 / 3
    assert precision_at_k("requests.md", ["requests.md"]) == 1.0
    assert precision_at_k("requests.md", []) == 0.0

    # Recall por chunks: cuantos chunks del documento esperado se recuperaron.
    chunks_por_fuente = {"requests.md": 4, "pandas.md": 2}
    recuperados = ["requests.md", "requests.md", "pandas.md"]
    assert recall_chunks_at_k("requests.md", recuperados, chunks_por_fuente) == 0.5
    assert recall_chunks_at_k("asyncio.md", ["requests.md"], chunks_por_fuente) == 0.0
    assert recall_chunks_at_k("pandas.md", ["pandas.md", "pandas.md", "pandas.md"], chunks_por_fuente) == 1.0

    # Promedio y casos borde.
    assert promedio([1.0, 0.0]) == 0.5
    assert promedio([]) == 0.0

    print("[OK] Todos los tests de metricas pasaron.")


if __name__ == "__main__":
    main()
