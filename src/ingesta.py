"""Pipeline de ingesta: data/ -> chunks -> embeddings -> Pinecone.

Cada vector se sube con IDs deterministas y metadata avanzada:

    text       contenido del chunk (el texto vive DENTRO de Pinecone, asi no
               hace falta consultar una base de datos relacional aparte)
    fuente     archivo de origen
    categoria  etiqueta de categoria (carpeta del dataset)
    etiquetas  lista de etiquetas (categoria + tema del documento)
    seccion    ultima seccion/titulo detectado en el chunk (Markdown/TXT)
    pagina     numero de pagina (solo archivos PDF)
    chunk_id   posicion del chunk dentro del corpus

Los IDs deterministas (fuente + chunk_id) hacen la ingesta idempotente:
volver a correrla actualiza los mismos vectores en vez de duplicarlos.

Formatos soportados: .md, .markdown, .txt, .json y .pdf.

Uso:
    python -m src.ingesta              # carga + sube (no borra nada)
    python -m src.ingesta --recrear    # vacia el namespace antes de subir
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import DIRECTORIO_DATOS, obtener_configuracion
from src.embeddings import obtener_embeddings
from src.setup_pinecone import obtener_cliente

EXTENSIONES_SOPORTADAS = {".md", ".markdown", ".txt", ".json", ".pdf"}
_PATRON_SECCION = re.compile(r"^#{1,4}\s+(.+?)\s*$", re.MULTILINE)


# ---------------------------------------------------------------------------
# 1) Carga de documentos
# ---------------------------------------------------------------------------

def _metadatos_base(ruta: Path) -> Dict:
    categoria = ruta.parent.name
    return {
        "fuente": ruta.name,
        "categoria": categoria,
        "etiquetas": [categoria, ruta.stem],
    }


def _leer_texto_plano(ruta: Path) -> List[Document]:
    contenido = ruta.read_text(encoding="utf-8")
    return [Document(page_content=contenido, metadata=_metadatos_base(ruta))]


def _leer_json(ruta: Path) -> List[Document]:
    """JSON como lista de objetos con clave 'contenido' (o 'texto' / 'content')."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if isinstance(datos, dict):
        datos = [datos]

    documentos = []
    for numero, registro in enumerate(datos, 1):
        if not isinstance(registro, dict):
            continue
        contenido = registro.get("contenido") or registro.get("texto") or registro.get("content")
        if not contenido:
            continue
        metadata = _metadatos_base(ruta)
        metadata["titulo"] = str(registro.get("titulo", f"registro {numero}"))
        documentos.append(Document(page_content=str(contenido), metadata=metadata))
    return documentos


def _leer_pdf(ruta: Path) -> List[Document]:
    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError as error:  # falta pypdf o langchain-community
        raise RuntimeError(
            f"No se pudo leer el PDF '{ruta.name}': instala las dependencias con "
            "'pip install -r requirements.txt' (pypdf incluido)."
        ) from error

    documentos = PyPDFLoader(str(ruta)).load()
    for documento in documentos:
        metadata = _metadatos_base(ruta)
        # 'page' viene base 0; lo guardamos base 1 para que sea legible.
        metadata["pagina"] = int(documento.metadata.get("page", 0)) + 1
        documento.metadata = metadata
    return documentos


def cargar_documentos(directorio: Optional[Path] = None) -> List[Document]:
    """Carga todos los documentos soportados desde `data/` (recursivo)."""
    directorio = Path(directorio) if directorio else DIRECTORIO_DATOS
    if not directorio.exists():
        raise FileNotFoundError(f"No existe el directorio de datos: {directorio}")

    documentos: List[Document] = []
    omitidos: List[str] = []

    for ruta in sorted(directorio.rglob("*")):
        if not ruta.is_file():
            continue
        extension = ruta.suffix.lower()
        if extension not in EXTENSIONES_SOPORTADAS:
            omitidos.append(ruta.name)
            continue
        if extension in {".md", ".markdown", ".txt"}:
            documentos.extend(_leer_texto_plano(ruta))
        elif extension == ".json":
            documentos.extend(_leer_json(ruta))
        elif extension == ".pdf":
            documentos.extend(_leer_pdf(ruta))

    if omitidos:
        print(f"[INFO] Omitidos por extension no soportada: {', '.join(sorted(set(omitidos)))}")
    print(f"[OK] Documentos cargados: {len(documentos)}")
    return documentos


# ---------------------------------------------------------------------------
# 2) Chunking + metadata enriquecida
# ---------------------------------------------------------------------------

def _detectar_seccion(texto: str) -> str:
    """Devuelve el ultimo titulo de seccion ('## ...') presente en el chunk."""
    coincidencias = _PATRON_SECCION.findall(texto)
    return coincidencias[-1].strip() if coincidencias else ""


