# Guía de la librería requests

`requests` es la librería HTTP más utilizada de Python: permite hacer peticiones a servicios web con muy poco código y maneja por ti los detalles de bajo nivel del protocolo HTTP. Se instala con `pip install requests` y no necesita configuración adicional para los casos comunes.

## Primera petición

Para hacer una petición GET basta con llamar a `requests.get()` y revisar la respuesta:

```python
import requests

respuesta = requests.get("https://api.github.com/repos/psf/requests", timeout=10)
print(respuesta.status_code)        # 200
print(respuesta.json()["name"])     # nombre del repositorio
```

El objeto `respuesta` concentra todo lo que devolvió el servidor: `status_code` (código HTTP), `text` (cuerpo como texto), `json()` (cuerpo decodificado desde JSON) y `headers` (cabeceras de la respuesta).

## Parámetros de consulta

Los parámetros de una URL se pasan con el argumento `params`, y requests se encarga de codificarlos y escaparlos:

```python
respuesta = requests.get(
    "https://api.github.com/search/repositories",
    params={"q": "language:python", "sort": "stars"},
    timeout=10,
)
```

## Cabeceras y autenticación

Las cabeceras personalizadas van en el diccionario `headers`, y la autenticación básica puede resolverse con el argumento `auth`:

```python
respuesta = requests.get(
    "https://api.ejemplo.cl/datos",
    headers={"Accept": "application/json", "Authorization": "Bearer TOKEN"},
    timeout=10,
)
```

Para autenticación HTTP Basic existe el atajo `auth=("usuario", "clave")`, que evita construir manualmente la cabecera.

## Envío de datos con POST

Para enviar un cuerpo JSON se usa el argumento `json=`; para formularios tradicionales, `data=`:

```python
respuesta = requests.post(
    "https://api.ejemplo.cl/productos",
    json={"nombre": "Teclado", "precio": 29990},
    timeout=10,
)
```

Con `json=` requests serializa el diccionario y define la cabecera `Content-Type: application/json` automáticamente.

## Manejo de errores con raise_for_status

Este es el punto más importante de la librería: **requests no lanza una excepción cuando el servidor responde con un error**. Una respuesta 404 o 500 llega como un objeto normal, y si no la revisas, tu programa continuará como si todo estuviera bien. El método `raise_for_status()` es el que convierte ese silencio en un error explícito: si el código de estado es 4xx (error del cliente) o 5xx (error del servidor), lanza una excepción `requests.exceptions.HTTPError`. Si el código es de éxito (2xx), no hace nada.

El patrón recomendado es:

```python
try:
    respuesta = requests.get(url, timeout=10)
    respuesta.raise_for_status()
except requests.exceptions.HTTPError as error:   # 4xx o 5xx
    print(f"El servidor respondió con error: {error}")
except requests.exceptions.Timeout:              # se superó el timeout
    print("La petición tardó demasiado")
except requests.exceptions.ConnectionError:      # problemas de red o DNS
    print("No se pudo conectar al servidor")
except requests.exceptions.RequestException as error:  # base común de todas
    print(f"Error inesperado: {error}")
```

Todas las excepciones de requests heredan de `requests.exceptions.RequestException`, así que ese `except` final actúa como red de seguridad. El argumento `timeout` también es clave: sin él, una petición puede quedarse colgada indefinidamente.

## Sesiones

Cuando haces muchas peticiones al mismo host, conviene usar una `Session`, que reutiliza la conexión TCP y mantiene cabeceras entre peticiones:

```python
sesion = requests.Session()
sesion.headers.update({"Authorization": "Bearer TOKEN"})
sesion.get("https://api.ejemplo.cl/usuarios", timeout=10)
sesion.get("https://api.ejemplo.cl/pedidos", timeout=10)
```

## Descarga de archivos grandes

Para descargas grandes se usa `stream=True` y se itera el contenido en bloques, evitando cargar todo en memoria:

```python
with requests.get(url, stream=True, timeout=30) as respuesta:
    respuesta.raise_for_status()
    with open("archivo.zip", "wb") as destino:
        for bloque in respuesta.iter_content(chunk_size=65536):
            destino.write(bloque)
```

## Redirecciones y metadatos

Por defecto requests sigue las redirecciones (3xx) automáticamente; con `allow_redirects=False` puedes inspeccionarlas. El historial queda en `respuesta.history` y el tiempo total de la petición en `respuesta.elapsed`. Para APIs, revisar `respuesta.url` final también es útil cuando hay redirecciones de por medio.
