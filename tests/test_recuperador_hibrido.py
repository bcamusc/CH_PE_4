"""Test del recuperador hibrido con dobles (fakes): sin red y sin API keys.

Verifica que:
  1. PineconeRetriever convierte los matches del SDK en Documents
     (page_content desde metadata["text"] y metadata limpia).
  2. El EnsembleRetriever combina BM25 (local) con el recuperador de Pinecone.

Ejecutar (desde la raíz del repo):
    python tests/test_recuperador_hibrido.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from src.rag_system import PineconeRetriever

try:  # mismo patron de import que src/rag_system.py
    from langchain_classic.retrievers import EnsembleRetriever
except ImportError:
    from langchain.retrievers import EnsembleRetriever


class EmbeddingsFalsos:
    """Devuelve un vector fijo; no descarga ningun modelo."""

    def embed_query(self, texto: str):
        return [0.1, 0.2, 0.3]


class CoincidenciaFalsa:
    def __init__(self, metadata):
        self.metadata = metadata


class RespuestaFalsa:
    def __init__(self, coincidencias):
        self.matches = coincidencias


class IndiceFalso:
    """Imita el SDK nativo de Pinecone: solo implementa .query()."""

    def __init__(self, coincidencias):
        self._coincidencias = coincidencias

    def query(self, vector, top_k, include_metadata, namespace):
        return RespuestaFalsa(self._coincidencias[:top_k])


def main() -> None:
    # --- 1) PineconeRetriever: los matches se convierten en Documents ---
    indice_falso = IndiceFalso(
        [
            CoincidenciaFalsa(
                {
                    "text": "raise_for_status lanza HTTPError en respuestas 4xx o 5xx.",
                    "fuente": "requests.md",
                    "categoria": "bibliotecas",
                    "chunk_id": 1,
                }
            )
        ]
    )
    retriever_pinecone = PineconeRetriever(
        indice=indice_falso,
        embeddings=EmbeddingsFalsos(),
        namespace="test",
        k=2,
    )
    documentos = retriever_pinecone.invoke("¿que hace raise_for_status?")

    assert len(documentos) == 1
    assert documentos[0].page_content.startswith("raise_for_status")
    assert documentos[0].metadata["fuente"] == "requests.md"
    assert "text" not in documentos[0].metadata  # el texto no queda duplicado

    # --- 2) EnsembleRetriever: BM25 + Pinecone combinados ---
    docs_locales = [
        Document(
            page_content="texto local sobre pathlib y read_text",
            metadata={"fuente": "pathlib.md", "categoria": "bibliotecas", "chunk_id": 0},
        ),
        Document(
            page_content="otro texto local sobre pandas",
            metadata={"fuente": "pandas.md", "categoria": "bibliotecas", "chunk_id": 1},
        ),
    ]
    retriever_bm25 = BM25Retriever.from_documents(docs_locales)
    retriever_bm25.k = 2

    retriever_hibrido = EnsembleRetriever(
        retrievers=[retriever_bm25, retriever_pinecone],
        weights=[0.5, 0.5],
    )
    resultados = retriever_hibrido.invoke("raise_for_status")

    fuentes = {documento.metadata["fuente"] for documento in resultados}
    assert "requests.md" in fuentes  # aporte del recuperador vectorial (fake)
    assert resultados, "El ensemble no puede devolver una lista vacia"

    print("[OK] Test del recuperador hibrido (con fakes) paso.")


if __name__ == "__main__":
    main()
