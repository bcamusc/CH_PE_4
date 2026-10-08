"""Inicializacion de infraestructura en Pinecone (modo Serverless).

Verifica si el indice existe:
  - si NO existe, lo crea con la dimension exacta del modelo de embeddings y
    espera a que quede listo;
  - si existe, comprueba que la dimension coincida y aborta con un mensaje
    claro si no (asi nunca intentas subir vectores de 384 dims a un indice
    configurado con 1536).

Uso:
    python -m src.setup_pinecone
"""

import time
from typing import Any, Optional

from pinecone import Pinecone, ServerlessSpec

from src.config import ErrorDeConfiguracion, obtener_configuracion


def obtener_cliente(api_key: Optional[str] = None) -> Pinecone:
    """Crea el cliente de Pinecone con la API key del .env."""
    config = obtener_configuracion()
    return Pinecone(api_key=api_key or config.pinecone_api_key)


def leer_campo(objeto: Any, clave: str, por_defecto: Any = None) -> Any:
    """Lee un campo de una respuesta del SDK (soporta dict y objeto)."""
    if isinstance(objeto, dict):
        return objeto.get(clave, por_defecto)
    return getattr(objeto, clave, por_defecto)


def nombres_de_indices(pc: Pinecone) -> list:
    """Lista los nombres de los indices de la cuenta."""
    return [str(leer_campo(indice, "name")) for indice in pc.list_indexes()]


def dimension_del_indice(pc: Pinecone, nombre: str) -> Optional[int]:
    """Devuelve la dimension configurada del indice (o None si no se pudo leer)."""
    valor = leer_campo(pc.describe_index(nombre), "dimension")
    return int(valor) if valor is not None else None


def esperar_indice_listo(pc: Pinecone, nombre: str, timeout: int = 90, intervalo: float = 3.0) -> bool:
    """Espera hasta que el indice quede en estado 'ready'."""
    inicio = time.time()
    while time.time() - inicio < timeout:
        estado = leer_campo(pc.describe_index(nombre), "status")
        if leer_campo(estado, "ready", False):
            return True
        time.sleep(intervalo)
    return False


def crear_indice_si_no_existe(pc: Optional[Pinecone] = None) -> str:
    """Garantiza que el indice existe con la dimension correcta. Devuelve su nombre."""
    config = obtener_configuracion()
    pc = pc or obtener_cliente()

    if config.index_name in nombres_de_indices(pc):
        dimension = dimension_del_indice(pc, config.index_name)
        if dimension is not None and dimension != config.embedding_dimension:
            raise ErrorDeConfiguracion(
                f"El indice '{config.index_name}' ya existe con dimension {dimension}, "
                f"pero el modelo '{config.embedding_model}' genera vectores de "
                f"{config.embedding_dimension} dimensiones.\n"
                "  Opcion 1 (recomendada): usa otro INDEX_NAME en el .env, "
                "por ejemplo rag-tecnico-openai.\n"
                "  Opcion 2: elimina el indice en https://app.pinecone.io y vuelve "
                "a ejecutar este script."
            )
        print(f"[OK] El indice '{config.index_name}' ya existe (dimension {dimension}, metric=cosine). No se recrea.")
        return config.index_name

    print(
        f"[..] Creando indice '{config.index_name}' (dimension {config.embedding_dimension}, "
        f"metric=cosine, serverless cloud={config.pinecone_cloud}, region={config.pinecone_region})..."
    )
    pc.create_index(
        name=config.index_name,
        dimension=config.embedding_dimension,
        metric="cosine",
        spec=ServerlessSpec(cloud=config.pinecone_cloud, region=config.pinecone_region),
    )

    if esperar_indice_listo(pc, config.index_name):
        print(f"[OK] Indice '{config.index_name}' creado y listo para recibir vectores.")
    else:
        print(
            "[WARN] El indice fue creado pero aun no reporta estado 'ready'. "
            "Espera unos segundos antes de ejecutar la ingesta."
        )
    return config.index_name


def ejecutar() -> str:
    """Paso 1 del pipeline: deja el indice listo (lo crea si no existe)."""
    config = obtener_configuracion()
    pc = obtener_cliente()

    indices = nombres_de_indices(pc)
    print(f"[INFO] Indices en tu cuenta: {indices if indices else '(ninguno)'}")
    print(
        f"[INFO] Configuracion: INDEX_NAME='{config.index_name}', NAMESPACE='{config.namespace}', "
        f"embeddings='{config.embedding_model}' ({config.embedding_dimension} dims)"
    )

    nombre = crear_indice_si_no_existe(pc)
    estadisticas = pc.Index(nombre).describe_index_stats()
    print(f"[INFO] Estadisticas actuales del indice: {estadisticas}")
    return nombre


def main() -> None:
    ejecutar()


if __name__ == "__main__":
    main()
