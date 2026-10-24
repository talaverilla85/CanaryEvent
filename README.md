# CanaryEvent · planGC

Agenda visual de planes cercanos en Gran Canaria, optimizada para móvil y tablet y publicable como PWA.

## Estado actual: fase 1 — eventos oficiales

- La portada carga **eventos reales importados**, no el catálogo de demostración.
- Búsqueda, categorías, filtros de fecha/gratis, ordenación por cercanía/hora, favoritos guardados localmente y mapa con centroides municipales aproximados.
- SQLite `data/events.sqlite` es la fuente persistente versionada en este repositorio. Se genera el catálogo público en `public/events.json` y el informe de fuentes en `public/meta.json`. Vercel publica los cambios de GitHub.
- GitHub Actions consulta fuentes municipales 4 veces al día (cada 6 horas aproximadamente, según disponibilidad del programador de GitHub). El workflow también admite ejecución manual.
- Se comprueban `robots.txt` y datos de fecha/hora; no hay scraping masivo de agregadores comerciales.
- Un evento se marca como cancelado solo ante un aviso explícito en su título o datos estructurados oficiales. Si desaparece de un listado, permanece hasta su fecha sin asumir que está cancelado.
- Las imágenes son **de ambientación**, no imágenes oficiales del evento.
- **La publicación de comercios y las cuentas siguen desactivadas**, deliberadamente pospuestas a una fase posterior.

