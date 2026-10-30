# DParranda · PostgreSQL (Neon)

Proyecto Neon creado: `silent-forest-22181101` (región europea, PostgreSQL 17).

La primera copia del catálogo público está cargada en Neon; el sincronizador de originales de SQLite está preparado, **pero requiere autorización de conexión de GitHub Actions**. La web pública sigue leyendo `public/events.json`, por lo que no se interrumpen las visitas.

## Una autorización pendiente de GitHub Actions

En el repositorio `talaverilla85/CanaryEvent`, abre Settings > Secrets and variables > Actions > New repository secret.

Nombre: `DPARRANDA_DATABASE_URL`

Valor: copia la cadena de conexión PostgreSQL de Neon para el proyecto `dparranda`, sin publicarla ni subirla a Git. Usar una conexión TLS del proveedor.

Tras guardarla, el workflow `Actualizar eventos oficiales` ejecutará `python scripts/postgres_migration.py --sync` después de publicar SQLite/JSON y verificará recuentos en una transacción. Los ajustes editoriales y campañas ya modificadas en Neon se conservan.

## Limitaciones y siguiente fase

No se ha activado todavía lectura directa de PostgreSQL en Vercel ni panel privado de administración. Habrá que configurar la conexión de servidor en Vercel y el acceso de administrador antes del cambio de fuente. No deben ponerse secretos en el frontend.

Los extractores y el catálogo JSON siguen siendo el respaldo funcional.
