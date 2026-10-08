# Manejo de excepciones en Python

Las excepciones son el mecanismo de Python para señalar que algo salió mal durante la ejecución. Saber manejarlas es la diferencia entre un programa que se cae con un error críptico y uno que reacciona con elegancia.

## try / except básico

El código riesgoso va dentro de `try` y la reacción va en `except`:

```python
try:
    edad = int("veinte")
except ValueError as error:
    print(f"Valor inválido: {error}")
```

Se pueden capturar varios tipos con cláusulas separadas, o con una tupla cuando la reacción es la misma:

```python
try:
    procesar(datos)
except (ValueError, TypeError):
    print("Datos mal formados")
except KeyError as error:
    print(f"Falta la clave {error}")
```

## else y finally

`try` puede llevar dos bloques adicionales y la diferencia entre ellos importa mucho:

- **`else`** se ejecuta **solo si no hubo ninguna excepción**. Sirve para poner código que no quieres que quede cubierto por el `try`: si ese código fallara, no quieres que las cláusulas `except` lo interpreten como un error de la operación original.
- **`finally`** se ejecuta **siempre**, haya excepción o no, incluso si hubo un `return` o un `break` en medio. Es el lugar para liberar recursos: cerrar archivos, conexiones o transacciones.

```python
try:
    conexion = abrir_conexion()
    datos = conexion.leer()
except TimeoutError:
    print("La conexión tardó demasiado")
else:
    print(f"Leídos {len(datos)} registros")   # solo si todo salió bien
finally:
    conexion.cerrar()                          # siempre, pase lo que pase
```

En resumen: `else` premia el camino feliz, `finally` garantiza la limpieza.

## raise y encadenamiento

Para señalar un error se usa `raise`. Dentro de un bloque `except`, un `raise` sin argumentos vuelve a lanzar la excepción actual, y `raise nueva from original` conserva la causa original en el traceback:

```python
def cargar_configuracion(ruta):
    try:
        return leer_archivo(ruta)
    except FileNotFoundError as error:
        raise RuntimeError(f"No se pudo cargar la configuración: {ruta}") from error
```

## Excepciones personalizadas

Cuando el dominio del programa tiene sus propios errores, conviene declarar excepciones propias. Heredar de `Exception` (no de `BaseException`) es la práctica correcta:

```python
class SaldoInsuficienteError(Exception):
    """La cuenta no tiene fondos para la operación."""

raise SaldoInsuficienteError("Saldo disponible: $5.000")
```

Con una jerarquía propia (`class ErrorDePago(Exception)` y subclases) se puede capturar por categoría, desde lo específico a lo general.

## Jerarquía y buenas prácticas

Todas las excepciones normales heredan de `Exception`, que a su vez hereda de `BaseException` (reservada para `KeyboardInterrupt` y `SystemExit`). De ahí se desprenden tres reglas de oro:

1. **Nunca uses un `except:` desnudo**, porque atrapa hasta la interrupción con Ctrl+C y oculta errores de programación. Captura `Exception` como máximo.
2. **No silencies errores**: un `except` que solo hace `pass` esconde la causa raíz y complica la depuración; registra o re-lanza.
3. **EAFP antes que LBYL**: en Python es idiomático intentar la operación y manejar la excepción (Easier to Ask Forgiveness than Permission) en vez de llenar el código de verificaciones previas.

## with y context managers

El patrón `try/finally` para liberar recursos es tan común que el lenguaje lo encapsula en el bloque `with`. Un archivo, una conexión o un lock garantizan su limpieza al salir del bloque, incluso si hubo excepción:

```python
with open("datos.txt", encoding="utf-8") as archivo:
    contenido = archivo.read()
# aquí el archivo ya está cerrado, haya error o no
```

Cuando escribas tus propias clases de recursos, implementa `__enter__` y `__exit__` para que también funcionen con `with`.