### Fuentes activas
1. [Ayuntamiento de Ingenio](https://ingenio.es/events/)
2. [Ayuntamiento de Agüimes](https://eventos.aguimes.es/)
3. [Juventud Las Palmas de Gran Canaria](https://actividadesjuventud.laspalmasgc.es/)
4. [Circuito de Artes Escénicas y Música de Gran Canaria](https://artesescenicasgrancanaria.com/agenda.html)
5. [Portal oficial de Eventos Gran Canaria (Cabildo)](https://www.eventosgrancanaria.com/) — exploración incremental de fichas públicas indexadas en sitemap XML; solo metadatos básicos, sin fotografías, textos largos ni credenciales de API.

Solo se muestra información suficiente para una ficha verificable; la cobertura territorial todavía no es total. Las actividades con horario/fechas incompletos no se inventan. Se conserva el enlace original.

### Cómo añadir más fuentes

Modificar la lista `SOURCES` de `scripts/sync_events.py` y añadir un extractor probado. Verificar las condiciones, robots.txt, estructura y licencia de cada portal. Las fuentes de terceros que restringen scraping requieren permiso.

### Ejecutar manualmente
```bash
python -m pip install -r scripts/requirements.txt
python -m unittest discover -s tests -v
python scripts/sync_events.py
```

### Desplegar
Vercel conectado con la rama `main`: Framework Other; raíz `./`; Output Directory `public`. Cada push al repositorio actualiza la portada. `public/events.json` y `public/meta.json` se actualizan tras la sincronización.

### Limitaciones

No es una verificación instantánea de cancelaciones, solo comprobación periódica de las fuentes conectadas. Algunas agendas publican PDFs o requieren permiso, y habrá que añadir conectores específicos. La ubicación es el centro del municipio salvo que una fuente proporcione coordenadas comprobadas. SQLite + GitHub es adecuado para un catálogo público controlado por sincronización, no para altas de usuarios concurrentes: la fase de comerciantes requerirá PostgreSQL u otra base de datos multiusuario con autenticación.

### Crecimiento progresivo y límites de reutilización

El robot comprueba robots.txt, indexación pública e integridad, consulta como máximo 75 páginas de eventos del Cabildo por ejecución y espacia solicitudes. La primera importación es progresiva: **667 fichas indexadas no equivalen a 667 eventos próximos completos**. Las actividades con horario desconocido se señalan claramente como pendientes de consultar; las que abarcan un periodo remiten a la programación del organizador. Las fichas enlazan siempre a la fuente original.

El aviso legal del portal oficial reserva derechos de textos, fotografías y otros elementos: **este conector no implica licencia de reproducción masiva de contenido ni de extracción de una base de datos protegida**. Antes de ofrecer un catálogo comercial completo, solicitar acceso a datos reutilizables o autorización al Cabildo y acordar frecuencia y atribución.

La paginación muestra 48 tarjetas por tanda para no saturar los móviles; el catálogo exportado puede contener más. 


### Portadas reales de los eventos

- Se importan las portadas originales que se publican en las agendas municipales (listados) y en las fichas individuales del portal del Cabildo.
- El catálogo exporta los campos image_url, image_alt, image_origin e image_status. Solo se admiten dominios oficiales concretos y se descartan imágenes genéricas, logos y favicons.
- Los archivos de imagen **no se copian ni se alojan en GitHub/Vercel**. El navegador solicita la imagen al servidor original. Las portadas conservan crédito y un enlace a la fuente; su uso público continuado debe revisarse con los titulares de derechos y sus políticas de incrustación.
- Si el organizador no publica imagen, si falla el enlace o si el servidor bloquea su uso externo, la tarjeta presenta un diseño neutro con la categoría, **nunca una foto ficticia o de otro evento**.
- Las portadas de fichas ya existentes se recuperan gradualmente en las siguientes ejecuciones programadas, a razón de hasta 75 páginas del Cabildo por sincronización, respetando intervalos entre peticiones.


### Mapa móvil y tablet (revisión 24/10/2026)
- Se ha corregido la firma SRI de la hoja de estilos de Leaflet, que impedía cargarla en navegadores modernos.
- Los marcadores representan concentraciones de eventos por municipio (o coordenada compartida); pulsar el marcador filtra el carrusel inferior por ese grupo.
- El carrusel admite cargar más resultados de 16 en 16, volver a todos los municipios, abrir fichas y retomar el mapa.
- La vista se ajusta a los marcadores y se redimensiona correctamente al abrirse; no salta inesperadamente durante la navegación.
- Importante: las coordenadas actuales son **centroides municipales**, no direcciones verificadas de los recintos. Se indica expresamente en el mapa. El geocodificado de recintos requiere fuentes y coordenadas validadas antes de presentar marcadores como localizaciones exactas.
- Prueba en navegador real con Playwright a tamaños 390×844 y 820×1180, además de pruebas automáticas de contrato del mapa.


### Verificación de precios y recintos (octubre 2026)

Las fichas del Circuito de Artes Escénicas y Música ahora se enriquecen desde la página oficial individual del espectáculo, no solo desde el resumen de agenda. Se comprueban precio, gratuidad explícita, recinto, duración y una descripción corta legible. Se utiliza un caché de 48 horas y un límite de 12 páginas por sincronización. Ejemplo: «31 Festival MASDANZA: Transeúnte» — Teatro Cuyás, 10 €, 50 minutos.

La tarjeta móvil muestra primero el recinto y debajo el municipio. Cuando no exista precio oficial verificable se indica «Precio por confirmar»: no se inventan importes. Las métricas prices_confirmed, prices_to_verify y venues_to_verify del meta.json permiten priorizar el enriquecimiento de otras fuentes.


### Enriquecimiento gradual de datos y enlaces oficiales

El sincronizador del Cabildo inspecciona únicamente fichas de eventos indexadas y permitidas por robots.txt, a un máximo de 75 páginas por ejecución. Usa Schema.org Event y campos explícitos para identificar precio y gratuidad, recinto y una URL externa indicada por la propia fuente. No deduce importes por encontrar un enlace de entradas ni trata un municipio como un recinto concreto. Las actividades con múltiples sesiones no reciben un precio único que no esté publicado expresamente.

Las fichas ya existentes se vuelven a revisar progresivamente mediante la columna facts_inspected en SQLite. La verificación de cambios ocurre cada aproximadamente seis horas; GitHub Actions puede retrasar la ejecución. No se exige descargar todas las páginas de una sola vez.

En la app, cuando consta, aparece un enlace «Consultar entradas» o «Web del organizador», además de la página del Cabildo. No se consultan automáticamente dominios externos desconocidos ni se garantiza disponibilidad de plazas. La información ausente permanece como «Precio por confirmar» o «Recinto por confirmar». La breve descripción del Cabildo se elabora a partir de hechos y no reproduce sin permiso sus sinopsis completas.

El indicador de calidad /meta.json permite medir precios y recintos confirmados. Para ampliar la cobertura de importes será necesario añadir adaptadores oficiales específicos de organizadores y acuerdos de reutilización.
