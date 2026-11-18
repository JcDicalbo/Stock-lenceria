"""Lencería: gestión de stock y ventas.

Ejecutar:        py app.py
Autoverificación: py app.py --test
Sin dependencias: solo librería estándar (tkinter + sqlite3).
"""
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

NOMBRE_TIENDA = "Lencería"  # cambiá esto por el nombre de tu local
STOCK_BAJO = 2              # se resalta todo lo que tenga esta cantidad o menos

# La base vive junto al programa (también cuando está empaquetado como .exe)
BASE = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
DB = BASE / "lenceria.db"

# ---------------------------------------------------------------- base de datos

ESQUEMA = """
CREATE TABLE IF NOT EXISTS categorias (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS talles     (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE COLLATE NOCASE);
CREATE TABLE IF NOT EXISTS colores    (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE COLLATE NOCASE);

-- Cada fila es una combinación producto + talle + color con su propio stock y precio
CREATE TABLE IF NOT EXISTS productos (
    id           INTEGER PRIMARY KEY,
    nombre       TEXT    NOT NULL,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id) ON DELETE RESTRICT,
    talle_id     INTEGER NOT NULL REFERENCES talles(id)     ON DELETE RESTRICT,
    color_id     INTEGER NOT NULL REFERENCES colores(id)    ON DELETE RESTRICT,
    cantidad     INTEGER NOT NULL CHECK (cantidad >= 0),
    precio       REAL    NOT NULL CHECK (precio > 0),
    UNIQUE (nombre, talle_id, color_id)
);

CREATE TABLE IF NOT EXISTS ventas (
    id              INTEGER PRIMARY KEY,
    fecha           TEXT    NOT NULL,  -- 'AAAA-MM-DD HH:MM:SS'
    producto_id     INTEGER REFERENCES productos(id) ON DELETE SET NULL,
    detalle         TEXT    NOT NULL,  -- copia de nombre/talle/color: el historial sobrevive si se borra el producto
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL    NOT NULL,
    total           REAL    NOT NULL
);
"""

SEMILLA = {
    "categorias": ["Corpiños", "Bombachas", "Medias", "Camisones", "Pijamas"],
    "talles": ["S", "M", "L", "XL"],
    "colores": ["Negro", "Blanco", "Rojo", "Nude", "Rosa"],
}

CONSULTA_PRODUCTOS = """
SELECT p.id, p.nombre, c.nombre, t.nombre, co.nombre, p.cantidad, p.precio
FROM productos p
JOIN categorias c ON c.id = p.categoria_id
JOIN talles t     ON t.id = p.talle_id
JOIN colores co   ON co.id = p.color_id
"""


def conectar(ruta=DB):
    con = sqlite3.connect(ruta)
    con.execute("PRAGMA foreign_keys = ON")
    nueva = not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'categorias'").fetchone()
    con.executescript(ESQUEMA)
    if nueva:
        with con:
            for tabla, valores in SEMILLA.items():
                con.executemany(f"INSERT INTO {tabla}(nombre) VALUES (?)", [(v,) for v in valores])
    return con


def nombres(con, tabla):
    return [r[0] for r in con.execute(f"SELECT nombre FROM {tabla} ORDER BY id")]


def id_de(con, tabla, nombre):
    return con.execute(f"SELECT id FROM {tabla} WHERE nombre = ?", (nombre,)).fetchone()[0]


def vender(con, producto_id, cantidad):
    """Descuenta el stock y guarda la venta en una sola transacción. Devuelve el total cobrado."""
    with con:
        fila = con.execute(
            "SELECT p.nombre, t.nombre, c.nombre, p.cantidad, p.precio FROM productos p "
            "JOIN talles t ON t.id = p.talle_id JOIN colores c ON c.id = p.color_id WHERE p.id = ?",
            (producto_id,)).fetchone()
        if fila is None:
            raise ValueError("Ese producto ya no existe.")
        nombre, talle, color, stock, precio = fila
        if cantidad > stock:
            raise ValueError(f"No alcanza el stock: de {nombre} ({talle}, {color}) "
                             f"quedan {stock} y querés vender {cantidad}.")
        con.execute("UPDATE productos SET cantidad = cantidad - ? WHERE id = ?", (cantidad, producto_id))
        total = round(precio * cantidad, 2)
        con.execute(
            "INSERT INTO ventas(fecha, producto_id, detalle, cantidad, precio_unitario, total) VALUES (?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), producto_id,
             f"{nombre} ({talle}, {color})", cantidad, precio, total))
    return total


# ---------------------------------------------------------------- formato y validación

