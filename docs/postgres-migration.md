# DParranda — transición PostgreSQL sin interrupción

## Estado actual
Se ha preparado el esquema PostgreSQL y un importador incremental. El
catálogo de producción continúa leyendo public/events.json y public/ads.json.
**No se ha activado todavía la lectura online ni el panel de administración.**

## Conexión (pendiente de una base de datos autorizada)
1. Crear y conectar PostgreSQL (por ejemplo, Neon) al proyecto DParranda.
   Revisar el plan antes de contratar recursos de pago.
2. Guardar la URL completa **como secreto**, sin compartirla en mensajes:
   GitHub > CanaryEvent > Settings > Secrets and variables > Actions:
   nombre DPARRANDA_DATABASE_URL.
3. La acción programada importa SQLite, el JSON público y la publicidad en
   una transacción; comprobar sus registros tras la primera ejecución.
4. Más adelante conectar la variable de servidor en Vercel para la API privada
   y aplicar autenticación administrativa. No colocar contraseñas en el HTML,
   repositorio, public/ o variables con prefijo público.

## Comprobaciones sin PostgreSQL
python scripts/postgres_migration.py --check

## Sincronizar manualmente (entorno seguro con DATABASE_URL configurada)
python scripts/postgres_migration.py --sync

## Garantías
- No se borra ni altera SQLite ni los archivos públicos de respaldo.
- Mantiene los IDs originales y el catálogo con sesiones expandidas.
- Importación repetible, transaccional y con verificación de paridad.
- No borra la edición manual: event_overrides separado de eventos de origen.
- Los anuncios editados en PostgreSQL no se reescriben desde ads.json.
- Un evento ya no publicado se marca inactive, sin destruir historial.
- No se activa ningún endpoint público ni se exponen credenciales.

## Próxima fase tras conectar PostgreSQL
1. Verificar recuentos de registros, fichas, fuentes y campañas.
2. Añadir API autenticada de administración (eventos y publicidad).
3. Configurar publicación desde PostgreSQL hacia web con caché y rollback.
4. Eliminar fichas duplicadas mediante revisión de sesiones y fuentes, no
   por similitud de títulos sin evidencia.
5. Separar texto verificado del evento y textos genéricos de los conectores.

Este paso no convierte PostgreSQL automáticamente en la fuente de lectura.
Ese cambio se hace exclusivamente tras comprobar las credenciales y paridad.
