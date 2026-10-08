"""Configuracion central del proyecto.

Este modulo es el unico lugar donde se leen las variables de entorno y donde
se resuelve la relacion *modelo de embeddings -> dimension*.

Centralizar la dimension es lo que evita el error clasico de estos pipelines:
crear el indice de Pinecone con una dimension (por ejemplo 1536) y despues
intentar subir vectores de otra (por ejemplo 384). Aqui la dimension se deriva
siempre del modelo configurado, nunca se escribe a mano.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

# --- Rutas del proyecto (absolutas: funcionan desde cualquier directorio) ---
RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
DIRECTORIO_DATOS = RAIZ_PROYECTO / "data"
DIRECTORIO_EVALUACION = RAIZ_PROYECTO / "evaluation"
ARCHIVO_GOLDEN_SET = DIRECTORIO_EVALUACION / "golden_set.json"

load_dotenv(RAIZ_PROYECTO / ".env")

# --- Modelos de embeddings soportados y su dimension EXACTA de salida ---
MODELOS_EMBEDDINGS: Dict[str, int] = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

# --- Modelo que se usa por defecto segun el proveedor elegido ---
MODELO_POR_DEFECTO: Dict[str, str] = {
    "huggingface": "sentence-transformers/all-MiniLM-L6-v2",
    "openai": "text-embedding-3-small",
}

PROVEEDORES_VALIDOS = tuple(MODELO_POR_DEFECTO.keys())


class ErrorDeConfiguracion(RuntimeError):
    """Error de configuracion con un mensaje accionable para el usuario."""


@dataclass(frozen=True)
class Configuracion:
    """Instantanea de toda la configuracion del pipeline."""

    pinecone_api_key: str
    index_name: str
    namespace: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    pinecone_cloud: str
    pinecone_region: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    peso_bm25: float
    peso_vectorial: float


def _entero(nombre: str, por_defecto: int) -> int:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return por_defecto
    try:
        return int(valor)
    except ValueError as error:
        raise ErrorDeConfiguracion(
            f"La variable {nombre} debe ser un numero entero (valor actual: {valor!r})."
        ) from error


def _flotante(nombre: str, por_defecto: float) -> float:
    valor = os.getenv(nombre)
    if valor is None or not valor.strip():
        return por_defecto
    try:
        return float(valor)
    except ValueError as error:
        raise ErrorDeConfiguracion(
            f"La variable {nombre} debe ser un numero (valor actual: {valor!r})."
        ) from error


@lru_cache(maxsize=1)
def obtener_configuracion() -> Configuracion:
    """Lee y valida la configuracion del .env (se cachea: se lee una sola vez)."""

    api_key = os.getenv("PINECONE_API_KEY", "").strip()
    if not api_key:
        raise ErrorDeConfiguracion(
            "Falta PINECONE_API_KEY en el archivo .env.\n"
            "  1) Si aun no existe, copia .env.example a .env.\n"
            "  2) Pega tu API key gratuita de Pinecone (https://app.pinecone.io -> API Keys)."
        )

    proveedor = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
    if proveedor not in PROVEEDORES_VALIDOS:
        raise ErrorDeConfiguracion(
            f"EMBEDDING_PROVIDER='{proveedor}' no es valido. "
            f"Opciones: {', '.join(PROVEEDORES_VALIDOS)}."
        )

    modelo = os.getenv("EMBEDDING_MODEL", "").strip() or MODELO_POR_DEFECTO[proveedor]
    if modelo not in MODELOS_EMBEDDINGS:
        raise ErrorDeConfiguracion(
            f"No tengo registrada la dimension del modelo '{modelo}'. "
            "Agregalo a MODELOS_EMBEDDINGS en src/config.py para que el indice "
            "se cree con la dimension correcta."
        )

    if proveedor == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
        raise ErrorDeConfiguracion(
            "EMBEDDING_PROVIDER=openai requiere OPENAI_API_KEY en el archivo .env. "
            "Si prefieres no usar OpenAI, deja EMBEDDING_PROVIDER=huggingface "
            "(modelo local, gratuito)."
        )

    return Configuracion(
        pinecone_api_key=api_key,
        index_name=(os.getenv("INDEX_NAME") or "rag-tecnico-python").strip(),
        namespace=(os.getenv("NAMESPACE") or "docs-tecnicos").strip(),
        embedding_provider=proveedor,
        embedding_model=modelo,
        embedding_dimension=MODELOS_EMBEDDINGS[modelo],
        pinecone_cloud=(os.getenv("PINECONE_CLOUD") or "aws").strip(),
        pinecone_region=(os.getenv("PINECONE_REGION") or "us-east-1").strip(),
        chunk_size=_entero("CHUNK_SIZE", 600),
        chunk_overlap=_entero("CHUNK_OVERLAP", 100),
        top_k=_entero("TOP_K", 5),
        peso_bm25=_flotante("PESO_BM25", 0.5),
        peso_vectorial=_flotante("PESO_VECTORIAL", 0.5),
    )