def pesos(x):
    """1234.5 -> '$ 1.234,50' (formato argentino)."""
    return "$ " + f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def numero(texto, que):
    """Precio positivo. Acepta '1500', '1500,50' y '1.500,50'."""
    t = texto.strip().replace("$", "").replace(" ", "")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        raise ValueError(f"{que} tiene que ser un número, por ejemplo 1500 o 1500,50.") from None
    if not 0 < v < 1e12:  # también descarta nan e infinito
        raise ValueError(f"{que} tiene que ser mayor que cero.")
    return round(v, 2)


def entero(texto, que, minimo):
    try:
        v = int(texto.strip())
    except ValueError:
        raise ValueError(f"{que} tiene que ser un número entero, sin decimales.") from None
    if v < minimo:
        raise ValueError(f"{que} tiene que ser {minimo} o más.")
    return v


def dmy(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}"


# ---------------------------------------------------------------- estilo visual

C = dict(
    fondo="#F6EEF0", panel="#FFFFFF", fila_alt="#FBF6F7", linea="#E7D7DD",
    lateral="#3B2433", lateral_act="#553449", lateral_txt="#D9C3CE",
    acento="#A8536E", acento_osc="#8C405A",
    tinta="#2E1F28", suave="#8A7480",
    alerta_bg="#FBE1E3", alerta_txt="#9B2C3C",
)
SERIF, SANS = "Constantia", "Segoe UI"
ESCALA = 1.0  # se ajusta al DPI de la pantalla al arrancar


def px(n):
    return int(n * ESCALA)


def estilos(raiz):
    s = ttk.Style(raiz)
    s.theme_use("clam")
    s.configure(".", background=C["fondo"], foreground=C["tinta"], font=(SANS, 10),
                bordercolor=C["linea"], lightcolor=C["linea"], darkcolor=C["linea"],
                troughcolor=C["panel"], focuscolor=C["acento"], selectbackground=C["acento"])
    s.configure("Panel.TFrame", background=C["panel"])
    s.configure("Titulo.TLabel", font=(SERIF, 26))
    s.configure("Subtitulo.TLabel", font=(SERIF, 16))
    s.configure("Bajada.TLabel", foreground=C["suave"])
    s.configure("Rotulo.TLabel", foreground=C["suave"], font=(SANS, 9))
    s.configure("Cifra.TLabel", font=(SERIF, 48), foreground=C["acento"])
    s.configure("CifraChica.TLabel", font=(SERIF, 22))
    s.configure("Aviso.TLabel", foreground=C["acento"], font=(SANS, 10, "bold"))

    s.configure("TButton", background=C["panel"], padding=(14, 7), relief="flat")
    s.map("TButton", background=[("active", C["fila_alt"])], bordercolor=[("focus", C["acento"])])
    s.configure("Primario.TButton", background=C["acento"], foreground="white",
                bordercolor=C["acento"], font=(SANS, 10, "bold"))
    s.map("Primario.TButton", background=[("active", C["acento_osc"])],
          bordercolor=[("focus", C["tinta"])])
    s.configure("Peligro.TButton", foreground=C["alerta_txt"])

    for w in ("TEntry", "TCombobox", "TSpinbox"):
        s.configure(w, fieldbackground=C["panel"], background=C["panel"], padding=6, arrowcolor=C["suave"])
        s.map(w, bordercolor=[("focus", C["acento"])], lightcolor=[("focus", C["acento"])])
    s.map("TCombobox", fieldbackground=[("readonly", C["panel"])],
          selectbackground=[("readonly", C["panel"])], selectforeground=[("readonly", C["tinta"])],
          bordercolor=[("focus", C["acento"])], lightcolor=[("focus", C["acento"])])
    raiz.option_add("*TCombobox*Listbox.font", (SANS, 10))
    raiz.option_add("*TCombobox*Listbox.selectBackground", C["acento"])

    s.configure("Treeview", background=C["panel"], fieldbackground=C["panel"],
                rowheight=px(32), borderwidth=0, font=(SANS, 10))
    s.map("Treeview", background=[("selected", C["acento"])], foreground=[("selected", "white")])
    s.configure("Treeview.Heading", background=C["panel"], foreground=C["suave"],
                font=(SANS, 9, "bold"), relief="flat", padding=(6, 8))
    s.map("Treeview.Heading", background=[("active", C["fila_alt"])])
    s.configure("Vertical.TScrollbar", background=C["linea"], arrowcolor=C["suave"], bordercolor=C["panel"])


# ---------------------------------------------------------------- piezas de interfaz

def campo(padre, texto, crear, side="left"):
    """Rótulo chico arriba y el control abajo. `crear` recibe el contenedor y devuelve el control."""
    f = ttk.Frame(padre)
    f.pack(side=side, fill="x", padx=(0, 12) if side == "left" else 0, pady=(0, 12))
    ttk.Label(f, text=texto, style="Rotulo.TLabel").pack(anchor="w", pady=(0, 3))
    w = crear(f)
    w.pack(fill="x")
    return w


