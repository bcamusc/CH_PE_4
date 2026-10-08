"""Recuperador hibrido (BM25 + Pinecone) encapsulado en la clase RAGSystem.

BM25 aporta busqueda lexica: coincidencias de palabras exactas, siglas,
nombres propios e identificadores de codigo (raise_for_status, Pydantic,
else/finally). El vectorial aporta busqueda semantica: parafrasis y
sinonimos. El EnsembleRetriever combina ambos rankings con Reciprocal
Rank Fusion y pesos configurables en el .env.
"""

from typing import Any, Dict, List, Optional

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore

try:  # LangChain 1.x movio los retrievers clasicos al paquete langchain-classic
    from langchain_classic.retrievers import EnsembleRetriever
except ImportError:  # compatibilidad con versiones anteriores de langchain
    from langchain.retrievers import EnsembleRetriever

from src.config import ErrorDeConfiguracion, obtener_configuracion
from src.embeddings import obtener_embeddings
from src.ingesta import cargar_chunks
from src.setup_pinecone import leer_campo, obtener_cliente


class RAGSystem:
    """Encapsula el EnsembleRetriever y expone una salida simple (top-k resultados)."""

    def __init__(self, retriever: EnsembleRetriever, k: int = 5) -> None:
        self.retriever = retriever
        self.k = k

    def obtener_top_k(self, consulta: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Devuelve los `k` mejores fragmentos combinando resultados lexicos y semanticos."""
        limite = k or self.k
        documentos: List[Document] = self.retriever.invoke(consulta)[:limite]

        resultados = []
        for documento in documentos:
            metadata = documento.metadata or {}
            resultados.append(
                {
                    "contenido": documento.page_content or metadata.get("text", ""),
                    "fuente": metadata.get("fuente", metadata.get("source", "desconocida")),
                    "categoria": metadata.get("categoria", "desconocida"),
                    "seccion": metadata.get("seccion", ""),
                    "chunk_id": metadata.get("chunk_id"),
                }
            )
        return resultados


def _contar_vectores(indice: Any, namespace: str) -> int:
    """Cuenta los vectores del namespace (para detectar que la ingesta aun no corre)."""
    estadisticas = indice.describe_index_stats()
    try:
        namespaces = estadisticas["namespaces"]
    except (TypeError, KeyError):
        namespaces = leer_campo(estadisticas, "namespaces", {}) or {}

    try:
        info = namespaces.get(namespace, {})
    except AttributeError:
        info = {}

    total = leer_campo(info, "vector_count")
    if total is None:
        total = leer_campo(info, "record_count", 0)
    return int(total or 0)


def construir_rag_system(
    k: Optional[int] = None,
    chunks: Optional[List[Document]] = None,
    exigir_datos: bool = True,
) -> RAGSystem:
    """Construye el RAGSystem completo: corpus local (BM25) + Pinecone (vectorial)."""
    config = obtener_configuracion()
    k = k or config.top_k
    chunks = chunks if chunks is not None else cargar_chunks()

    if not chunks:
        raise ErrorDeConfiguracion(
            "No hay chunks en el corpus local. Revisa el directorio data/ (debe tener "
            "documentos .md, .txt, .json o .pdf)."
        )

    indice = obtener_cliente().Index(config.index_name)

    if exigir_datos and _contar_vectores(indice, config.namespace) == 0:
        raise ErrorDeConfiguracion(
            f"El namespace '{config.namespace}' del indice '{config.index_name}' esta vacio.\n"
            "  Ejecuta primero la ingesta:\n"
            "    python -m src.setup_pinecone\n"
            "    python -m src.ingesta"
        )

    # Recuperador lexico: BM25 sobre el mismo corpus de chunks (vive en memoria).
    retriever_bm25 = BM25Retriever.from_documents(chunks)
    retriever_bm25.k = k

    # Recuperador semantico: similitud de coseno sobre los vectores de Pinecone.
    vectorstore = PineconeVectorStore(
        index=indice,
        embedding=obtener_embeddings(),
        namespace=config.namespace,
    )
    retriever_vectorial = vectorstore.as_retriever(search_kwargs={"k": k})

    # Combinacion hibrida con pesos configurables (PESO_BM25 / PESO_VECTORIAL).
    retriever_hibrido = EnsembleRetriever(
        retrievers=[retriever_bm25, retriever_vectorial],
        weights=[config.peso_bm25, config.peso_vectorial],
    )

    return RAGSystem(retriever_hibrido, k=k)
