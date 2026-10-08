"""Consulta interactiva del recuperador hibrido.

Uso:
    python -m src.consulta                                   # modo interactivo
    python -m src.consulta --pregunta "¿Como uso pathlib?"   # consulta unica
"""

import argparse
from typing import Any, Dict, List

from src.config import obtener_configuracion
from src.rag_system import construir_rag_system


def imprimir_resultados(resultados: List[Dict[str, Any]]) -> None:
    if not resultados:
        print("[WARN] No se recupero ningun fragmento.")
        return

    print(f"\nTop {len(resultados)} fragmentos recuperados (BM25 + Pinecone):")
    for numero, resultado in enumerate(resultados, 1):
        seccion = f" | seccion: {resultado['seccion']}" if resultado.get("seccion") else ""
        extracto = resultado["contenido"][:220].replace("\n", " ")
        if len(resultado["contenido"]) > 220:
            extracto += "..."
        print(f"\n  {numero}. [{resultado['fuente']} | {resultado['categoria']}{seccion}]")
        print(f"     {extracto}")
    print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta el recuperador hibrido (BM25 + Pinecone).")
    parser.add_argument("--pregunta", help="Consulta unica (si se omite, entra en modo interactivo).")
    parser.add_argument("--k", type=int, default=None, help="Cantidad de fragmentos a recuperar.")
    argumentos = parser.parse_args()

    config = obtener_configuracion()
    print(
        f"[INFO] Indice: '{config.index_name}' | Namespace: '{config.namespace}' | "
        f"Embeddings: {config.embedding_model} ({config.embedding_dimension} dims)"
    )
    rag = construir_rag_system(k=argumentos.k)

    if argumentos.pregunta:
        imprimir_resultados(rag.obtener_top_k(argumentos.pregunta))
        return

    print("Modo interactivo - consulta el sistema RAG hibrido (escribe 'salir' para terminar)\n")
    while True:
        pregunta = input("Pregunta: ").strip()
        if pregunta.lower() in {"salir", "exit", "quit", ""}:
            print("\nListo, terminamos la sesion.")
            break
        imprimir_resultados(rag.obtener_top_k(pregunta))


if __name__ == "__main__":
    main()