def tabla(padre, columnas, alto=10):
    """columnas: [(id, título, ancho, alineación)]. Devuelve (marco, treeview)."""
    marco = ttk.Frame(padre, style="Panel.TFrame", padding=1)
    tv = ttk.Treeview(marco, columns=[c[0] for c in columnas], show="headings", selectmode="browse", height=alto)
    for cid, titulo, ancho, alin in columnas:
        tv.heading(cid, text=titulo, anchor=alin)
        tv.column(cid, width=px(ancho), minwidth=px(50), anchor=alin)
    sb = ttk.Scrollbar(marco, orient="vertical", command=tv.yview)
    tv.configure(yscrollcommand=sb.set)
    tv.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tv.tag_configure("par", background=C["fila_alt"])
    tv.tag_configure("bajo", background=C["alerta_bg"], foreground=C["alerta_txt"])
    return marco, tv


def llenar(tv, filas, tag=lambda i, fila: "par" if i % 2 else ""):
    tv.delete(*tv.get_children())
    for i, (iid, *valores) in enumerate(filas):
        tv.insert("", "end", iid=iid, values=valores, tags=(tag(i, valores),))


class Pagina(ttk.Frame):
    def __init__(self, padre, app, titulo, bajada):
        super().__init__(padre)
        self.app, self.con = app, app.con
        ttk.Label(self, text=titulo, style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(self, text=bajada, style="Bajada.TLabel").pack(anchor="w", pady=(0, 20))

    def refrescar(self):
        pass


# ---------------------------------------------------------------- 1. Stock

class PaginaStock(Pagina):
    def __init__(self, padre, app):
        super().__init__(padre, app, "Stock",
                         "Cada fila es un producto en un talle y color, con su propio stock.")
        barra = ttk.Frame(self)
        barra.pack(fill="x")
        self.buscar = tk.StringVar()
        self.buscar.trace_add("write", lambda *_: self.refrescar())
        campo(barra, "Buscar", lambda f: ttk.Entry(f, textvariable=self.buscar, width=26))
        self.filtros = []
        for rotulo, tbl, todos in (("Categoría", "categorias", "Todas"),
                                   ("Talle", "talles", "Todos"), ("Color", "colores", "Todos")):
            cb = campo(barra, rotulo, lambda f: ttk.Combobox(f, state="readonly", width=13))
            cb.set(todos)
            cb.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
            self.filtros.append((cb, tbl, todos))

        botones = ttk.Frame(barra)
        botones.pack(side="right", anchor="s", pady=(0, 12))
        ttk.Button(botones, text="Eliminar", style="Peligro.TButton", command=self.eliminar).pack(side="right")
        ttk.Button(botones, text="Editar", command=self.editar).pack(side="right", padx=8)
        ttk.Button(botones, text="Nuevo producto", style="Primario.TButton",
                   command=lambda: dialogo_producto(self)).pack(side="right")

        marco, self.tv = tabla(self, [
            ("nombre", "Producto", 240, "w"), ("cat", "Categoría", 120, "w"), ("talle", "Talle", 60, "center"),
            ("color", "Color", 100, "w"), ("stock", "Stock", 70, "e"), ("precio", "Precio", 110, "e"),
            ("subtotal", "Subtotal", 120, "e")])
        marco.pack(fill="both", expand=True)
        self.tv.bind("<Double-1>", lambda e: self.editar())
        self.tv.bind("<Delete>", lambda e: self.eliminar())
        self.pie = ttk.Label(self, style="Bajada.TLabel")
        self.pie.pack(anchor="w", pady=(10, 0))

    def refrescar(self):
        valores = []
        for cb, tbl, todos in self.filtros:
            cb["values"] = [todos] + nombres(self.con, tbl)
            if cb.get() not in cb["values"]:
                cb.set(todos)
            v = "" if cb.get() == todos else cb.get()
            valores += [v, v]
        filas = self.con.execute(
            CONSULTA_PRODUCTOS +
            " WHERE (p.nombre || ' ' || c.nombre || ' ' || co.nombre) LIKE ?"
            " AND (? = '' OR c.nombre = ?) AND (? = '' OR t.nombre = ?) AND (? = '' OR co.nombre = ?)"
            " ORDER BY p.nombre, t.id, co.nombre",
            [f"%{self.buscar.get().strip()}%", *valores]).fetchall()
        llenar(self.tv, [(pid, n, c, t, co, q, pesos(p), pesos(q * p)) for pid, n, c, t, co, q, p in filas],
               tag=lambda i, v: "bajo" if v[4] <= STOCK_BAJO else ("par" if i % 2 else ""))
        bajos = sum(f[5] <= STOCK_BAJO for f in filas)
        aviso = f"  {bajos} con stock bajo ({STOCK_BAJO} o menos), marcados en rosa." if bajos else ""
        self.pie.config(text=f"{len(filas)} productos en la lista.{aviso}")

    def elegido(self):
        sel = self.tv.selection()
        if not sel:
            messagebox.showinfo("Elegí un producto", "Primero hacé clic en un producto de la lista.", parent=self)
            return None
        return int(sel[0])

    def editar(self):
        pid = self.elegido()
        if pid is not None:
            dialogo_producto(self, pid)

    def eliminar(self):
        pid = self.elegido()
        if pid is None:
            return
        n, _, t, co = self.tv.item(pid, "values")[:4]
        if messagebox.askyesno("Eliminar producto",
                               f"¿Eliminar {n} ({t}, {co})?\n\nNo se puede deshacer. "
                               "Las ventas ya registradas se conservan en el historial.",
                               icon="warning", parent=self):
            with self.con:
                self.con.execute("DELETE FROM productos WHERE id = ?", (pid,))
            self.refrescar()


def dialogo_producto(pagina, pid=None):
    con = pagina.con
    d = tk.Toplevel(pagina)
    d.title("Editar producto" if pid else "Nuevo producto")
    d.configure(bg=C["fondo"])
    d.transient(pagina.winfo_toplevel())
    d.resizable(False, False)
    cuerpo = ttk.Frame(d, padding=28)
    cuerpo.pack(fill="both")
    ttk.Label(cuerpo, text=d.title(), style="Subtitulo.TLabel").pack(anchor="w", pady=(0, 16))

    # nombres ya cargados: elegir uno sirve para sumar otro talle/color sin reescribir todo
    previos = {n: (c, p) for _, n, c, _, _, _, p in con.execute(CONSULTA_PRODUCTOS)}
    nombre = campo(cuerpo, "Nombre", lambda f: ttk.Combobox(f, values=sorted(previos), width=40), "top")
    cat = campo(cuerpo, "Categoría", lambda f: ttk.Combobox(
        f, values=nombres(con, "categorias"), state="readonly"), "top")
    fila = ttk.Frame(cuerpo)
    fila.pack(fill="x")
    talle = campo(fila, "Talle", lambda f: ttk.Combobox(f, values=nombres(con, "talles"), state="readonly", width=12))
    color = campo(fila, "Color", lambda f: ttk.Combobox(f, values=nombres(con, "colores"), state="readonly", width=16))
    fila = ttk.Frame(cuerpo)
    fila.pack(fill="x")
    cant = campo(fila, "Cantidad en stock", lambda f: ttk.Entry(f, width=14))
    precio = campo(fila, "Precio unitario ($)", lambda f: ttk.Entry(f, width=16))

    def autocompletar(_):
        c, p = previos.get(nombre.get(), (None, None))
        if c:
            cat.set(c)
            precio.delete(0, "end")
            precio.insert(0, f"{p:.2f}".replace(".", ","))
    nombre.bind("<<ComboboxSelected>>", autocompletar)

    if pid:
        _, n, c, t, co, q, p = con.execute(CONSULTA_PRODUCTOS + " WHERE p.id = ?", (pid,)).fetchone()
        nombre.set(n), cat.set(c), talle.set(t), color.set(co)
        cant.insert(0, q)
        precio.insert(0, f"{p:.2f}".replace(".", ","))

    def guardar():
        n = nombre.get().strip()
        try:
            if not n:
                raise ValueError("Escribí el nombre del producto.")
            if not (cat.get() and talle.get() and color.get()):
                raise ValueError("Elegí categoría, talle y color.")
            q = entero(cant.get(), "La cantidad", 0)
            p = numero(precio.get(), "El precio")
        except ValueError as e:
            messagebox.showerror("Revisá los datos", str(e), parent=d)
            return
        datos = (n, id_de(con, "categorias", cat.get()), id_de(con, "talles", talle.get()),
                 id_de(con, "colores", color.get()), q, p)
        try:
            with con:
                if pid:
                    con.execute("UPDATE productos SET nombre=?, categoria_id=?, talle_id=?, color_id=?, "
                                "cantidad=?, precio=? WHERE id=?", (*datos, pid))
                else:
                    con.execute("INSERT INTO productos(nombre, categoria_id, talle_id, color_id, cantidad, precio) "
                                "VALUES (?,?,?,?,?,?)", datos)
        except sqlite3.IntegrityError:
            messagebox.showerror("Producto repetido",
                                 f"Ya existe {n} en talle {talle.get()} y color {color.get()}.\n"
                                 "Editá ese producto para cambiar su stock.", parent=d)
            return
        d.destroy()
        pagina.refrescar()

    botones = ttk.Frame(cuerpo)
    botones.pack(fill="x", pady=(8, 0))
    ttk.Button(botones, text="Guardar", style="Primario.TButton", command=guardar).pack(side="right")
    ttk.Button(botones, text="Cancelar", command=d.destroy).pack(side="right", padx=8)
    d.bind("<Return>", lambda e: guardar())
    d.bind("<Escape>", lambda e: d.destroy())
    nombre.focus_set()
    d.grab_set()


# ---------------------------------------------------------------- 2. Presupuesto

class PaginaPresupuesto(Pagina):
    def __init__(self, padre, app):
        super().__init__(padre, app, "Presupuesto",
                         "Lo que vale todo el stock del local, a precio de venta.")
        self.valor = ttk.Label(self, style="Cifra.TLabel")
        self.valor.pack(anchor="w")
        self.detalle = ttk.Label(self, style="Bajada.TLabel", font=(SANS, 11))
        self.detalle.pack(anchor="w")
        ttk.Label(self, text="Por categoría", style="Subtitulo.TLabel").pack(anchor="w", pady=(36, 12))
        self.lienzo = tk.Canvas(self, bg=C["fondo"], highlightthickness=0)
        self.lienzo.pack(fill="both", expand=True)
        self.lienzo.bind("<Configure>", lambda e: self.dibujar())
        self.datos = []

    def refrescar(self):
        self.datos = self.con.execute(
            "SELECT c.nombre, COALESCE(SUM(p.cantidad), 0), COALESCE(SUM(p.cantidad * p.precio), 0) "
            "FROM categorias c LEFT JOIN productos p ON p.categoria_id = c.id "
            "GROUP BY c.id ORDER BY 3 DESC, c.nombre").fetchall()
        n_prod = self.con.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
        unidades = sum(u for _, u, _ in self.datos)
        self.valor.config(text=pesos(sum(v for *_, v in self.datos)))
        self.detalle.config(text=f"{unidades} unidades en {n_prod} productos")
        self.dibujar()

    def dibujar(self):
        cv = self.lienzo
        cv.delete("all")
        ancho = cv.winfo_width()
        maximo = max([v for *_, v in self.datos], default=0) or 1
        x0, largo = px(150), max(ancho - px(150) - px(260), px(60))
        for i, (nombre, unid, valor) in enumerate(self.datos):
            y = i * px(40) + px(12)
            cv.create_text(0, y, text=nombre, anchor="w", font=(SANS, 11), fill=C["tinta"])
            cv.create_rectangle(x0, y - px(6), x0 + largo, y + px(6), fill=C["linea"], width=0)
            if valor:
                cv.create_rectangle(x0, y - px(6), x0 + largo * valor / maximo, y + px(6), fill=C["acento"], width=0)
            cv.create_text(x0 + largo + px(18), y, text=pesos(valor), anchor="w",
                           font=(SANS, 11, "bold"), fill=C["tinta"])
            cv.create_text(ancho - 2, y, text=f"{unid} u.", anchor="e", font=(SANS, 10), fill=C["suave"])


# ---------------------------------------------------------------- 3. Ventas

class PaginaVentas(Pagina):
    def __init__(self, padre, app):
        super().__init__(padre, app, "Ventas", "Al registrar una venta, el stock se descuenta solo.")
        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)

        izq = ttk.Frame(cuerpo, width=px(340))
        izq.pack(side="left", fill="y", padx=(0, 28))
        izq.pack_propagate(False)
        ttk.Label(izq, text="Nueva venta", style="Subtitulo.TLabel").pack(anchor="w", pady=(0, 12))
        self.filtro = tk.StringVar()
        self.filtro.trace_add("write", lambda *_: self.cargar_productos())
        campo(izq, "Buscar producto", lambda f: ttk.Entry(f, textvariable=self.filtro), "top")
        self.prod = campo(izq, "Producto (solo los que tienen stock)",
                          lambda f: ttk.Combobox(f, state="readonly"), "top")
        self.cant = campo(izq, "Cantidad", lambda f: ttk.Spinbox(
            f, from_=1, to=9999, width=8, command=self.resumen), "top")
        self.cant.set(1)
        self.prod.bind("<<ComboboxSelected>>", lambda e: self.resumen())
        self.cant.bind("<KeyRelease>", lambda e: self.resumen())
        self.total = ttk.Label(izq, style="CifraChica.TLabel")
        self.total.pack(anchor="w")
        self.unitario = ttk.Label(izq, style="Bajada.TLabel")
        self.unitario.pack(anchor="w", pady=(0, 12))
        ttk.Button(izq, text="Registrar venta", style="Primario.TButton", command=self.registrar).pack(fill="x")
        self.aviso = ttk.Label(izq, style="Aviso.TLabel", wraplength=px(330))
        self.aviso.pack(anchor="w", pady=(8, 0))
        ttk.Label(izq, text="Totales por día", style="Subtitulo.TLabel").pack(anchor="w", pady=(16, 8))
        marco, self.dias = tabla(izq, [("dia", "Día", 100, "w"), ("unid", "Unidades", 80, "e"),
                                       ("total", "Total", 120, "e")], alto=5)
        marco.pack(fill="both", expand=True)

        der = ttk.Frame(cuerpo)
        der.pack(side="left", fill="both", expand=True)
        cifras = ttk.Frame(der)
        cifras.pack(fill="x", pady=(0, 14))
        self.hoy, self.general = (self.cifra(cifras, t) for t in ("Vendido hoy", "Vendido en total"))
        marco, self.hist = tabla(der, [("fecha", "Fecha", 95, "w"), ("hora", "Hora", 60, "w"),
                                       ("detalle", "Producto", 260, "w"), ("cant", "Cant.", 55, "e"),
                                       ("total", "Total cobrado", 120, "e")])
        marco.pack(fill="both", expand=True)
        self.opciones = {}

    def cifra(self, padre, rotulo):
        f = ttk.Frame(padre)
        f.pack(side="left", padx=(0, 48))
        ttk.Label(f, text=rotulo, style="Rotulo.TLabel").pack(anchor="w")
        valor = ttk.Label(f, style="CifraChica.TLabel")
        valor.pack(anchor="w")
        return valor

    def cargar_productos(self):
        filas = self.con.execute(
            CONSULTA_PRODUCTOS + " WHERE p.cantidad > 0 AND (p.nombre || ' ' || c.nombre || ' ' || co.nombre) LIKE ?"
            " ORDER BY p.nombre, t.id, co.nombre", (f"%{self.filtro.get().strip()}%",)).fetchall()
        self.opciones = {f"{n} ({t}, {co}), quedan {q}": (pid, p) for pid, n, _, t, co, q, p in filas}
        self.prod["values"] = list(self.opciones)
        if self.prod.get() not in self.opciones:
            # tras una venta el texto cambia ("quedan N"): conservar la elección por id
            anterior = getattr(self, "_pid", None)
            self.prod.set(next((k for k, v in self.opciones.items() if v[0] == anterior), ""))
        self.resumen()

    def resumen(self):
        pid, precio = self.opciones.get(self.prod.get(), (None, 0))
        self._pid = pid
        try:
            q = int(self.cant.get())
        except ValueError:
            q = 0
        self.total.config(text=pesos(precio * max(q, 0)) if pid else "")
        self.unitario.config(text=f"{q} × {pesos(precio)}" if pid else "Elegí un producto para ver el total.")

    def registrar(self):
        pid, _ = self.opciones.get(self.prod.get(), (None, 0))
        try:
            if pid is None:
                raise ValueError("Elegí el producto que vendiste.")
            total = vender(self.con, pid, entero(self.cant.get(), "La cantidad", 1))
        except ValueError as e:
            messagebox.showerror("No se registró la venta", str(e), parent=self)
            return
        self.aviso.config(text=f"Venta registrada: {pesos(total)}")
        self.cant.set(1)
        self.refrescar()

    def refrescar(self):
        self.cargar_productos()
        suma = "SELECT COALESCE(SUM(total), 0) FROM ventas"
        self.hoy.config(text=pesos(self.con.execute(suma + " WHERE substr(fecha, 1, 10) = ?",
                                                    (date.today().isoformat(),)).fetchone()[0]))
        self.general.config(text=pesos(self.con.execute(suma).fetchone()[0]))
        # shortcut: carga todo el historial; si pasa de decenas de miles de ventas, paginar
        llenar(self.hist, [(i, dmy(f), f[11:16], d, q, pesos(t)) for i, f, d, q, t in self.con.execute(
            "SELECT id, fecha, detalle, cantidad, total FROM ventas ORDER BY id DESC")])
        llenar(self.dias, [(d, dmy(d), u, pesos(t)) for d, u, t in self.con.execute(
            "SELECT substr(fecha, 1, 10) d, SUM(cantidad), SUM(total) FROM ventas GROUP BY d ORDER BY d DESC")])


