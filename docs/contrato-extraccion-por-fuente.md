# Contrato de recopilación por fuente — D’Parranda

## Regla no negociable
La identificación, extracción y verificación original **se mantienen específicas de cada fuente**.
El enriquecimiento SEO no sustituye los conectores ni sus reglas, y nunca se invoca desde una visita pública.

## Orden del proceso existente
1. `scripts/sync_events.py` y sus módulos especializados extraen eventos de agendas, calendarios, recintos, PDF y otras fuentes admitidas.
2. Cada conector aplica su formato y comprobaciones particulares (fecha, hora, lugar, título, fuente, cartel, categoría), según los procedimientos originales.
3. `dedup_key` y `upsert` preservan la identidad del evento y aplican las políticas existentes de duplicados y actualización.
4. Los módulos de corroboración existentes aportan datos verificables y se aplica la política de publicación.
5. **Solo después de esos pasos**, `scripts/event_enrichment.py` revisa los campos ausentes o insuficientes y consulta de forma limitada enlaces ya conocidos. Un dato se incorpora únicamente si se confirma la identidad del evento (título + fecha), manteniendo el ID.
6. El catálogo público y PostgreSQL se sincronizan con el procedimiento original.

## Particularidades que se mantienen
- Ingenio: eventos y sesiones de su agenda municipal, fechas y lugares del HTML específico.
- Agüimes: eventos de su propio portal y validación de municipio/horario.
- Juventud de Las Palmas: fechas de reserva reales del selector; no se inventan repeticiones.
- Artes Escénicas: fichas del recinto, caché original de detalles y verificación de programación.
- Fuentes culturales, cartelería, ayuntamientos y programas PDF: siguen sus conectores, validaciones y políticas propias.
- Las páginas SEO consultan los datos ya publicados; no fuerzan búsquedas, transformaciones o lecturas de imágenes durante la visita.

## Enriquecimiento diario incremental (22 noviembre 2026)
- La cola se alimenta de **todos los eventos aprobados y vigentes** guardados en SQLite. Los eventos ya completos dejan de consumir consultas hasta que aparezca una carencia nueva.
- Cada registro conserva `attempts`, `next_check_at`, `outcome`, campos pendientes y evidencias de los cambios en `event_enrichment_checks` y `event_enrichment_proofs`.
- La tarea programada ejecuta **hasta 16 documentos oficiales y 40 fichas por pasada**; los reintentos fallidos se espacian progresivamente hasta 14 días. Los eventos nuevos se priorizan y el resto avanza en las siguientes ejecuciones.
- Se comprueban las carencias de hora, recinto, precisión de la ubicación, descripción, cartel y precio. Para indexar no se exige cartel ni precio, pero sí los requisitos originales de la ficha SEO.
- Primero se busca el enlace original o del organizador; se permite seguir enlaces internos del mismo portal únicamente cuando el enlace coincide con el título. El candidato final siempre debe acreditar **título y fecha exactos**.
- La prueba primaria es un objeto `Event` de JSON-LD del organizador. Como alternativa se aceptan descripciones y horas **solo** cuando la ficha oficial contiene un `h1` exacto y un único `time datetime` del mismo día; los listados generales no sirven.
- Carteles, precios y coordenadas solo se incorporan desde metadatos explícitos de la ficha verificada, y las coordenadas exigen también municipio confirmado. Imágenes externas a los dominios autorizados se descartan.
- Una copia verificable de los datos se reutiliza si la fuente vuelve a publicar un resumen incompleto, pero **solo mientras coincidan ID, título, día y URL originales**. Los extractores no se modifican.
- El resumen agregado de cada pasada queda en `data/seo_enrichment_status.json`, sin exponer datos de usuarios ni credenciales. El estado de cada evento y sus pruebas permanecen en SQLite.
- Si una fuente oficial no publica el dato, se mantiene pendiente: **nunca se inventa ni se afirma que todas las fichas llegarán a indexarse**.

## Prioridad SEO de la cola (23 noviembre 2026)
- No se bajan los umbrales para indexar ni se habilitan nuevas fuentes no fiables. Se conserva la comprobación de título + fecha exacta, procedencia, y el historial de pruebas.
- En **cada ciclo de ocho eventos seleccionados**, cuatro plazas corresponden a eventos con **una** carencia SEO obligatoria, dos a los de **dos** carencias, una a los de **tres o más** carencias y una a eventos que solo necesitan mejoras opcionales (precio/cartel). Si alguna categoría está vacía, las plazas se redistribuyen automáticamente.
- Las carencias SEO obligatorias son horario exacto, nombre del recinto, **precisión de la ubicación** y descripción útil. Recinto desconocido + ubicación municipal se cuentan como **dos carencias**, aunque un mismo dato oficial pueda resolver ambas.
- Dentro de cada categoría, las sesiones aún futuras tienen preferencia sobre los programas largos empezados anteriormente. Dos de cada tres revisiones favorecen eventos no comprobados; la tercera se reserva para comprobaciones vencidas. **Nunca** se elude `next_check_at` ni el descanso de 72 horas de comprobaciones antiguas.
- Se mantiene el límite existente de **16 documentos oficiales y 40 fichas por ejecución**. La cuota de 6/8 plazas priorizadas se aplica a fichas seleccionadas; las consultas reales pueden variar porque una ficha puede requerir varios documentos y las URL ya comprobadas se reutilizan dentro de la ejecución.
- El informe `data/seo_enrichment_status.json` incluye `one_seo_gap`, `two_seo_gaps`, `near_ready` y `checked_by_priority`. **Estas cifras se calculan en SQLite de recopilación**, antes de las posibles correcciones del panel de publicación; no equivalen al número de páginas efectivamente incluidas en el sitemap ni a páginas indexadas por Google. Para ese resultado se consulta el sitemap real.
- La cola se reevalúa sola con cada sincronización programada; no se añade otro bot, dashboard ni acción manual.

## Restricciones del enriquecimiento
- No crear eventos nuevos por una coincidencia aproximada, ni cambiar el ID.
- No modificar un dato completo si el conector lo ha obtenido correctamente.
- No inferir nuevas sesiones, precios, horarios, lugares, autores o imágenes a partir de pistas.
- No tratar un evento de otro municipio o fecha como el mismo.
- Exigir prueba concreta, almacenar URL original y URL corroborante, y poder auditar qué campo se modificó.
- Límite de consultas, comprobación de robots.txt, tiempo de reposo entre búsquedas y gestión de errores.
- Si falla el enriquecimiento, la ingesta anterior debe continuar.

## Pruebas de regresión
Se comparó esta rama con `main` el 21/11/2026:
`extract_ingenio`, `extract_aguimes`, `extract_juventud`,
`extract_artes`, `enrich_artes_entries`, `dedup_key` y `upsert` son idénticos.

Antes de fusionar, ejecutar el conjunto de pruebas y comprobar una sincronización en entorno de prueba, con sus cantidades y fuentes. No activar la fase si Vercel sigue bloqueando la preview.
