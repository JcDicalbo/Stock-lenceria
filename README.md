# Stock Lenceria

App de escritorio para gestionar el stock y las ventas de un local de lencería.

## Para el usuario (no necesitás instalar nada)

1. Descargá el instalador desde la sección **Releases** de este repositorio, o ejecutá `instalador\Instalar Lenceria.exe`.
2. Instalá la app como cualquier programa de Windows.
3. Abrí **Stock Lenceria** desde el menú Inicio o el acceso directo en el escritorio.
4. La base de datos (`lenceria.db`) se crea sola junto al ejecutable. Guardá una copia de ese archivo de vez en cuando como respaldo.

No necesitás instalar Python ni ningún otro programa.

## Para quienes quieran ejecutar el código fuente

Si tenés Python 3 instalado y querés correr `app.py` directamente:

```powershell
py app.py
```

Para verificar que todo funciona:

```powershell
py app.py --test
```

## Estructura

- `app.py` — código fuente (solo librería estándar: tkinter + sqlite3)
- `Lenceria.spec` — configuración de PyInstaller para generar el .exe
- `instalador.iss` — script de Inno Setup para crear el instalador de Windows
- `icono.ico`, `icono.png` — íconos de la app
