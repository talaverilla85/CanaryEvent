# Auditoría editorial DParranda · 30 de octubre de 2026

## Descripciones completadas

Se revisaron las 85 fichas públicas que tenían una descripción de menos de 80 caracteres. Se consultaron las páginas oficiales de cada organizador y se escribió una sinopsis específica para cada actividad; los pases de un mismo espectáculo comparten la sinopsis artística sin fusionarse.

- **85/85 fichas objetivo**: guardadas en `event_overrides.details_override`.
- **114 descripciones editoriales** de 80 o más caracteres en total (incluye 29 que ya estaban completas antes).
- **0 fichas públicas** con descripción inferior a 80 caracteres tras el cambio.
- **513 eventos públicos activos**; los cuatro duplicados identificados previamente siguen enlazados con su ficha principal y conservan su registro original.
- Comprobado por consulta a Neon y por `https://canaryevent.vercel.app/api/catalog` (HTTP 200, 513 fichas, cero descripciones menores de 80 caracteres).
- No se modificaron los registros fuente `events`, no se creó ningún evento ficticio y no hizo falta desplegar Vercel.

## Evidencia y fuentes

Cada `published_events.payload.source_url` permite regresar a la web consultada. Las páginas verificadas pertenecen a:
- Teatro Pérez Galdós, Auditorio Alfredo Kraus, Teatro Cuyás y Sala Insular de Teatro.
- Agenda municipal LPA Cultura; ayuntamientos de Ingenio, Agüimes, Gáldar, San Bartolomé de Tirajana, Santa Lucía y Vega de San Mateo.
- Circuito de Artes Escénicas de Gran Canaria, Juventud Las Palmas, Sociedad Filarmónica de Las Palmas y plataformas de entradas con información corroborada.

Se evitó inventar intérpretes, precios, descuentos y horarios no publicados. Las descripciones se almacenan como anulaciones editoriales, reversibles y separadas de los datos descargados de origen.

## Calidad pendiente (independiente de las descripciones)

- **Airsoft (ID 609)**: la ubicación real descrita por la fuente es Hangar 37, San Bartolomé de Tirajana, pero la ficha fuente tiene municipio Agüimes. Se necesita corrección editorial de municipio (nuevo campo + publicación) o ajuste del extractor.
- **Festival Internacional de Magia (ID 743)**: la noticia municipal confirma el festival, pero no aporta intérpretes u hora exacta en la fuente de la ficha. Mantener la advertencia al visitante.
- **Cine de Terror (ID 11)**: la agenda de Agüimes advierte que la hora no es definitiva; la inscripción y la plaza requieren confirmación.
- **14 fichas de conciertos escolares con varios pases** siguen marcadas para asignar correctamente el horario a cada ID; no deben fusionarse solo por título y fecha.
- Comprobar en el siguiente ciclo de sincronización que `event_overrides` permanece intacto.
- **Sin images oficiales en todas las fichas:** trabajo separado; no usar fotografías inventadas como carteles reales.

**Criterio aplicado:** descripción completa significa que el texto supera el umbral y está fundamentado en información del espectáculo; no implica que todos los datos del evento estén plenamente validados.
