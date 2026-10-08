"""Script de evaluacion: ejecuta el Golden Set y calcula Precision@k y Recall@k.

Uso:
    python -m src.evaluate             # usa TOP_K del .env (5 por defecto)
    python -m src.evaluate --k 5
    python -m src.evaluate --sin-json  # no guarda evaluation/resultados.json

El reporte se imprime en consola y tambien se guarda en
evaluation/resultados.json (util para pegar el resumen en el README).
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import (
    ARCHIVO_GOLDEN_SET,
    DIRECTORIO_EVALUACION,
    Configuracion,
    ErrorDeConfiguracion,
    obtener_configuracion,
)
from src.ingesta import cargar_chunks
from src.metricas import precision_at_k, promedio, recall_at_k, recall_chunks_at_k
from src.rag_system import RAGSystem, construir_rag_system

ARCHIVO_RESULTADOS = DIRECTORIO_EVALUACION / "resultados.json"


def cargar_golden_set(ruta: Path = ARCHIVO_GOLDEN_SET) -> List[Dict[str, str]]:
    """Carga y valida el Golden Set: lista de {pregunta, documento_id_esperado}."""
    if not ruta.exists():
        raise ErrorDeConfiguracion(f"No existe el Golden Set en {ruta}")

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, list) or not datos:
        raise ErrorDeConfiguracion("El Golden Set debe ser una lista JSON con al menos una pregunta.")

    for numero, caso in enumerate(datos, 1):
        if not isinstance(caso, dict) or "pregunta" not in caso or "documento_id_esperado" not in caso:
            raise ErrorDeConfiguracion(
                f"El caso #{numero} del Golden Set debe tener las claves "
                "'pregunta' y 'documento_id_esperado'."
            )
    return datos


def evaluar(
    rag: RAGSystem,
    golden_set: List[Dict[str, str]],
    chunks_por_fuente: Dict[str, int],
    k: int = 5,
) -> Dict[str, Any]:
    """Ejecuta cada pregunta del Golden Set y agrega las metricas."""
    detalle: List[Dict[str, Any]] = []

    for caso in golden_set:
        pregunta = caso["pregunta"]
        esperado = caso["documento_id_esperado"]

        resultados = rag.obtener_top_k(pregunta, k=k)
        fuentes = [resultado["fuente"] for resultado in resultados]

        detalle.append(
            {
                "pregunta": pregunta,
                "documento_esperado": esperado,
                "documentos_recuperados": fuentes,
                "recall@k": recall_at_k(esperado, fuentes),
                "precision@k": precision_at_k(esperado, fuentes),
                "recall_chunks@k": recall_chunks_at_k(esperado, fuentes, chunks_por_fuente),
            }
        )

    return {
        "k": k,
        "total_preguntas": len(detalle),
        "detalle": detalle,
        "promedios": {
            "recall@k": promedio([fila["recall@k"] for fila in detalle]),
            "precision@k": promedio([fila["precision@k"] for fila in detalle]),
            "recall_chunks@k": promedio([fila["recall_chunks@k"] for fila in detalle]),
        },
    }


def imprimir_reporte(reporte: Dict[str, Any], config: Configuracion, total_chunks: int) -> None:
    """Imprime el resumen de la evaluacion en consola."""
    k = reporte["k"]
    separador = "=" * 80

    print(separador)
    print("EVALUACION DEL RECUPERADOR HIBRIDO (BM25 + Pinecone)")
    print(
        f"Indice: {config.index_name} | Namespace: {config.namespace} | "
        f"Embeddings: {config.embedding_model} ({config.embedding_dimension} dims)"
    )
    print(f"k = {k} | Preguntas del Golden Set: {reporte['total_preguntas']} | Chunks en el corpus: {total_chunks}")
    print(separador)

    for numero, fila in enumerate(reporte["detalle"], 1):
        estado = "[OK]" if fila["recall@k"] == 1.0 else "[X] "
        print(f"\n{estado} ({numero}/{reporte['total_preguntas']}) {fila['pregunta']}")
        print(f"        esperado:    {fila['documento_esperado']}")
        print(f"        recuperados: {', '.join(fila['documentos_recuperados']) or '(ninguno)'}")
        print(
            f"        Recall@{k}: {fila['recall@k']:.0%} | "
            f"Precision@{k}: {fila['precision@k']:.1%} | "
            f"Recall chunks@{k}: {fila['recall_chunks@k']:.1%}"
        )

    promedios = reporte["promedios"]
    print("\n" + "-" * 80)
    print("RESULTADOS PROMEDIOS")
    print(f"  Recall@{k} (documento):  {promedios['recall@k']:.1%}")
    print(f"  Precision@{k}:           {promedios['precision@k']:.1%}")
    print(f"  Recall@{k} (chunks):     {promedios['recall_chunks@k']:.1%}")
    print("-" * 80)
    print(
        "Nota: el Golden Set tiene un solo documento esperado por pregunta, por lo\n"
        f"que el Recall@{k} por documento solo puede valer 0% o 100% (no hay termino\n"
        "medio matematicamente posible). El Recall por chunks muestra el matiz intermedio."
    )
    print(separador)


def ejecutar(k: Optional[int] = None, guardar_json: bool = True) -> Dict[str, Any]:
    """Paso 3 del pipeline: construye el RAGSystem, evalua e imprime el reporte."""
    config = obtener_configuracion()
    k = k or config.top_k

    golden_set = cargar_golden_set()
    chunks = cargar_chunks()

    chunks_por_fuente: Dict[str, int] = {}
    for chunk in chunks:
        fuente = str(chunk.metadata.get("fuente", "desconocida"))
        chunks_por_fuente[fuente] = chunks_por_fuente.get(fuente, 0) + 1

    rag = construir_rag_system(k=k, chunks=chunks)
    reporte = evaluar(rag, golden_set, chunks_por_fuente, k=k)
    imprimir_reporte(reporte, config, len(chunks))

    if guardar_json:
        salida = {
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "configuracion": {
                "indice": config.index_name,
                "namespace": config.namespace,
                "proveedor_embeddings": config.embedding_provider,
                "modelo_embeddings": config.embedding_model,
                "dimension": config.embedding_dimension,
                "k": k,
            },
            **reporte,
        }
        ARCHIVO_RESULTADOS.parent.mkdir(parents=True, exist_ok=True)
        ARCHIVO_RESULTADOS.write_text(
            json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Resultados guardados en: {ARCHIVO_RESULTADOS}")

    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evalua el recuperador hibrido contra el Golden Set (Precision@k / Recall@k)."
    )
    parser.add_argument("--k", type=int, default=None, help="Cantidad de documentos a recuperar (por defecto TOP_K del .env).")
    parser.add_argument("--sin-json", action="store_true", help="No guardar evaluation/resultados.json.")
    argumentos = parser.parse_args()
    ejecutar(k=argumentos.k, guardar_json=not argumentos.sin_json)


if __name__ == "__main__":
    main()