def dividir_en_chunks(
    documentos: List[Document],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> List[Document]:
    """Divide con RecursiveCharacterTextSplitter y enriquece la metadata."""
    config = obtener_configuracion()
    chunk_size = chunk_size or config.chunk_size
    chunk_overlap = chunk_overlap or config.chunk_overlap

    separador = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = separador.split_documents(documentos)

    ultima_seccion_por_fuente: Dict[str, str] = {}
    for indice, chunk in enumerate(chunks):
        fuente = str(chunk.metadata.get("fuente", "desconocida"))
        # Si el chunk no contiene un titulo, hereda la seccion anterior del
        # mismo archivo (los splits cortan a mitad de seccion).
        seccion = _detectar_seccion(chunk.page_content) or ultima_seccion_por_fuente.get(fuente, "")
        ultima_seccion_por_fuente[fuente] = seccion
        # Diccionario nuevo por chunk (evita compartir el mismo dict entre chunks).
        chunk.metadata = {**chunk.metadata, "seccion": seccion, "chunk_id": indice}

    print(f"[OK] Chunks generados: {len(chunks)} (chunk_size={chunk_size} tokens, overlap={chunk_overlap})")
    if chunks:
        print(f"[INFO] Ejemplo de metadata: {chunks[0].metadata}")
    return chunks


def cargar_chunks() -> List[Document]:
    """Carga + divide. Este corpus local tambien alimenta al recuperador BM25."""
    return dividir_en_chunks(cargar_documentos())


# ---------------------------------------------------------------------------
# 3) Ingesta a Pinecone
# ---------------------------------------------------------------------------

def _id_vector(fuente: str, chunk_id: int) -> str:
    """ID determinista y compatible con las reglas de Pinecone."""
    base = re.sub(r"[^0-9a-zA-Z_-]", "-", Path(fuente).stem)
    return f"{base}-{chunk_id}"


def preparar_registros(chunks: List[Document]) -> Tuple[List[str], List[Dict], List[str]]:
    """Convierte los chunks en (textos, metadatas, ids) listos para Pinecone."""
    textos: List[str] = []
    metadatas: List[Dict] = []
    ids: List[str] = []

    for chunk in chunks:
        metadata = {clave: valor for clave, valor in chunk.metadata.items() if valor is not None}
        metadata["text"] = chunk.page_content  # el texto viaja dentro del vector
        textos.append(chunk.page_content)
        metadatas.append(metadata)
        ids.append(_id_vector(str(metadata.get("fuente", "documento")), int(metadata.get("chunk_id", len(ids)))))

    return textos, metadatas, ids


def ingerir(chunks: List[Document], recrear: bool = False) -> None:
    """Sube los chunks (con sus embeddings) al indice y namespace configurados."""
    from langchain_pinecone import PineconeVectorStore  # import local: solo se usa al ingerir

    config = obtener_configuracion()
    indice = obtener_cliente().Index(config.index_name)

    if recrear:
        print(f"[..] Vaciando el namespace '{config.namespace}' antes de subir (--recrear)...")
        try:
            indice.delete(delete_all=True, namespace=config.namespace)
        except Exception as error:  # el namespace puede no existir todavia
            print(f"[INFO] No se pudo vaciar el namespace (probablemente ya estaba vacio): {error}")

    vectorstore = PineconeVectorStore(
        index=indice,
        embedding=obtener_embeddings(),
        namespace=config.namespace,
    )

    textos, metadatas, ids = preparar_registros(chunks)
    print(
        f"[..] Generando embeddings y subiendo {len(textos)} vectores a "
        f"'{config.index_name}' (namespace '{config.namespace}')..."
    )
    vectorstore.add_texts(texts=textos, metadatas=metadatas, ids=ids)

    estadisticas = indice.describe_index_stats()
    print(f"[OK] Ingesta completada. Estadisticas del indice: {estadisticas}")


def ejecutar(recrear: bool = False) -> None:
    """Paso 2 del pipeline: carga el dataset local y lo sube a Pinecone."""
    chunks = cargar_chunks()
    if not chunks:
        print("[ERROR] No hay documentos para ingerir. Revisa el directorio data/.")
        return
    ingerir(chunks, recrear=recrear)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingesta de data/ hacia un indice Serverless de Pinecone."
    )
    parser.add_argument(
        "--recrear",
        action="store_true",
        help="Vacia el namespace antes de subir (util si cambiaste el chunking o el dataset).",
    )
    argumentos = parser.parse_args()
    ejecutar(recrear=argumentos.recrear)


if __name__ == "__main__":
    main()
