"""Fabrica de embeddings.

Un solo lugar decide que modelo se usa: cualquier parte del pipeline que
necesite generar vectores llama a obtener_embeddings() y obtiene exactamente
el mismo modelo (y por lo tanto la misma dimension que el indice de Pinecone).
"""

from langchain_core.embeddings import Embeddings

from src.config import obtener_configuracion


def obtener_embeddings() -> Embeddings:
    """Crea el generador de embeddings segun EMBEDDING_PROVIDER del .env."""

    config = obtener_configuracion()

    if config.embedding_provider == "huggingface":
        # Modelo local: corre en CPU, no requiere API key ni paga por uso.
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=config.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

    if config.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=config.embedding_model)

    # obtener_configuracion() ya valida el proveedor, asi que esto no deberia pasar.
    raise ValueError(f"Proveedor de embeddings no soportado: {config.embedding_provider}")
