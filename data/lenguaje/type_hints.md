# Anotaciones de tipo (type hints) en Python

Los *type hints* son anotaciones que declaran qué tipo de datos espera y devuelve cada parte del programa. Python no las exige en tiempo de ejecución, pero herramientas como `mypy`, `pyright` o Pylance las verifican de forma estática: actúan como documentación ejecutable que además detecta errores antes de correr el código.

## Anotaciones básicas

```python
def saludar(nombre: str) -> str:
    return f"Hola, {nombre}"

precios: list[float] = [1000.0, 2500.0]
configuracion: dict[str, int] = {"reintentos": 3}
```

Las colecciones modernas se anotan directamente en minúscula (`list[int]`, `dict[str, float]`, `tuple[int, str]`, `set[str]`), sin importar nada extra.

## Optional y None

Cuando un valor puede ser `None`, el tipo se declara con `Optional` o, desde Python 3.10, con la sintaxis `X | None` (equivalentes):

```python
from typing import Optional

def buscar(email: str, telefono: Optional[str] = None) -> Optional[str]:
    ...
```

Aquí `telefono: Optional[str] = None` declara dos cosas: el argumento **puede recibir `None` como valor** (no solo texto), y además tiene `None` por defecto, así que es opcional de pasar. Ojo con el nombre: `Optional[str]` no significa "argumento opcional", significa "tipo `str` o `None`". Un parámetro obligatorio también puede anotarse `Optional[str]` si exige que le pasen algo, aunque ese algo pueda ser `None` explícito.

```python
def renombrar(archivo: str, apodo: str | None = None) -> None:
    nombre_final = apodo if apodo is not None else archivo
```

## Uniones y tipos literales

La unión `A | B` expresa "uno u otro tipo", y `Literal` restringe a valores concretos:

```python
from typing import Literal

def conectar(modo: Literal["lectura", "escritura"]) -> None:
    ...
```

Si combinas más de dos tipos, la unión se encadena: `int | str | None`.

## TypedDict: diccionarios con estructura

`TypedDict` describe diccionarios con claves y tipos conocidos, muy útil para datos que llegan como JSON:

```python
from typing import TypedDict

class Usuario(TypedDict):
    nombre: str
    edad: int
    activo: bool

usuario: Usuario = {"nombre": "Ana", "edad": 31, "activo": True}
```

## Protocol: tipado estructural

Un `Protocol` declara un conjunto de métodos que un tipo debe cumplir, sin exigir herencia explícita (duck typing verificado por el chequeador):

```python
from typing import Protocol

class Exportable(Protocol):
    def exportar(self) -> str: ...

def publicar(item: Exportable) -> None:
    print(item.exportar())
```

Cualquier clase que tenga `exportar()` sirve, aunque nunca mencione a `Exportable`.

## Tipos invocables y genéricos

`Callable[[int], str]` describe funciones que reciben un entero y devuelven texto, útil para callbacks. En código genérico (una función que funciona con cualquier tipo) se usa `TypeVar`; y `Iterable[T]`, `Sequence[T]` permiten aceptar cualquier colección del tipo `T`.

## Herramientas y adopción gradual

El chequeo se corre con `mypy archivo.py`, `pyright` o directamente en el editor con Pylance, que subraya los problemas mientras escribes. Los proyectos grandes suelen adoptar hints de forma gradual: se anotan las funciones públicas primero y se activa un modo estricto por módulo. Con `from __future__ import annotations` las anotaciones se evalúan de forma diferida, lo que permite usar nombres aún no definidos y mejora el arranque. En resumen: más tipos declarados, menos bugs descubiertos en producción y mejor autocompletado en el editor.
