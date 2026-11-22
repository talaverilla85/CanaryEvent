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
