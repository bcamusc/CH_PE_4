# FastAPI: APIs modernas con validación automática

FastAPI es un framework para construir APIs HTTP en Python aprovechando las anotaciones de tipo y Pydantic. Su gran ventaja es que la validación de datos no se escribe a mano: se declara con tipos y el framework la aplica sola, devolviendo errores detallados cuando algo no calza.

## Primeros pasos

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def raiz():
    return {"mensaje": "hola"}
```

Se levanta con `uvicorn main:app --reload`. Además, FastAPI genera documentación interactiva automática en `/docs` (Swagger UI) y `/redoc` sin escribir nada extra.

## Parámetros de ruta y de consulta

Los parámetros que van dentro de la URL se declaran en el decorador; los de consulta (`?clave=valor`) son argumentos de la función con valor por defecto:

```python
@app.get("/productos/{producto_id}")
def obtener_producto(producto_id: int, incluir_precio: bool = False, limite: int = 10):
    ...
```

Si el cliente envía `producto_id="abc"`, FastAPI responde 422 con un mensaje de validación, sin código adicional de tu parte.

## Validación del cuerpo con modelos Pydantic

Este es el corazón de FastAPI. Para recibir datos JSON se define un modelo heredando de `pydantic.BaseModel` y se declara como tipo del parámetro. FastAPI **valida automáticamente el cuerpo de la petición** contra ese modelo: si falta un campo obligatorio, sobra un campo o un tipo no corresponde, responde con error 422 y el detalle exacto del problema; si todo está bien, entrega una instancia ya tipada y validada:

```python
from pydantic import BaseModel

class Producto(BaseModel):
    nombre: str
    precio: float
    stock: int = 0

@app.post("/productos", status_code=201)
def crear_producto(producto: Producto):
    # producto.nombre ya es str y producto.precio ya es float, validados
    return {"creado": producto.nombre}
```

No hace falta revisar `request.json()`, ni convertir tipos manualmente, ni responder errores de formato: el modelo declara el contrato y FastAPI lo hace cumplir.

## Respuestas y errores

El código de estado de éxito se declara en el decorador (`status_code=201`). Para errores de negocio se usa `HTTPException`, que corta la ejecución y devuelve la respuesta de error correspondiente:

```python
from fastapi import HTTPException

@app.get("/productos/{producto_id}")
def obtener_producto(producto_id: int):
    producto = buscar(producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto
```

Con `response_model` se declara la forma de la respuesta, y FastAPI filtra cualquier campo extra que no corresponda al contrato.

## async def vs def

Los endpoints declarados con `async def` corren en el event loop y permiten usar `await` (ideal para I/O de red o base de datos asíncrona). Los declarados con `def` normal se ejecutan en un pool de hilos, lo que permite usar librerías bloqueantes sin congelar la API. La elección depende de las librerías que uses por dentro.

## Organizar con routers

A medida que la API crece, los endpoints se agrupan en `APIRouter`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/productos", tags=["productos"])

@router.get("/")
def listar():
    ...

app.include_router(router)
```

El prefijo y las etiquetas se aplican a todas las rutas del router y quedan reflejados en la documentación.

## Dependencias con Depends

El sistema de dependencias inyecta recursos compartidos (sesiones de base de datos, usuario autenticado, configuración) en los endpoints:

```python
from fastapi import Depends

def obtener_sesion():
    sesion = crear_sesion()
    try:
        yield sesion
    finally:
        sesion.close()

@app.get("/pedidos")
def listar_pedidos(sesion=Depends(obtener_sesion)):
    return sesion.query(...)
```

FastAPI resuelve la dependencia por ti en cada petición y ejecuta el cierre al terminar.

## Despliegue

En producción se usa `uvicorn main:app --host 0.0.0.0 --port 8000`, o gunicorn con workers de uvicorn (`gunicorn -k uvicorn.workers.UvicornWorker`). Como FastAPI es ASGI, también corre en plataformas serverless siempre que respeten esa interfaz.
