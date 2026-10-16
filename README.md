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

## Carátulas de juegos (CoverFlow 3D)

NX Flow acepta un campo opcional `cover` por entrada. El orden de prioridad es:

1. Reemplazo explícito en `data/covers.json` (por ID o por `Consola|Título`).
2. Campo `cover` del port personalizado.
3. Portada enlazada de [Libretro Thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails), **únicamente cuando hay coincidencia exacta de nombre y consola**.
4. Icono de Homebrew App Store para aplicaciones.
5. Caja generada por NX Flow con el título cuando no hay imagen verificada.

El archivo `scripts/resolve_covers.py` intenta completar carátulas en la misma actualización automática de seis horas; no es necesario subirlas todas a mano. Las imágenes de juegos no identificados no se inventan ni se asignan mediante coincidencias aproximadas.

**Agregar una portada personalizada:**

1. En GitHub abre `assets/covers` y utiliza **Add file → Upload files**. Sube, por ejemplo, `super-mario-64.webp` (recomendado JPG/WebP/PNG vertical, 400–800 píxeles de ancho).
2. En `data/covers.json` agrega el nombre exacto y su consola a `by_title`, por ejemplo:
   ```json
   {
     "by_id": {},
     "by_title": {
       "Nintendo 64|Super Mario 64": "assets/covers/super-mario-64.webp"
     }
   }
   ```
3. La siguiente ejecución de **Actions → Actualizar biblioteca NX Flow** incorporará el cambio, o puedes presionar **Run workflow**.

Para un port nuevo en `data/custom/nintendo/n64.json`, también puedes escribir `"cover": "assets/covers/mi-port.webp"` directamente. Esto se preserva entre actualizaciones.

Las carátulas oficiales de videojuegos pueden estar protegidas por derechos de autor; procura usar imágenes con permiso o conforme a las condiciones de su fuente, conserva sus créditos y no redistribuyas ROMs ni datos propietarios. El sitio enlaza las imágenes públicas de Libretro, no las almacena de forma masiva.

## Carátulas visibles para todo el catálogo

El CoverFlow y la cuadrícula siempre muestran una carátula para cada entrada, incluso cuando no existe una portada real en las fuentes públicas.

Prioridad visual:

1. **Carátula real del juego** en el campo `cover` (Libretro, x360db, o imagen personalizada).
2. **Portada diseñada automáticamente más icono auténtico** cuando la entrada proviene de HB App Store y tiene `icon`.
3. **Portada ilustrada de NX Flow**, con el título, consola y colores identificables. Se genera en el navegador (SVG); no se presenta como arte oficial.

Si una carátula externa no carga, el diseño SVG toma su lugar. Así no aparecen cajas vacías ni imágenes rotas.

Para cambiar una ilustración por una carátula autorizada, sube la imagen a `assets/covers/` y referencia su ruta en `data/covers.json` con la clave `Consola|Título`. La siguiente sincronización aplicará el cambio.

La deduplicación conserva un registro por título, consola y tipo; las alternativas quedan en metadatos. Por eso el total visual coincide con las entradas únicas, no con las variantes importadas.