# ---------------------------------------------------------------- 4. Catálogos

class PaginaCatalogos(Pagina):
    def __init__(self, padre, app):
        super().__init__(padre, app, "Catálogos",
                         "Las opciones que aparecen al cargar un producto. Elegí una para renombrarla o eliminarla.")
        fila = ttk.Frame(self)
        fila.pack(fill="both", expand=True)
        fila.rowconfigure(0, weight=1)
        self.listas = {}
        for i, (tbl, titulo) in enumerate((("categorias", "Categorías"), ("talles", "Talles"), ("colores", "Colores"))):
            col = ttk.Frame(fila)
            col.grid(row=0, column=i, sticky="nsew", padx=(0, 24) if i < 2 else 0)
            fila.columnconfigure(i, weight=1, uniform="cat")
            ttk.Label(col, text=titulo, style="Subtitulo.TLabel").pack(anchor="w")
            lb = tk.Listbox(col, font=(SANS, 11), bg=C["panel"], fg=C["tinta"], relief="flat", bd=10,
                            highlightthickness=1, highlightbackground=C["linea"], highlightcolor=C["acento"],
                            selectbackground=C["acento"], selectforeground="white", activestyle="none",
                            exportselection=False)
            lb.pack(fill="both", expand=True, pady=(8, 10))
            ent = ttk.Entry(col)
            ent.pack(fill="x")
            lb.bind("<<ListboxSelect>>", lambda e, lb=lb, ent=ent: lb.curselection() and (
                ent.delete(0, "end"), ent.insert(0, lb.get(lb.curselection()[0]))))
            ent.bind("<Return>", lambda e, t=tbl: self.agregar(t))
            bot = ttk.Frame(col)
            bot.pack(fill="x", pady=(8, 0))
            ttk.Button(bot, text="Agregar", style="Primario.TButton", command=lambda t=tbl: self.agregar(t)).pack(side="left")
            ttk.Button(bot, text="Renombrar", command=lambda t=tbl: self.renombrar(t)).pack(side="left", padx=6)
            ttk.Button(bot, text="Eliminar", style="Peligro.TButton", command=lambda t=tbl: self.eliminar(t)).pack(side="left")
            self.listas[tbl] = (lb, ent)

    def refrescar(self):
        for tbl, (lb, _) in self.listas.items():
            lb.delete(0, "end")
            lb.insert("end", *nombres(self.con, tbl))

    def elegido(self, tbl):
        lb, ent = self.listas[tbl]
        sel = lb.curselection()
        if not sel:
            messagebox.showinfo("Elegí una opción", "Primero hacé clic en una opción de la lista.", parent=self)
            return None, ent
        return lb.get(sel[0]), ent

    def guardar(self, sql, params, nombre):
        try:
            with self.con:
                self.con.execute(sql, params)
        except sqlite3.IntegrityError:
            messagebox.showerror("Ya existe", f"«{nombre}» ya está en la lista.", parent=self)
            return
        self.listas_limpiar()

    def listas_limpiar(self):
        for _, ent in self.listas.values():
            ent.delete(0, "end")
        self.refrescar()

    def agregar(self, tbl):
        nombre = self.listas[tbl][1].get().strip()
        if not nombre:
            messagebox.showinfo("Falta el nombre", "Escribí el nombre en el campo de abajo y tocá Agregar.", parent=self)
            return
        self.guardar(f"INSERT INTO {tbl}(nombre) VALUES (?)", (nombre,), nombre)

    def renombrar(self, tbl):
        viejo, ent = self.elegido(tbl)
        nuevo = ent.get().strip()
        if viejo is None:
            return
        if not nuevo or nuevo == viejo:
            messagebox.showinfo("Escribí el nombre nuevo", f"Cambiá «{viejo}» en el campo de abajo y tocá Renombrar.",
                                parent=self)
            return
        self.guardar(f"UPDATE {tbl} SET nombre = ? WHERE nombre = ?", (nuevo, viejo), nuevo)

    def eliminar(self, tbl):
        nombre, _ = self.elegido(tbl)
        if nombre is None or not messagebox.askyesno("Eliminar", f"¿Eliminar «{nombre}»?", icon="warning", parent=self):
            return
        try:
            with self.con:
                self.con.execute(f"DELETE FROM {tbl} WHERE nombre = ?", (nombre,))
        except sqlite3.IntegrityError:
            messagebox.showerror("No se puede eliminar",
                                 f"Hay productos cargados con «{nombre}». Cambiales esa opción "
                                 "o eliminalos antes.", parent=self)
            return
        self.listas_limpiar()


