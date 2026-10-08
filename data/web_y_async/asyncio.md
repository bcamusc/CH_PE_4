# asyncio: concurrencia cooperativa en Python

`asyncio` es el módulo de la biblioteca estándar para escribir código concurrente de un solo hilo: en lugar de lanzar varios hilos, un **event loop** administra muchas tareas y cambia entre ellas cuando cada una espera (por ejemplo, por una respuesta de red). Es ideal para programas limitados por espera de I/O, como clientes HTTP que consultan varias URLs.

## Modelo mental

Una función declarada con `async def` es una **corrutina**. Para ejecutarla hay que esperarla con `await` o agendarla en el loop. El punto de entrada habitual es `asyncio.run()`:

```python
import asyncio

async def saludar():
    await asyncio.sleep(1)   # cede el control al loop durante 1 segundo
    return "hola"

resultado = asyncio.run(saludar())
```

A diferencia de `time.sleep()`, que bloquea todo el programa, `asyncio.sleep()` deja que el loop siga ejecutando otras tareas mientras espera.

## Ejecutar varias tareas en paralelo con gather

`asyncio.gather()` recibe varias corrutinas, las ejecuta de forma concurrente y **espera a que todas terminen**, devolviendo una lista con los resultados en el mismo orden en que se pasaron:

```python
async def descargar(nombre, segundos):
    await asyncio.sleep(segundos)
    return f"{nombre} listo"

async def main():
    resultados = await asyncio.gather(
        descargar("api-1", 2),
        descargar("api-2", 1),
        descargar("api-3", 3),
    )
    print(resultados)   # ['api-1 listo', 'api-2 listo', 'api-3 listo'] tras ~3 s

asyncio.run(main())
```

Tres descargas de 2, 1 y 3 segundos tardan ~3 segundos en total, no 6, porque avanzan a la vez. Con `return_exceptions=True`, si una falla, los demás resultados igual se entregan (la excepción queda dentro de la lista).

## Agendar tareas con create_task

`gather` es lo más común cuando conoces todas las tareas de antemano. Si necesitas lanzar una tarea y seguir haciendo otras cosas, usa `create_task`:

```python
tarea = asyncio.create_task(descargar("fondo", 5))
# ... aqui puedes hacer otras cosas mientras la tarea avanza ...
resultado = await tarea
```

## Procesar resultados a medida que llegan

`asyncio.as_completed()` entrega las tareas terminadas en orden de finalización (no en el orden en que se lanzaron), útil cuando quieres procesar cada respuesta apenas esté lista:

```python
for futura in asyncio.as_completed([tarea_a, tarea_b]):
    resultado = await futura
    print(resultado)
```

## Timeouts y cancelación

Para poner un límite de tiempo a una corrutina se usa `asyncio.wait_for()`, que lanza `TimeoutError` si se supera:

```python
try:
    resultado = await asyncio.wait_for(descargar("lenta", 30), timeout=5)
except TimeoutError:
    print("se acabó el tiempo")
```

Las tareas también se pueden cancelar manualmente con `tarea.cancel()` cuando ya no son necesarias.

## Limitar la concurrencia

Lanzar miles de tareas a la vez puede saturar una API. Un `Semaphore` limita cuántas corren en simultáneo:

```python
limite = asyncio.Semaphore(10)

async def consultar(url):
    async with limite:
        return await pedir(url)
```

Solo diez corrutinas entrarán al bloque `async with` a la vez; el resto espera su turno.

## Errores comunes

El error clásico es llamar `time.sleep()` o una función bloqueante dentro de una corrutina: eso congela el loop completo y toda la concurrencia se pierde; usa `asyncio.sleep()` o bien `asyncio.to_thread(funcion_bloqueante)` para mover trabajo bloqueante a un hilo aparte. También conviene recordar que una corrutina no se ejecuta hasta que alguien la espera o la agenda: crearla sin `await` ni `create_task` no tiene ningún efecto.
