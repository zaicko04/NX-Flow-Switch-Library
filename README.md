# NX Flow — Nintendo Switch Homebrew Library

Catálogo visual **CoverFlow 3D** de ports, emuladores, Wine / PC y homebrew, con organización por familias y subcategorías de consola (Nintendo, PlayStation, Sega, Xbox, Arcade, Android y PC).

## Vista previa y publicación

- El `index.html` es una versión autónoma funcional: incluye CSS, JS y logotipos integrados. Usa `data/catalog.json` cuando está disponible y los 18 registros de demostración como respaldo.
- Para publicar en **Netlify**, conecta este repositorio GitHub. El archivo `netlify.toml` publica la raíz; no hace falta build.
- Para publicar en **GitHub Pages**, ve a **Settings → Pages** y selecciona **Deploy from a branch**, rama `main`, directorio `/(root)`. URL prevista: https://zaicko04.github.io/NX-Flow-Switch-Library/ después de activar Pages.
- El sitio no almacena ROMs, ISOs ni datos protegidos de juegos comerciales.

## Actualización automática

`.github/workflows/sync.yml` ejecuta `python scripts/sync_catalog.py` cada seis horas y permite iniciarlo manualmente desde la pestaña **Actions** → **Actualizar biblioteca NX Flow** → **Run workflow**.

El script consulta:
- [SwitchPorts](https://github.com/robzilla10001/SwitchPorts) para ports y emuladores registrados.
- [Homebrew App Store](https://hb-app.store/switch) para metadatos, imágenes y enlaces originales.
- [GBAtemp](https://gbatemp.net/forums/nintendo-switch.283/) mediante un RSS, únicamente como avisos **por verificar**.

Si una fuente deja de responder, el importador conserva su última información registrada. La cobertura es progresiva y no garantiza contener todos los proyectos existentes.

Si GitHub Actions no puede guardar el catálogo, habilita **Settings → Actions → General → Workflow permissions → Read and write permissions**.

## Agregar mis propios ports

Crea `data/custom/nintendo/n64.json` o un archivo equivalente por familia y sistema. Ejemplo:

```json
{"items":[{"title":"Mi port N64","url":"https://github.com/usuario/proyecto","description":"Requiere archivos originales obtenidos legalmente"}]}
```

Cada archivo con `items` genera sus registros en la siguiente sincronización. Únicamente enlaza archivos cuya distribución esté autorizada.

## Estado

Interfaz funcional y catálogo inicial disponibles. Los datos masivos se obtendrán después de la primera ejecución del workflow. No hay hosting externo configurado todavía.