# ---------------------------------------------------------------- ventana principal

class App(tk.Tk):
    def __init__(self, con):
        super().__init__()
        global ESCALA
        ESCALA = self.winfo_fpixels("1i") / 96
        self.con = con
        self.title(f"{NOMBRE_TIENDA} - stock y ventas")
        try:  # empaquetada, Tk lee el ícono del propio .exe; sin icono.ico se queda el de Tk
            self.iconbitmap(default=sys.executable if getattr(sys, "frozen", False) else BASE / "icono.ico")
        except tk.TclError:
            pass
        self.minsize(min(px(1040), self.winfo_screenwidth()), min(px(640), self.winfo_screenheight() - px(80)))
        self.state("zoomed")  # arranca maximizada: entra en cualquier pantalla
        self.configure(bg=C["fondo"])
        estilos(self)

        lateral = tk.Frame(self, bg=C["lateral"], width=px(210))
        lateral.pack(side="left", fill="y")
        lateral.pack_propagate(False)
        tk.Label(lateral, text=NOMBRE_TIENDA, font=(SERIF, 24, "italic"), bg=C["lateral"], fg="white",
                 anchor="w").pack(fill="x", padx=24, pady=(32, 0))
        tk.Label(lateral, text="stock y ventas", font=(SANS, 9), bg=C["lateral"], fg=C["lateral_txt"],
                 anchor="w").pack(fill="x", padx=24, pady=(0, 32))
        tk.Label(lateral, text="Ctrl+1 a Ctrl+4\npara cambiar de sección", font=(SANS, 8), justify="left",
                 bg=C["lateral"], fg=C["suave"], anchor="w").pack(side="bottom", fill="x", padx=24, pady=20)

        cont = ttk.Frame(self, padding=(36, 28))
        cont.pack(side="left", fill="both", expand=True)
        cont.rowconfigure(0, weight=1)
        cont.columnconfigure(0, weight=1)
        self.paginas, self.nav = {}, {}
        secciones = (("Stock", PaginaStock), ("Ventas", PaginaVentas),
                     ("Presupuesto", PaginaPresupuesto), ("Catálogos", PaginaCatalogos))
        for i, (nombre, clase) in enumerate(secciones, 1):
            self.paginas[nombre] = clase(cont, self)
            self.paginas[nombre].grid(row=0, column=0, sticky="nsew")
            fila = tk.Frame(lateral, bg=C["lateral"])
            fila.pack(fill="x")
            marca = tk.Frame(fila, width=4, bg=C["lateral"])
            marca.pack(side="left", fill="y")
            lbl = tk.Label(fila, text=nombre, font=(SANS, 11), anchor="w", padx=20, pady=11, cursor="hand2",
                           bg=C["lateral"], fg=C["lateral_txt"])
            lbl.pack(side="left", fill="x", expand=True)
            lbl.bind("<Button-1>", lambda e, n=nombre: self.mostrar(n))
            self.bind(f"<Control-Key-{i}>", lambda e, n=nombre: self.mostrar(n))
            self.nav[nombre] = (fila, marca, lbl)
        self.mostrar("Stock")

    def mostrar(self, nombre):
        for n, (fila, marca, lbl) in self.nav.items():
            activo = n == nombre
            fondo = C["lateral_act"] if activo else C["lateral"]
            fila.config(bg=fondo)
            lbl.config(bg=fondo, fg="white" if activo else C["lateral_txt"])
            marca.config(bg=C["acento"] if activo else fondo)
        self.paginas[nombre].tkraise()
        self.paginas[nombre].refrescar()  # cada sección se recalcula al abrirla: siempre al día


