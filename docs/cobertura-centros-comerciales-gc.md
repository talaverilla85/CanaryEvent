# Cobertura de eventos en centros comerciales de Gran Canaria
Revisión: 23 noviembre 2026

Este inventario es **una lista de trabajo, NO una afirmación de que todos los
centros de Gran Canaria están integrados**. Los dos primeros publican fichas de eventos verificadas y Siete Palmas se vigila
sin publicar nada hasta encontrar actividades futuras con fecha y hora. No confundir
«fuente localizada» con «eventos capturados».

| Centro | Fuente localizada | Situación real |
|---|---|---|
| Las Arenas (Las Palmas GC) | https://cclasarenas.com/club-arenillo-programacion-navidad-2026/ | **Automático**: sesiones verificadas y cartel oficial general |
| El Corte Inglés Mesa y López (Las Palmas GC) | https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/mercado-navideno-las-palmas | **Automático**: mercado navideño y cartel propio |
| Atlántico Vecindario | https://ccatlantico.com/novedades/?sector=eventos | Pendiente de extractor. Existen anuncios, pero hay que separar promociones comerciales de talleres con fechas |
| Siete Palmas (Las Palmas GC) | https://sietepalmascc.com/ahora-mas/eventos | **Monitor automático en pruebas**: noticias oficiales; sin eventos futuros fechados a 24/11. Reutiliza la URL oficial de la imagen cuando está disponible; no archiva fotos en Drive |
| El Muelle (Las Palmas GC) | https://ccelmuelle.es/eventos-noticias/ | Pendiente. Mezcla anuncios antiguos y recientes; se debe comprobar el año original |
| La Ballena (Las Palmas GC) | https://centrocomerciallaballena.com/cat/eventos/ | Pendiente. Publica campaña Navidad 2026 sin fechas individuales |
| Las Ramblas (Las Palmas GC) | https://lasramblascentro.com/noticias/ | Pendiente. La página «Eventos de diciembre» corresponde a una Navidad que cita 2025; nunca atribuir a 2026 |
| La Minilla (Las Palmas GC) | https://laminillacc.com/ | Pendiente. Programa web visible sin calendario navideño completo |
| Las Terrazas Outlet (Telde) | https://lasterrazasoutlet.com/ | Pendiente. La web muestra novedades comerciales, no una agenda concreta validada |
| Mogán Mall (Puerto Rico, Mogán) | https://moganmall.com/navidad/ · [PDF oficial 2026](https://drive.google.com/file/d/1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v/view) | **Programa 2026–27 transcrito y sincronizado automáticamente desde un listado verificado**: fecha, hora, imagen remota oficial y enlace al PDF. El sitio HTML mantiene HTTP 403 para el bot: NO se elude. Las siguientes temporadas exigirán revisión de un nuevo PDF oficial |
| Alisios (Tamaraceite, Las Palmas GC) | Pendiente de localizar feed público oficial estable | No integrado. El encendido del 21/11 ya terminó |
| El Mirador (Jinámar, Telde) | Pendiente de localizar feed público oficial estable | No integrado |
| El Tablero (San Bartolomé de Tirajana) | Pendiente de localizar agenda pública oficial | No integrado |
| La Mareta (Telde) | Pendiente de localizar agenda pública oficial | No integrado |

Otros centros o complejos comerciales podrían añadir más fuentes: el inventario
no pretende ser exhaustivo de cada pequeño centro o zona comercial de la isla.

## Política
- Para publicar, exigir día, hora, actividad y recinto verificables. No
  rellenar años o sesiones a partir de campañas genéricas.
- Si la fuente es un programa completo, no transformar sus días de apertura
  en eventos diarios ficticios.
- La fuente oficial incluye carteles de campaña: identificarlos como
  «Imagen del programa», no como fotografías de la actividad individual.
- Fuentes de eventos orgánicos y campañas publicitarias de D'Parranda siguen
  siendo independientes; ninguna inclusión genera derecho a un banner.
- Prioridad de próximos conectores: La Ballena, El Muelle y Atlántico Vecindario;
  Mogán Mall solo si se dispone de acceso permitido y fechas verificadas.

## Mogán Mall · control de procedencia (24 noviembre 2026)

- El propio centro enlaza públicamente `MOGANMALL_AgendaDeNavidad_2026.pdf`, creado el 10/11/2026, desde `https://moganmall.com/navidad/`.
- PDF público: `https://drive.google.com/file/d/1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v/view` (3.415.654 bytes; SHA-256 `8da43f340ba9affb91dbee347a9dc432bf4c17dc136cefed8bb74c5257eabe38`). Es una sola página rasterizada, sin texto legible automáticamente.
- Las actividades se transcribieron y comprobaron visualmente contra el cartel oficial. `scripts/mogan_mall_official.py` almacena exclusivamente este calendario 2026–27; el sincronizador filtra fechas ya pasadas y deduplica. No afirma extraer cada día el HTML bloqueado ni reutiliza fechas en futuras Navidades.
- Imagen de las fichas: miniatura **externa** del PDF oficial, `https://drive.google.com/thumbnail?id=1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v&sz=w640`. D'Parranda no sube imágenes a Drive, ni guarda una copia del PDF, y enlaza su fuente original.
- La página SEO `/centros-comerciales/mogan-mall` aparece automáticamente cuando existan suficientes actividades futuras verificadas; desaparece del índice tras su finalización.
- Para la Navidad 2027/28 habrá que identificar otro programa oficial; este conector no debe inventar una edición anual.
