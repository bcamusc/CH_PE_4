# pandas: análisis de datos tabulares en Python

`pandas` es la biblioteca de referencia para manipular datos tabulares. Su estructura central es el `DataFrame`, una tabla con filas y columnas etiquetadas, y su complemento es la `Series`, una columna individual. La convención de importación es `import pandas as pd`.

## Carga y exploración

El punto de partida típico es leer un archivo, por ejemplo CSV o Parquet:

```python
import pandas as pd

df = pd.read_csv("ventas.csv")
df.head()        # primeras 5 filas
df.info()        # tipos de datos y valores no nulos
df.describe()    # estadísticas de las columnas numéricas
df.dtypes        # tipo de cada columna
df.shape         # (filas, columnas)
```

## Selección de datos

Para elegir columnas se usa el nombre; para filas, `loc` (por etiqueta) e `iloc` (por posición):

```python
df["ciudad"]                 # una columna (Series)
df[["ciudad", "ventas"]]     # varias columnas
df.loc[0:4, "ciudad"]        # etiquetas inclusivas
df.iloc[0:5, 0:2]            # posiciones exclusivas
df[df["ventas"] > 100000]    # filtro booleano
```

## Crear y transformar columnas

Las operaciones se aplican de forma vectorizada, sin bucles explícitos:

```python
df["ventas_netas"] = df["ventas"] * 0.81          # nueva columna
df["fecha"] = pd.to_datetime(df["fecha"])          # conversión de tipo
df["ciudad"] = df["ciudad"].astype("category")     # optimiza memoria si se repite
```

## Valores faltantes

Los nulos se detectan y tratan explícitamente para no ensuciar los resultados:

```python
df.isna().sum()                       # cuántos nulos por columna
df.dropna(subset=["ventas"])          # elimina filas con ventas nulas
df["ventas"].fillna(df["ventas"].median(), inplace=True)  # rellena con la mediana
```

## Agrupar y agregar con groupby

La operación estrella de pandas es `groupby`, que implementa el patrón dividir-aplicar-combinar: separa las filas por el valor de una columna, calcula algo dentro de cada grupo y combina los resultados. Se pueden calcular promedios por grupo, por ejemplo el promedio de ventas por ciudad:

```python
promedio_por_ciudad = df.groupby("ciudad")["ventas"].mean()
promedio_por_ciudad = promedio_por_ciudad.reset_index()
```

También se pueden pedir varias métricas a la vez con `agg`, o agrupar por más de una columna:

```python
resumen = df.groupby(["ciudad", "mes"]).agg(
    ventas_promedio=("ventas", "mean"),
    ventas_totales=("ventas", "sum"),
    transacciones=("ventas", "count"),
).reset_index()
```

## Combinar tablas

`merge` une dos DataFrames por una clave común, con la misma semántica que un JOIN de SQL:

```python
resultado = pd.merge(clientes, pedidos, on="cliente_id", how="left")
```

`how` acepta `inner`, `left`, `right` y `outer`. Para apilar tablas de la misma estructura verticalmente se usa `pd.concat([df1, df2])`.

## Ordenar y exportar

```python
df.sort_values("ventas", ascending=False, inplace=True)
df.to_csv("salida.csv", index=False)
df.to_parquet("salida.parquet")   # requiere pyarrow
```

`index=False` evita que el índice quede como una columna extra en el archivo.

## Rendimiento

Evita iterar filas con `for` y `iterrows()`: casi todo se puede expresar con operaciones vectorizadas (`df["a"] + df["b"]`) o con `df.apply(fn)`, que es más lento que una vectorización pero aceptable en columnas pequeñas. Usar el tipo `category` en columnas de texto repetido reduce el uso de memoria de forma notable. Y para pipelines grandes, Parquet es preferible a CSV: pesa menos y preserva los tipos de datos.
