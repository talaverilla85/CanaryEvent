# Navidad y actividades de centros comerciales — D'Parranda

## Criterios editoriales (23/11/2026)

Se publican actividades reales de centros comerciales con fecha, recinto y, para sesiones, hora verificada. No se admiten descuentos, aperturas comerciales, anuncios de tiendas ni promociones sin actividad cultural o familiar. Estas fichas son contenido editorial, no publicidad contratada.

## Fuentes integradas en la sincronización diaria

- **Centro Comercial Las Arenas:** https://cclasarenas.com/club-arenillo-programacion-navidad-2026/ . Se extraen talleres, encuentros de Papá Noel y Reyes Magos y tren de renos para noviembre y diciembre de 2026 y enero de 2027. Se exige coincidencia del día de la semana y fecha real, descartando los días incorrectos. No se marca ninguna actividad como gratuita sin evidencia. Hay ubicación de edificio verificada con OSM way 33127705 y contacto oficial del centro.
- **El Corte Inglés José Mesa y López:** https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/mercado-navideno-las-palmas . Mercado con acceso libre, 20 noviembre de 2026 a 5 enero de 2027, con información expresa de cierres 25 diciembre y 1 enero. Las compras y consumiciones no son gratuitas. Se muestra como programa largo, sin inventar visitas diarias.

Cada fuente respeta robots.txt, límites de descarga y conexión HTTPS del sincronizador existente, y registra su propia fuente y posibles fallos en source_log. Un fallo no interrumpe el resto de la recogida. Los programas futuros no se anuncian hasta que la fuente facilite fechas correctas.

### Otras fuentes revisadas pero sin extracción automática

- **Siete Palmas:** el evento oficial encontrado estaba fechado el 20/11/2026 y ya terminó. Faltan fechas verificadas para posteriores actividades.
- **Mogán Mall:** el proceso de recopilación obtuvo HTTP 403. No se intenta eludir la limitación ni generar eventos sin evidencia suficiente.
- **CC Atlántico:** la programación visible fue publicada en enero de 2026 y muestra fechas sin un año inequívoco para la próxima Navidad; no se traslada automáticamente a 2026-27.

## Página de Navidad

- URL permanente: https://dparranda.es/navidad-gran-canaria .
- Se alimenta del catálogo público en vivo, incluyendo ayuntamientos, cultura y centros comerciales: papá Noel, Reyes Magos, luces, mercadillos, talleres y demás actividades claramente navideñas.
- No aparecen eventos expirados, anuncios pagados como si fueran eventos, ni promociones de tiendas.
- HTML servido en servidor, enlaces a las fuentes, canónica, título estacional y sitemap dinámico. Se indexa solo cuando al menos tres planes diferentes cumplen calidad suficiente; si no, noindex.
- El banner activo de AriMar aparece en una posición claramente etiquetada «ESPACIO PATROCINADO · PUBLICIDAD» después de tres fichas, desde la misma campaña administrada en la base de datos, con parámetros UTM incluyendo utm_content=navidad, y el mismo registro de clics de la portada. No implica medición de impresiones ni modifica las campañas existentes.
- La programación sigue actualizándose con el trabajo automático diario, sin intervención de usuarios.

## Criterio de sesiones detalladas (23/11/2026)

- **Una ficha por actividad y día.** Si el mismo taller tiene horario de mañana
  y tarde, sus dos franjas se indican expresamente en la tarjeta y en el
  detalle: «Dos sesiones: 11:00–14:00 y 17:00–20:00». No se crean fichas
  duplicadas ni se anuncia una actividad continua de 11 a 20 h.
- **Las Arenas:** el extractor desglosa el programa completo de Club Arenillo
  por día y actividad. Cuando existe un cartel oficial conjunto de la
  temporada se muestra como «Imagen oficial del programa navideño de Las
  Arenas», sin atribuir esa imagen a un taller concreto.
- **Mesa y López:** se mantiene una ficha del mercado navideño, con su periodo
  completo; **además** se extrae el programa específico de espectáculos
  familiares publicado oficialmente:
  https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/una-navidad-llena-de-magia-risas-y-diversion-para-toda-la-familia .
  Hay 13 actuaciones distintas, entre el 4 y el 30 de diciembre de 2026,
  de 18:00 a 19:00 h, con entrada libre anunciada. Cada actuación tiene
  título, fecha, horario, fuente y fotografía del programa original.
- La página de los espectáculos no expresa el año en su programación; **solo
  se utiliza como fuente automática si la página oficial del mercado del
  mismo centro confirma explícitamente la temporada 2026–27** y todos los
  días de la semana coinciden con el calendario. De lo contrario, no se
  incorporan fichas. Tras el 30 de diciembre no se consultan sus actuaciones
  pasadas.
- Se evitan fichas individuales indexadas casi idénticas para estos
  programas de sesiones, sin ocultarlas del buscador ni de la agenda de
  Navidad. La página temática reúne los actos y el anuncio de AriMar queda
  como publicidad diferenciada.
