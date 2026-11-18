# Lencería: stock y ventas

App de escritorio en un solo archivo (`app.py`). Usa solo Python estándar (tkinter + sqlite3), así que no hay que instalar nada aparte de Python.

## 1. Estructura de la base de datos

Archivo `lenceria.db`, que se crea solo junto a `app.py` (o junto al `.exe`) la primera vez que se abre la app.

```
categorias (id, nombre UNIQUE)      ─┐
talles     (id, nombre UNIQUE)      ─┼─<  productos (id, nombre, categoria_id FK, talle_id FK, color_id FK,
colores    (id, nombre UNIQUE)      ─┘               cantidad >= 0, precio > 0,
                                                     UNIQUE(nombre, talle_id, color_id))
                                                         │
                                                         └──<  ventas (id, fecha, producto_id FK, detalle,
                                                                        cantidad > 0, precio_unitario, total)
```

- **Cada fila de `productos` es una combinación producto + talle + color** con su propio stock y precio. "Corpiño Valentina M Negro" y "Corpiño Valentina L Rojo" son dos filas.
- Las claves foráneas de categoría, talle y color usan `ON DELETE RESTRICT`: no se puede borrar un color si hay productos que lo usan.
- `ventas.detalle` guarda una copia del nombre, talle y color, y `producto_id` pasa a `NULL` si se borra el producto. Así el historial queda intacto.
- Cada venta descuenta el stock y se registra dentro de **una sola transacción**: o pasan las dos cosas o no pasa ninguna.

## 2. Cómo ejecutarla

1. Instalá Python 3 desde https://www.python.org/downloads/ (en el instalador tildá **"Add Python to PATH"**).
2. Abrí una terminal en la carpeta `lenceria`.
3. Ejecutá:
   ```
   py app.py
   ```
   (en Mac/Linux: `python3 app.py`)

Opcional, para verificar que la lógica de stock y ventas funciona: `py app.py --test`

**Copia de seguridad:** todos los datos están en `lenceria.db`. Copiá ese archivo a un pendrive o a la nube cada tanto.

## 3. Uso rápido

| Sección | Qué hace |
|---|---|
| **Stock** | Alta, edición (doble clic) y baja de productos. Buscador y filtros. En rosa, lo que tiene 2 unidades o menos. |
| **Ventas** | Elegís el producto, la cantidad y tocás *Registrar venta*. Muestra el historial, lo vendido hoy, el total general y los totales por día. |
| **Presupuesto** | Valor total del stock (precio × cantidad), unidades, y desglose por categoría. Se recalcula cada vez que abrís la sección. |
| **Catálogos** | Agregar, renombrar y eliminar categorías, talles y colores. |

Atajos: `Ctrl+1` a `Ctrl+4` para cambiar de sección, `Enter` para guardar en los formularios, `Supr` para eliminar el producto seleccionado.

Para cargar el mismo producto en otro talle o color: *Nuevo producto*, elegí el nombre en la lista desplegable (se completan solos la categoría y el precio) y cambiá talle, color y cantidad.

Para poner el nombre de tu local, cambiá `NOMBRE_TIENDA` al principio de `app.py`.

## 4. Convertirla en .exe (opcional)

```
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name Lenceria app.py
```

El ejecutable queda en `dist\Lenceria.exe`. La base `lenceria.db` se crea **al lado del .exe**, así que poné el .exe en una carpeta fija (por ejemplo `Documentos\Lenceria`) y hacé copia de esa carpeta.