# ---------------------------------------------------------------- autoverificación

def autotest():
    con = conectar(":memory:")
    ids = [id_de(con, t, n) for t, n in (("categorias", "Medias"), ("talles", "M"), ("colores", "Negro"))]
    with con:
        pid = con.execute("INSERT INTO productos(nombre, categoria_id, talle_id, color_id, cantidad, precio) "
                          "VALUES ('Medias red', ?, ?, ?, 5, 1000)", ids).lastrowid
    stock = lambda: con.execute("SELECT cantidad FROM productos WHERE id = ?", (pid,)).fetchone()[0]
    ventas = lambda: con.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]

    assert vender(con, pid, 1) == 1000 and stock() == 4, "la venta descuenta stock"
    try:
        vender(con, pid, 10)
        raise AssertionError("no debería vender más que el stock")
    except ValueError:
        pass
    assert stock() == 4 and ventas() == 1, "una venta rechazada no toca nada"
    try:
        con.execute("DELETE FROM categorias WHERE id = ?", (ids[0],))
        raise AssertionError("no debería borrar una categoría en uso")
    except sqlite3.IntegrityError:
        pass
    try:
        with con:
            con.execute("INSERT INTO productos(nombre, categoria_id, talle_id, color_id, cantidad, precio) "
                        "VALUES ('Medias red', ?, ?, ?, 2, 900)", ids)
        raise AssertionError("no debería duplicar producto+talle+color")
    except sqlite3.IntegrityError:
        pass
    with con:
        con.execute("DELETE FROM productos WHERE id = ?", (pid,))
    assert ventas() == 1, "el historial sobrevive al borrar el producto"

    assert pesos(1234.5) == "$ 1.234,50"
    assert numero("1.234,50", "x") == 1234.5 and numero("$ 800", "x") == 800
    for malo in ("0", "-5", "abc", "nan", "inf"):
        try:
            numero(malo, "x")
            raise AssertionError(f"debería rechazar {malo!r}")
        except ValueError:
            pass
    assert entero("3", "x", 1) == 3
    for malo in ("0", "2.5", ""):
        try:
            entero(malo, "x", 1)
            raise AssertionError(f"debería rechazar {malo!r}")
        except ValueError:
            pass
    print("Autoverificación OK")


if __name__ == "__main__":
    if "--test" in sys.argv:
        autotest()
    else:
        try:  # letra nítida en pantallas con zoom de Windows
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
        App(conectar()).mainloop()
