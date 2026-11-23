# Biblioteca multimedia de D’Parranda · Archivo de originales

## Situación y alcance

Este sistema es independiente de la PWA: **no altera `public/events.json`, ni las imágenes que ve el visitante, ni la sincronización de eventos**.
Lee el catálogo publicado por los extractores y el inventario de Google Sheets.
Los 224 registros iniciales se conservan y el proceso incorpora automáticamente nuevas imágenes oficiales al inventario.

Inventario: `Inventario maestro — 224 imágenes oficiales de eventos activos`.
Carpeta de destino: `D’Parranda — Biblioteca multimedia / 01 — Carteles y fotografías originales / año / Gran Canaria / categoría / municipio`.
Las piezas navideñas claramente identificadas se guardan bajo `Navidad año / municipio`.

## Permisos: son dos cosas distintas

- Columna **J**: permiso para *crear nuevas publicaciones, historias o reels*. No lo decide el archivador.
- Columna **L**: permiso para *descargar y conservar una copia en Drive*. Solo el valor exacto **Autorizado** habilita la descarga.
- **Pendiente** y **Denegado** nunca se descargan.
- Una imagen visible en un sitio municipal no es por sí misma una licencia de reutilización comercial.
- Si la condición de reutilización es incierta, dejar pendiente y conservar únicamente el enlace y la fuente.
- Para imágenes admitidas, conservar la URL de procedencia, autoría y atribución; el archivo interno no implica permiso para redes.

## Desduplicación y controles

- Agrupación por URL: varias sesiones del mismo evento comparten un cartel.
- SHA-256 del contenido: si dos enlaces devuelven el mismo archivo binario, se guarda una sola copia.
- Columna **K**: estado de archivo. **M**: ID de Drive. **N**: SHA-256. **O**: fecha. **P**: error.
- Se respeta `robots.txt` y no se siguen redirecciones externas automáticamente.
- Solo HTTPS público, imágenes validadas, máximo 15 MB. No se descargan HTML, SVG o documentos no-imagen.
- Las imágenes existentes permanecen en su carpeta; no se eliminan cuando el evento caduca.
- Los errores quedan visibles en la hoja para revisar dominios bloqueados o formatos incompatibles.

## Activación segura (una vez)

**Importante:** haber conectado la cuenta Google Drive con ChatGPT **no** entrega un token a GitHub Actions.
Por seguridad, se necesita una autorización OAuth independiente, creada en el equipo del propietario.

1. Accede a Google Cloud Console con la cuenta propietaria de la biblioteca. Crea un proyecto privado y habilita **Google Drive API** y **Google Sheets API**.
2. Configura la pantalla de consentimiento OAuth. Crea un cliente **Aplicación de escritorio** y descarga `client_secret.json` a un directorio local que NO sea el repositorio. Para uso continuo, evita mantener el proyecto en el modo externo «Testing», cuyos refresh tokens pueden caducar a los 7 días.
3. En el equipo local instala las dependencias:

   `python -m pip install google-auth-oauthlib google-api-python-client google-auth requests`

4. Ejecuta: `python scripts/drive_oauth_setup.py --client /ruta/privada/client_secret.json`.
5. Inicia sesión y autoriza exclusivamente la cuenta dueña del Drive de D’Parranda. La herramienta guarda el token en `~/.dparranda-drive-oauth.json` con permisos restrictivos. **No lo copies al chat ni al repositorio.**
6. En GitHub, abre **Settings → Secrets and variables → Actions → New repository secret**. Nombre: `DPARRANDA_GOOGLE_DRIVE_OAUTH_JSON`. Valor: el contenido JSON completo del archivo generado.
7. Revisa en la hoja los derechos de una imagen de prueba y cambia **L** a `Autorizado` solo si el permiso para descargarla está acreditado.
8. Integra la propuesta en `main` después de revisarla. Abre **Actions → Archivar imágenes autorizadas en Drive → Run workflow** y comprueba columnas **K** y **M:P**.

## Ejecución automática

El workflow `.github/workflows/archive-event-images-drive.yml` corre al finalizar correctamente «Actualizar eventos oficiales» y tiene un respaldo diario a las 07:13 UTC. **Solo funcionará después de integrar el código en main y configurar el secreto OAuth**.
Si falta el secreto ejecuta únicamente un diagnóstico (`--dry-run`) y no intenta subir archivos.
Admite hasta 80 descargas por ejecución y evita volver a copiar las imágenes que ya tengan ID de Drive.
Solo procesa material de eventos vigentes o futuros; conserva los carteles archivados de eventos anteriores.

## Prueba sin Drive

`python scripts/archive_event_images_drive.py --dry-run`

Este comando muestra el número de URLs oficiales distintas en el catálogo, pero no lee permisos ni sube fotografías.
Los tests de reglas se ejecutan con:

`python -m unittest discover -s tests -p 'test_drive_image_archive.py' -v`

## Limitaciones de esta versión

- La foto que se guarda es la que devuelve la URL disponible, que puede ser un thumbnail WebP; no es necesariamente el JPG de resolución máxima.
- Las redirecciones y fallos de `robots.txt` se registran para revisión, no se sortean.
- Una URL ya archivada no se vuelve a descargar en cada pasada; una imagen sustituida in situ en la fuente requiere una futura rutina de revalidación.
- El archivador no acredita automáticamente derechos de autor; la autorización se documenta manualmente.
