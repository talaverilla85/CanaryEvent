# ¿Pa' Dónde? · Agenda de Gran Canaria (repositorio CanaryEvent)

Agenda visual de planes cercanos en Gran Canaria, optimizada para móvil y tablet y publicable como PWA.


## Marca y dominio: decisiones pendientes (24 de octubre de 2026)

Marca visible aprobada: **¿Pa' Dónde?** El repositorio técnico conserva el nombre CanaryEvent y la URL de producción sigue siendo https://canaryevent.vercel.app/ hasta que haya un dominio registrado. La aplicación opera por ahora exclusivamente en Gran Canaria, aunque su marca admite una expansión futura a las ocho islas.

Pendiente de realizar — sin compras ni registros:
- [ ] Reconfirmar disponibilidad y comprar padondecanarias.es como candidato principal. Consultar el buscador oficial de Red.es antes de pagar.
- [ ] Considerar registrar también padondecanarias.com y padondecanarias.app como protección opcional, comprobando el coste de compra y renovación; no es necesario adquirir padonde.com.
- [ ] Verificar posibles conflictos de marca (OEPM y EUIPO); ya existe otro servicio llamado Pa' Donde dedicado a ocio/experiencias fuera de España.
- [ ] Verificar y, si procede, crear los perfiles de redes como @padondecanarias (su disponibilidad no está confirmada).
- [ ] Una vez registrado el dominio y comprobada la marca: conectar el dominio propio, configurar canónicas, redirecciones e indexación SEO, manteniendo un solo dominio principal. El sitio de prueba de Vercel tiene actualmente noindex,nofollow para evitar su indexación prematura.
- [ ] Revisar el plan de hosting antes de monetizar (el plan Hobby de Vercel está orientado a uso no comercial).
- [ ] Planificar selector de islas e importadores específicos por isla, sin mostrar resultados de otras islas mientras solo cubrimos Gran Canaria.

Los candidatos .es fueron vistos como disponibles el 24/10/2026; eso no reserva los dominios ni garantiza su disponibilidad o precio futuro. El titular debe ser el usuario o su empresa, nunca el asistente.

## Actualización automática y estado de fuentes

GitHub Actions ejecuta el sincronizador cada seis horas, con cron UTC 00:37, 06:37, 12:37 y 18:37 (GitHub puede retrasar la ejecución). También admite ejecución manual desde GitHub Actions.

1. Las pruebas verifican los extractores, fechas, precios, enlaces y duplicados.
2. El proceso lee las fuentes públicas conectadas y respeta sus límites/robots.txt; errores de una fuente se registran y no borran el resto del catálogo.
3. El catálogo SQLite y los JSON de eventos y metadatos se actualizan y se versionan en GitHub. La sincronización ahora reintenta sobre la última versión de main ante rechazos por cambios simultáneos, evitando forzar el repositorio.
4. Vercel despliega automáticamente main al recibir los cambios del catálogo.
5. La web carga events.json evitando la caché y vuelve a comprobarlo periódicamente o al regresar a la pestaña. Muestra la fecha de última revisión en horario de Canarias y avisa cuando han transcurrido más de 12 horas o una fuente da error.

La renovación no es en tiempo real. Precios, aforos, cancelaciones y horarios pueden cambiar entre consultas y deben contrastarse con la organización.

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


### Fuente de entradas · TuReservaOnline (Gran Canaria)

El sincronizador consulta el listado público activo de TuReservaOnline (hasta seis páginas de 24 fichas por pasada) que consume su propia web. Solo se guardan datos fácticos de eventos: título, lugar, municipio, fecha/s, tarifa mínima cuando se indica, estado de entradas agotadas, enlace al evento y URL remota de su portada. El código utiliza exclusivamente una proyección mínima de los datos de eventos; no guarda ni presenta información de usuarios, comerciantes, métodos de pago o claves aunque una respuesta del proveedor incluyera campos ajenos a las actividades.

- Exclusión estricta de municipios que no pertenezcan a Gran Canaria (no se importan eventos de Tenerife u otras islas).
- Comparación por título normalizado, fecha y municipio antes de crear una ficha nueva. Las fichas originales de ayuntamientos y Cabildo mantienen su URL y se enriquecen con el enlace de entradas cuando hay coincidencia.
- La tarifa indicada como «Desde X €» es la mínima publicada, no un precio final garantizado. Si no aparece, no se muestra importe. Cero euros como precio mínimo no se interpreta automáticamente como que todas las localidades sean gratuitas.
- Las actividades que abarcan varios días se publican como periodos, sin fabricar sesiones diarias ni horas no confirmadas.
- Las fotografías permanecen alojadas en el sitio de origen, sin descarga ni redistribución de archivos. Hay que respetar derechos de sus autores y las condiciones de reutilización si se monetiza el servicio.
- Se verifican las normas de robots.txt, se respetan errores de bloqueo o saturación y se limita el ritmo de consultas. La sincronización puede ser interrumpida si la plataforma cambia sus condiciones técnicas.
- La reserva o compra se realiza directamente en el sitio de entradas. CanaryEvent no efectúa pagos ni comprueba disponibilidad en tiempo real.

Se ha estudiado Tomaticket como posible fuente adicional, pero su web responde con un bloqueo automático a las peticiones de nuestro robot. No intentamos eludirlo: para integrarlo sería necesario disponer de un acceso autorizado o feed reutilizable. También son candidatas de ampliación las agendas oficiales del Auditorio Alfredo Kraus y otros teatros y auditorios de la isla.


Para fichas del día que ya no figuren en el listado activo se permite una verificación focalizada y limitada contra la página pública original del evento, únicamente cuando su identificador textual coincide con el sitemap oficial; se almacenan solo fecha, recinto, precio publicado y enlace. Por ejemplo, «Gran Final Yo Canto» puede verificarse tras cerrarse las reservas sin presentarlo como un evento todavía reservable. Se utiliza una caché de 36 horas y un máximo de cuatro fichas por ejecución. La base de datos conserva duplicados históricos como registros internos, pero los oculta del catálogo cuando se demuestra la coincidencia mediante el título, la fecha, el enlace municipal original y el municipio de la plataforma.
