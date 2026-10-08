"""Orquestador del flujo completo: setup del indice -> ingesta -> evaluacion.

Uso:
    python -m src.pipeline              # flujo completo
    python -m src.pipeline --recrear    # ademas vacia el namespace antes de ingerir
"""

import argparse

from src import evaluate, ingesta, setup_pinecone


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta el pipeline completo del modulo RAG.")
    parser.add_argument("--recrear", action="store_true", help="Vacia el namespace antes de ingerir.")
    argumentos = parser.parse_args()

    print("\n### PASO 1/3: verificando el indice de Pinecone ###")
    setup_pinecone.ejecutar()

    print("\n### PASO 2/3: ingesta de documentos ###")
    ingesta.ejecutar(recrear=argumentos.recrear)

    print("\n### PASO 3/3: evaluacion (Precision@k / Recall@k) ###")
    evaluate.ejecutar()


if __name__ == "__main__":
    main()
