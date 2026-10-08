"""Metricas de evaluacion (funciones puras, sin dependencias externas).

Se mantienen separadas del recuperador para poder testearlas sin red,
sin API keys y sin instalar LangChain ni Pinecone.
"""

from typing import Dict, Sequence


def recall_at_k(documento_esperado: str, documentos_recuperados: Sequence[str]) -> float:
    """Recall@k a nivel de documento: 1.0 si el documento esperado aparece
    entre los recuperados, 0.0 si no."""
    return 1.0 if documento_esperado in documentos_recuperados else 0.0


def precision_at_k(documento_esperado: str, documentos_recuperados: Sequence[str]) -> float:
    """Precision@k: fraccion de los documentos recuperados que pertenecen
    al documento esperado."""
    if not documentos_recuperados:
        return 0.0
    aciertos = sum(1 for documento in documentos_recuperados if documento == documento_esperado)
    return aciertos / len(documentos_recuperados)


def recall_chunks_at_k(
    documento_esperado: str,
    documentos_recuperados: Sequence[str],
    chunks_por_fuente: Dict[str, int],
) -> float:
    """Metrica complementaria: que fraccion de los chunks del documento esperado
    alcanzo a recuperar el top-k."""
    total = chunks_por_fuente.get(documento_esperado, 0)
    if total <= 0:
        return 0.0
    recuperados = sum(1 for documento in documentos_recuperados if documento == documento_esperado)
    return min(recuperados / total, 1.0)


def promedio(valores: Sequence[float]) -> float:
    """Promedio simple (0.0 si la secuencia viene vacia)."""
    return sum(valores) / len(valores) if valores else 0.0
