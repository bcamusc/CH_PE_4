# pathlib: rutas de archivos orientadas a objetos

`pathlib` es el módulo de la biblioteca estándar para trabajar con rutas del sistema de archivos como objetos en lugar de cadenas de texto. Desde Python 3.6 es la forma recomendada por sobre `os.path`. La clase central es `Path`, disponible directamente con `from pathlib import Path`.

## Crear y combinar rutas

El operador `/` combina rutas de forma portable (funciona igual en Windows, macOS y Linux):

```python
from pathlib import Path

base = Path("data")
ruta = base / "bibliotecas" / "requests.md"
print(ruta)   # data/bibliotecas/requests.md (o con \ en Windows)
```

`Path.cwd()` entrega el directorio de trabajo actual, `Path.home()` el directorio del usuario, y `ruta.resolve()` convierte una ruta relativa en absoluta y normalizada.

## Partes de una ruta

Un objeto `Path` expone sus componentes como propiedades de solo lectura:

```python
ruta = Path("data/bibliotecas/requests.md")
ruta.name      # 'requests.md'
ruta.stem      # 'requests'   (nombre sin extensión)
ruta.suffix    # '.md'
ruta.parent    # 'data/bibliotecas'
ruta.parts     # ('data', 'bibliotecas', 'requests.md')
```

Con `with_name()` y `with_suffix()` se construyen rutas derivadas sin tocar el disco, por ejemplo para cambiar la extensión de `.txt` a `.md`.

## Comprobaciones

Antes de operar conviene verificar el estado del archivo o directorio:

```python
ruta.exists()    # ¿existe algo en esa ruta?
ruta.is_file()   # ¿es un archivo?
ruta.is_dir()    # ¿es un directorio?
```

## Leer y escribir texto

Para leer todo el contenido de un archivo de texto como una cadena, el atajo `read_text()` reemplaza el clásico `open(..., "r")` + `read()`:

```python
contenido = Path("notas.txt").read_text(encoding="utf-8")
```

Y para escribir:

```python
Path("salida.txt").write_text("hola mundo", encoding="utf-8")
```

Estos métodos leen y escriben **todo** el archivo de una sola vez; para archivos enormes o procesamiento por líneas conviene seguir usando `open()`. Para datos binarios existen `read_bytes()` y `write_bytes()`.

## Crear y eliminar

Los directorios se crean con `mkdir()`. Los argumentos `parents=True` crean las carpetas intermedias que falten y `exist_ok=True` evita el error si ya existe:

```python
Path("salidas/2026").mkdir(parents=True, exist_ok=True)
```

Para eliminar, `unlink()` borra un archivo (con `missing_ok=True` no falla si no existe) y `rmdir()` borra un directorio, pero solo si está vacío.

## Recorrer y buscar con patrones

`iterdir()` lista el contenido de un directorio y `glob()` filtra por patrón; `rglob()` hace lo mismo pero de forma recursiva por todos los subdirectorios:

```python
carpeta = Path("data")

for archivo in sorted(carpeta.glob("*.md")):
    print(archivo.name)

# Todos los Markdown, en cualquier subcarpeta:
for archivo in sorted(carpeta.rglob("*.md")):
    print(archivo)
```

Esta combinación es ideal para cargar datasets: `rglob("*.md")` encuentra cada documento sin importar cuán anidada esté la carpeta.

## Buenas prácticas

Usa `pathlib` en todo código nuevo en lugar de `os.path.join` y concatenaciones de cadenas. Para rutas que dependen de la ubicación del proyecto, construye desde el archivo actual: `Path(__file__).resolve().parents[1]` entrega la raíz del proyecto sin importar desde dónde se ejecute el script. Y evita rutas absolutas hardcodeadas: combina `Path` relativo con la raíz resuelta, como hacen los scripts de este repositorio.
