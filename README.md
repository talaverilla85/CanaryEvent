# D’Parranda · Disfruta de tus islas

Agenda digital de ocio y cultura de las islas Canarias. En esta primera fase publica eventos verificados de Gran Canaria. La plataforma está optimizada para móvil y tablet y funciona como PWA instalable.

## Marca y dominio · 29 de octubre de 2026

**Marca visible en la web:** D’Parranda. Identidad vectorial: D protagonista con olas turquesa y ocho islas de colores planos. Lema: «Disfruta de tus islas».

**Web actual:** https://canaryevent.vercel.app/ . El nombre técnico del repositorio sigue siendo CanaryEvent para mantener el historial y los despliegues.

**Dominio propuesto:** `dparranda.es` (no se ha verificado su registro ni se ha comprado ni conectado). No publicar otro dominio o redireccionar hasta que el usuario confirme su compra y titularidad.

Pendientes de identidad comercial y distribución:
- [ ] Comprobar titularidad, disponibilidad y posibles conflictos en OEPM y EUIPO para D’Parranda y nombres fonéticamente similares.
- [ ] Confirmar disponibilidad y registrar `dparranda.es` a nombre del usuario o de su empresa si procede.
- [ ] Tras registrar el dominio: conectar Vercel, configurar canónicas, redirecciones, indexación SEO y enlaces de la app. La versión técnica mantiene `noindex,nofollow` hasta tomar esa decisión.
- [ ] Verificar el plan de alojamiento de Vercel antes de explotar comercialmente el producto.
- [ ] Completar conectores de datos para las otras siete islas; el selector muestra las ocho, pero **solo Gran Canaria presenta eventos reales por ahora**.

El frontend usa `public/brand/dparranda-theme.css` y recursos SVG/PNG en `public/brand/` y `public/icons/`. Al cambiar recursos de marca, actualizar el manifiesto PWA y la versión de la caché en `public/sw.js`. Los tests de `tests/test_homepage_dom_contract.py` comprueban la integridad del arranque, navegación, marca y recursos de instalación.

## Actualización automática y estado de fuentes

GitHub Actions ejecuta el sincronizador una vez al día, con cron UTC 05:37 (GitHub puede retrasar la ejecución). También admite ejecución manual desde GitHub Actions.

1. Las pruebas verifican los extractores, fechas, precios, enlaces y duplicados.
2. El proceso lee las fuentes públicas conectadas y respeta sus límites/robots.txt; errores de una fuente se registran y no borran el resto del catálogo.
3. El catálogo SQLite y los JSON de eventos y metadatos se actualizan y se versionan en GitHub. La sincronización ahora reintenta sobre la última versión de main ante rechazos por cambios simultáneos, evitando forzar el repositorio.
4. Vercel despliega automáticamente main al recibir los cambios del catálogo.
5. La web carga events.json evitando la caché y vuelve a comprobarlo periódicamente o al regresar a la pestaña. Muestra la fecha de última revisión en horario de Canarias y avisa cuando han transcurrido más de 30 horas o una fuente da error.

La renovación no es en tiempo real. Precios, aforos, cancelaciones y horarios pueden cambiar entre consultas y deben contrastarse con la organización.

## Estado actual: fase 1 — eventos oficiales

- La portada carga **eventos reales importados**, no el catálogo de demostración.
- Búsqueda, categorías, filtros de fecha/gratis, ordenación por cercanía/hora, favoritos guardados localmente y mapa con centroides municipales aproximados.
- SQLite `data/events.sqlite` es la fuente persistente versionada en este repositorio. Se genera el catálogo público en `public/events.json` y el informe de fuentes en `public/meta.json`. Vercel publica los cambios de GitHub.
- GitHub Actions consulta fuentes municipales una vez al día (cada 24 horas aproximadamente, según disponibilidad del programador de GitHub). El workflow también admite ejecución manual.
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


### Nueva fuente municipal: Santa Lucía de Tirajana (San Rafael 2026)

La agenda publicada por el Ayuntamiento es necesaria porque parte de las fiestas de barrio,
verbenas y actividades infantiles no aparecen en el catálogo del Cabildo. El adaptador
municipal de 2026 permite rescatar fechas y lugares expresamente verificados desde
noticias oficiales del Ayuntamiento. Es específico del programa 2026 y caduca el
1 de noviembre; **no** debe reutilizar eventos como si fueran las fiestas de 2027.
La cobertura completa de todos los ayuntamientos requiere conectores adicionales
(individuales por formato, autorización y fuente), no solo añadir URLs a una lista.
La Graciosa se tratará como isla seleccionable y sus eventos seguirán asociados
administrativamente al municipio de Teguise.

La agenda municipal de Cultura de Gáldar también dispone de un conector activo
que lee campos estructurados de EventON (fecha, hora, recinto, URL), limitado
a los eventos de esa concejalía. Todavía no cubre todas las concejalías de Gáldar.


### Más fuentes oficiales municipales (25/10/2026)

- **Santa Brígida**: calendario oficial de eventos con JSON-LD estructurado.
  Se consultan como máximo el mes actual y el siguiente. Las actividades que
  abarcan fechas se publican como *periodos*, no como funciones diarias. Por
  prudencia no se inventan gratuidades ni se publican horas tempranas dudosas.
- **Teror**: programación oficial del Auditorio publicada para
  octubre de 2026–enero de 2027, con fecha y precio individual cuando figuran
  expresamente. No se interpreta su calendario habitual de fiestas sin año
  como un programa confirmado para 2026 o 2027.
- **Telde**: noticias municipales verificadas de Finaos, pregón de San
  Gregorio y Feria de Artesanía (2026). Es una integración parcial y finita:
  el año próximo necesitará nuevas fuentes/programas oficiales, no copiar
  automáticamente las fechas de este año.

Los tres conectores respetan robots.txt y limitan las respuestas. Los datos
de todas las fuentes se sincronizan una vez al día. Si falla un portal,
las otras fuentes continúan y el error se muestra en metadatos.

La exportación pública elimina únicamente duplicados inequívocos entre
Cabildo y ayuntamientos cuando coinciden título, municipio y día y no
contradicen horas ni recintos. Las dos fichas originales se conservan
en SQLite para trazabilidad; no se suprimen dos sesiones distintas.


### Artenara y vigilancia de fiestas en barrios de Telde (octubre 2026)

- Artenara: dos fichas oficiales publicadas en el archivo de noticias de
  9/10/2026 (Mercadillo Tradicional 31/10 y Feria de las Tradiciones 1/11).
  El conector vuelve a comprobar las noticias. Es específico de estas
  ediciones: no infiere fechas futuras ni horas no publicadas.
- Telde (barrios): cada ejecución consulta el índice municipal anual y
  guarda los enlaces de programas PDF en public/municipal_programs.json.
  Es un inventario documental, NO una agenda de actos. El archivo registra
  la última comprobación y la primera vez que apareció cada URL.
  No se crean eventos sin analizar el programa correspondiente.
- Valsequillo: agenda localizada pero la consulta HTTPS falla al verificar
  el certificado desde el ejecutor. Se deja documentado en
  data/municipal_sources_gc.json; no se desactiva la validación TLS.

La web sigue limitada a Gran Canaria y sincroniza datos diariamente.


### Valsequillo: fuente verificada de la Mancomunidad (2026)

valsequillo_medianias.py añade dos jornadas de Alma de Medianías
(31 de octubre y 1 de noviembre de 2026) desde el organizador oficial.
Las horas y entrada gratuita se contrastan contra la publicación cada vez.
El extractor se desactiva después del 1/11/2026: no inventa ediciones 2027.
Este conector es parcial: la agenda del Ayuntamiento de Valsequillo
continúa pendiente de un acceso HTTPS con certificado válido. Nunca
se inhabilita la verificación TLS.


### Tarjetas de eventos y geolocalización (octubre 2026)

La agenda pide permiso de ubicación mediante la API nativa del navegador
al entrar en el sitio (HTTPS). Si el visitante lo autoriza, calcula en
memoria la distancia aproximada en kilómetros hasta las coordenadas
publicadas para cada evento, que a menudo son el centro del municipio:
**distancia en línea recta, no kilómetros en coche ni dirección exacta**.
La coordenada del visitante no se guarda en el servidor ni en localStorage.

Si se deniega o no está disponible el permiso, no se bloquea la agenda:
continúa el selector de municipio, con su centro como referencia.
La selección manual tiene prioridad sobre una respuesta de GPS pendiente;
al reabrir la pestaña solo se refresca el GPS si el permiso sigue concedido.
Las fechas verificadas pasan a estar debajo de las fotografías, mostrando
el periodo vigente en vez de la fecha antigua de inicio; los títulos tienen
hasta tres líneas y los bordes/sombras son más legibles en móvil.
Los formatos patrocinados de AriMar no cambian con esta actualización.


### Distancias y recordatorios de favoritos

La interfaz muestra el municipio en su línea y la distancia aproximada
al pie de cada tarjeta, calculada en línea recta desde la ubicación autorizada
del visitante. Si la ficha no incluye coordenadas del recinto, se utilizan las
coordenadas conocidas del municipio y la etiqueta especifica municipio.
Si no existe permiso de ubicación, no se inventa un km.

El detalle de cada plan contiene Recordarme. El visitante elige una
antelación que aún esté en el futuro: 15 min, 1 h o 3 h para actividades con
hora verificada; 1, 2, 3 o 7 días antes; y para planes en sábado o domingo
Viernes anterior, 18:00, en hora local de Canarias. El sistema produce un
archivo iCalendar .ics con alarma VALARM absoluta, incluyendo el cambio
de hora de Canarias. No se crea una alerta de horas para eventos sin hora
confirmada. Los programas que comenzaron hace semanas requieren una nueva
sesión confirmada para programar recordatorios.

Importante: la aplicación todavía es estática y NO ofrece notificaciones
push. El usuario debe abrir el .ics e incorporarlo al calendario que
utilice (Android/iOS/otros); las notificaciones dependen de la configuración y
la compatibilidad de ese calendario. La funcionalidad futura de recordatorios
push, cuentas y suscripciones se evaluará posteriormente, con permisos,
gestión de bajas y un servicio de envío. No se almacena geolocalización ni
suscripciones en el servidor.


### Novedades desde la última visita (sin notificaciones push)

El navegador guarda un inventario local de identificadores de eventos vistos
en la clave padonde_known_event_ids_v1 y lo compara con el catálogo actualizado.
La primera visita crea una referencia, sin presentar cientos de falsos nuevos.
En visitas posteriores aparece, por ejemplo, «6 planes nuevos» cuando el
catálogo contiene seis identificadores que el navegador aún no había visto.
La persona puede «Ver novedades» o «Marcar vistas». Las fichas modificadas
sin cambiar su ID NO se cuentan como nuevas. No requiere cuenta de usuario,
y no transmite al servidor ningún historial de lectura. Si se borra el
almacenamiento del navegador, se crea una referencia nueva.

### Push de nuevos eventos (PENDIENTE, no habilitado)

El contador anterior funciona solamente al abrir la web. NO es una
notificación del sistema con la aplicación cerrada. Para Web Push real faltan:
- Backend HTTPS con almacenamiento privado y persistente de suscripciones.
- Claves VAPID en secretos del servidor, bajas y expiración de suscripciones.
- Permiso solicitado exclusivamente tras pulsar «Activar avisos», no al entrar.
- Service worker con eventos push y notificationclick.
- Diferencias de eventos añadidos en la sincronización diaria, agrupadas en
  un solo resumen («6 planes nuevos en Gran Canaria») sin duplicados.
- Preferencias de isla o municipios, silenciar avisos, darse de baja;
  nunca enviar ni guardar ubicación precisa del dispositivo.

No se ha activado un servidor de envío push, ni se muestra un botón que
prometa notificaciones del sistema antes de existir el backend.


### Control editorial de programas y ubicaciones

Los carteles de programaciones de varios días se guardan como fuentes,
pero no se publican como una actividad individual. La sincronización
aplica program_quality.py, retira fichas genéricas de la exportación y
genera data/program_review_gc.json con los programas por desglosar.

ingenio_juvenil_program.py ejemplifica el protocolo: la iniciación al
boxeo del 17/11/2026 se importa por separado, en Las Palmas de Gran
Canaria (Barranco de la Ballena); el hockey del 6/11/2026 queda en
revisión porque el cartel solo dice Ingenio, sin instalación concreta.
El adaptador valida que el cartel oficial no ha sido reemplazado y
caduca el 17/11/2026. El municipio del organizador y el lugar real
de celebración son datos distintos.

### Auditoría de programas municipales de Gran Canaria

El archivo `data/municipal_program_audit_gc.json` registra los 21 municipios,
sus fuentes conocidas, el formato disponible y la siguiente tarea para
extraer actividades verificadas. En 2026 los 34 PDF descubiertos en Telde
no equivalen a 34 fiestas futuras; la revisión de contenidos debe comprobar
fechas, recintos y ediciones. Se distinguen agendas conectadas, extractores
parciales y portales que todavía necesitan identificación. Los PDFs escaneados
se procesan con revisión documental y **nunca** pasan automáticamente a la
agenda sin comprobar sus evidencias.

### Piloto de extracción visual de programas PDF de Telde

El sincronizador diario ya descubre los enlaces PDF municipales (34 programas
en el índice oficial el 26/10/2026). El script scripts/telde_pdf_vision.py
trabaja sobre ese inventario, sin inventar eventos a partir de los títulos.

Los PDF oficiales de San Francisco (1 página) y Caserones Altos (15 páginas)
no contienen texto extraíble; los resultados de prueba gratuitos están en
data/telde_pdf_pilot/report_sanfrancisco.json y
data/telde_pdf_pilot/report_caserones.json. Otras seis muestras confirmaron
también la ausencia de texto extraíble en sus primeras páginas.

El pipeline respeta robots.txt, limita origen a PDF HTTPS www.telde.es,
8 MB y 35 páginas, y calcula SHA-256 para reutilizar inferencias por
documento/página/modelo. Usa pypdfium2 para representar cada página como
imagen y Responses API con salida JSON estructurada y comprobación estricta
de fechas, títulos, horarios y referencia. No realiza OCR.

**Nunca publica el resultado del modelo directamente.** Los candidatos
van a data/telde_pdf_pilot/pending_review.json con la etiqueta
pending_review, documento y página para comprobación humana. No se
añaden actividades vencidas a la agenda. No modifica events.sqlite.

Prueba local sin API ni coste:

    python -m pip install -r scripts/requirements.txt
    python scripts/telde_pdf_vision.py --filename sanfrancisco26.pdf --max-pages 1

Prueba real de vision, solo cuando el usuario configure OPENAI_API_KEY:

    python scripts/telde_pdf_vision.py --filename sanfrancisco26.pdf --max-pages 1 --max-cost-usd 0.05 --api

Se incluye un workflow manual de GitHub Actions llamado Piloto PDF de Telde:
se ejecuta sin API por defecto. Para autorizar costes es necesario configurar
el secreto OPENAI_API_KEY en GitHub y marcar el campo api; el informe y cola
se entregan como artefacto telde-pdf-review.

Usamos por defecto gpt-5.6-luna; los precios actuales indicativos son
$0.20 por 1M tokens de entrada y $1.20 por 1M tokens de salida. El script
mide tokens y coste del modelo en cada respuesta. El tope de gasto del
script es orientativo, y no sustituye los limites reales del proyecto API.
NUNCA pegar claves secretas en el chat, archivos del proyecto o GitHub.


### Conector continuo de agenda del Ayuntamiento de Tejeda

El conector scripts/tejeda_agenda.py lee los artículos recién publicados en
https://tejeda.eu/agenda-eventos/ en cada sincronización diaria; importa
únicamente actividades con un día/mes futuro explícito, respaldado por la
fecha de publicación del artículo municipal. No presupone que los talleres
recurrentes sin fecha exacta tengan una sesión diaria; no inventa horarios,
entrada gratuita ni precio. Respeta robots.txt y verifica el dominio HTTPS
de cada detalle. Agaete y Firgas quedan inventariados con sus portales
institucionales actuales, sin considerarlos conectados mientras sus listados
mostrados continúen desactualizados.

### Recintos localizados en la descripción oficial (27/10/2026)
Cuando la ficha estructurada solo identifica un municipio, los adaptadores del Cabildo, Arucas y Tejeda pueden recuperar el **nombre** del recinto a partir de una indicación explícita en la descripción de la propia fuente (por ejemplo, `Lugar: Biblioteca Municipal...` o `en el Centro Cultural...`). Se rechazan nombres truncados, lugares de paso, menciones al organizador y programas que citan varios recintos. Nunca se geocodifica mediante suposición: las coordenadas siguen siendo las municipales hasta una validación separada.
El Cabildo usa `cabildo_scans.venue_inspected` para revisar primero las fichas con recinto pendiente, con el límite de 75 páginas por sincronización; `meta.json` ofrece `pending_venue_rechecks` y `venues_to_verify`. Las fichas originales se conservan para posteriores correcciones.

### Filtro de calidad de ubicación y segundas fuentes (octubre 2026)

- **Un plan sin recinto no se publica en el listado de actividades completas.** Se conserva en SQLite para poder mejorar su información sin perderlo. El informe `data/venue_review_gc.json` enumera los retenidos con su fuente; el resumen `public/meta.json` separa `approved`, `candidate_events`, `excluded_missing_venue` y `venues_verified`. Los programas que requieren desglose se revisan aparte.
- El enriquecimiento adicional `scripts/organizer_venues.py` consulta solo fichas de eventos específicas de una lista estricta de **webs oficiales de organizadores**, cuando la fuente primaria incluye un enlace autorizado. Comprueba la coincidencia del título, respeta `robots.txt`, no sigue redirecciones, limita el tamaño y la frecuencia de las peticiones y guarda caché. Solo toma el nombre fáctico del recinto; no copia descripciones.
- Los recintos sin un único lugar claro (programas itinerantes, sedes múltiples o meras referencias al municipio) siguen retenidos. No se infieren coordenadas GPS a partir del nombre del edificio: el mapa conserva el indicador explícito de precisión municipal hasta validar la geolocalización.
- Una importación posterior no borra un recinto que ya quedó confirmado por una fuente oficial, aunque la nueva respuesta omita ese campo. La fuente original del evento permanece intacta.


### Enriquecimiento verificable de la ubicación de ULPGC

Cuando el Cabildo enlaza expresamente a una ficha de agenda ULPGC y el
nombre de la actividad **especifica el edificio** en el propio título
(por ejemplo «Campaña de hemodonación: Facultad de Ciencias del Mar»),
se muestra ese recinto en lugar del texto «por confirmar». La distancia
sigue siendo **aproximada al municipio** mientras no existan coordenadas
contrastadas del lugar. La web de ULPGC responde HTTP 403 a la consulta
automática: no se sortean restricciones, no se copia su página ni se generan
horarios diarios a partir de un intervalo impreciso.

El caso documentado de los días 26–27 de octubre de 2026 se contrasta con
la captura de la ficha ULPGC y el aviso oficial sanitario del 23/10/2026:
26/10, 09:30–19:45; 27/10, 09:00–18:30. Como el primer día ya ha pasado,
la ficha próxima del 27/10 utiliza su horario real y no el cierre como
hora de comienzo. Las demás campañas sin inicio confirmado mantienen
solo la fecha, no una hora supuesta. La corrección se aplica en cada
extracción incremental del Cabildo, sin interrumpir las demás fuentes.


### Auditoría automática de calidad (Gran Canaria)

Cada sincronización ejecuta scripts/audit_source_health_gc.py y guarda
data/source_quality_gc.json, con métricas por fuente, recintos aún sin
verificar, precios desconocidos, programas pendientes y coincidencias
potencialmente duplicadas. Los errores de red y parser se diferencian
expresamente de las fuentes sanas que no tenían eventos nuevos.

Los eventos con recinto desconocido permanecen en
data/venue_review_gc.json y NO se presentan como ubicaciones verificadas.
El parser extrae lugares únicamente cuando hay una mención clara en la
información oficial, nunca por mera semejanza de nombres.
Los nombres de recintos conocidos no implican que sus coordenadas estén
verificadas: las distancias se calculan a centros de municipio
si accuracy=municipality.

La deduplicación del catálogo combina anuncios de fuentes oficiales
cuando título, municipio, fecha, hora y recinto coinciden. Un caso de
recintos contradictorios se conserva para revisión humana. Las fuentes
originales siguen registradas en SQLite.


### Fechas y tarjetas por jornada

Los eventos de **2 o 3 días consecutivos con un intervalo explícito
de fechas** se publican como una tarjeta por día. Primero se descartan
carteles/programas genéricos, luego se identifican las fechas de cada jornada
y finalmente se deduplican solo anuncios correspondientes a la **misma fecha**.
Si un evento va del 28 al 29, salen una ficha del 28 y otra del 29.

No se inventan sesiones si un espectáculo cruza la medianoche o si las
fuentes aportan horarios parciales ambiguos. Los cursos, exposiciones y otros
planes con rangos largos **continúan visibles durante todos los días en que
siguen vigentes** en los filtros temporales, sin generar decenas o cientos de
supuestas sesiones diarias. Para disponer de una tarjeta por sesión semanal
o mensual hay que leer las fechas reales del programa original.

Las tarjetas diarias derivadas tienen IDs negativos estables que no colisionan
con los IDs positivos originales de SQLite: los favoritos y enlaces
compartidos pueden señalar cada jornada. Los originales permanecen intactos
en SQLite para conservar procedencia y permitir correcciones.

No confundir deduplicación con control de calidad: las fichas sin recinto
concreto continúan en data/venue_review_gc.json para verificar lugar
real y no mostrar una falsa ubicación exacta. El campo occurrences de
public/meta.json desglosa esta proyección, y el campo
verified_source_events_before_daily_projection muestra cuántos anuncios
individuales, previos a la expansión, tenían recinto contrastado.


### Ubicaciones verificadas: recinto o municipio

El nombre del recinto viene de la fuente oficial del evento. Su posición en
el mapa solo deja de ser municipal cuando el par (municipio, recinto) coincide
con una referencia geográfica contrastada por separado. La lista offline
scripts/verified_venue_coordinates.py contiene cada punto de OpenStreetMap
y una fuente institucional que confirma el edificio o complejo.

Primera fase: siete recintos y alrededor de 181 fichas del catálogo actual.
accuracy=venue representa el punto del edificio o complejo identificado, no
necesariamente su puerta, una ruta por carretera ni una posición GPS exacta.
Para todos los recintos aún no verificados se utiliza el centro del municipio,
accuracy=municipality. No se realizan búsquedas geográficas imprecisas durante
la sincronización diaria.

El upsert y una revisión completa de coordenadas en cada sincronización
emplean la misma tabla. Si un organizador corrige el nombre del recinto, las
coordenadas se revisan también. Se conservan los IDs de los eventos.

Las actividades sin recinto identificable siguen pendientes de contraste con
los organizadores. No se fabrican ubicaciones ni se publican como planes
completos aquellas que no cumplen la política de calidad.


### Cola de recintos pendientes: corroboración entre fuentes

La cola data/venue_review_gc.json contenía 149 fichas en la revisión del
27/10/2026, no publicadas hasta identificar su recinto. El módulo
scripts/cross_source_venue_facts.py comprueba cada sincronización si otra
fuente independiente publica el mismo título, mismo municipio y mismo día.
Solo recupera un lugar cuando existe exactamente una opción específica y
no hay conflicto de horario o recinto. La prueba inicial identifica dos
recintos confirmables de esa cola; tres coincidencias ambiguas se mantienen
pendientes. Los demás casos siguen pendientes de consulta al organizador.
No se aplican coincidencias difusas, ni se inventan recintos.

La distancia del usuario continúa basándose en el punto preciso del recinto
para los siete recintos cartografiados y, en los demás casos publicados, en
el centro aproximado del municipio. Nunca es distancia de conducción.


### Comprobación automatizada de recintos a partir del organizador (27 oct 2026)

La cola data/venue_review_gc.json contiene fichas con recinto sin
verificar y no publicadas. El segundo contraste organizer_venues.py
admite páginas individuales de una lista explícita de organizadores.
structured_organizer_venues.py comprueba sala por fecha y sesión
de OFGC, lugar con vínculo oficial de LPA Cultura y campo Lugar:
de Casa África. Los nombres de recinto requieren coincidencia del
título y compatibilidad municipal; un evento de Agüimes, Madrid o
París no puede aparecer como localizado en Las Palmas de Gran Canaria.

Cada página de un mismo programa se consulta una vez en cada ejecución
y se comprueba para cada fecha individual. ULPGC queda fuera del rastreo
automatizado por su robots.txt restrictivo. La actualización diaria
contrasta las nuevas páginas y solo publica recintos verificados.


### Auditoría automática de precios

Tras cada sincronización diaria se genera data/price_provenance_audit.json
desde el catálogo publicado. Distingue gratis, precio fijo,
tarifa mínima, mínimo cero ambiguo y precios contradictorios.
Nunca convierte automaticamente "Desde 0 EUR" en gratis porque
solo ciertas entradas podrían ser gratuitas.
Este control es clasificación, no verifica en directo todos los editores.
Para comprobar la plataforma de tickets contra su API pública:
python scripts/audit_price_provenance.py --live-tickets
La pasada diaria de sincronización consulta ya esa plataforma:
el informe diario no duplica solicitudes a su API.


### Filtros de descubrimiento (27/10/2026)

La vista **Explorar** combina los atajos Hoy/Mañana/Fin de semana/7 días/Próximamente
con un selector **Elegir fechas**: mes completo o intervalo inclusivo de días.
Incluye las actividades cuyo periodo se superpone con el rango seleccionado;
no crea eventos nuevos y depende de la cobertura futura del catálogo.

El filtro **Categorías** es acumulativo (OR): tocar varias categorías
muestra cualquiera de ellas; «Todas» limpia la selección. La preferencia
de categorías se recuerda únicamente en el navegador. Se mantienen los
avisos del calendario, las coordenadas autorizadas, favoritos y los anuncios.


### Extracción condicionada de programas PDF de Telde

La lista oficial public/municipal_programs.json contiene enlaces a programas
de barrios. scripts/telde_pdf_auto.py revisa los PDF recientes usando HTTPS,
robots.txt, un límite de documentos y un límite de páginas por ejecución.

- PDF con texto: extracción convencional de actividad, fecha y hora, con
  coincidencia literal entre la prueba textual y el propio documento.
- PDF escaneado o insuficiente: se envía la página como imagen a gpt-6-luna
  mediante Responses API, solo cuando existe OPENAI_API_KEY en los secretos
  del entorno. Sin secreto no hay llamadas ni coste.
- Verificación: cada candidato tiene PDF y página de origen y hash SHA-256.
  Se rechazan años incompatibles y fechas imposibles. Un modelo de IA no
  puede publicar eventos directamente; quedan pendientes de revisión.
- Costes: límite de documentos, páginas, llamadas y gasto estimado diario.
  La caché por hash/página evita pagar otra vez por lo mismo. No se
  guardan imágenes ni claves en Git.
- Se ejecuta desde el workflow de actualización diaria en GitHub Actions,
  cuando la clave de API está disponible.

Prueba local sin gasto:
python scripts/telde_pdf_auto.py --filename sanfrancisco26.pdf
python scripts/telde_pdf_auto.py --filename caseronesaltos26.pdf --max-pages 2


### Seguridad de extracción de programas PDF

Se verificó que el piloto había incluido por error una ficha de demostración
de Caserones Altos el 07/11/2026. Se eliminó del conjunto verificable y el
sincronizador compara siempre **la huella SHA-256 de la descarga real**,
el seguimiento de la página y las dos respuestas de lectura visual independiente
antes de publicar. También limpia las fichas exclusivas del importador PDF que
hayan perdido esa prueba documental. No borra las actividades obtenidas de otras
fuentes. Los documentos históricos pueden producir cero actos futuros;
esto es un resultado correcto, no un fallo de la conexión.


#### Proceso automático de programas PDF de Telde

1. Detección previa: refresh_telde_pdf_index.py actualiza la relación oficial
   de programas antes de pasar a la extracción, sin un día de retraso.
2. Descarga: solo PDFs HTTPS publicados en www.telde.es y respetando robots;
   límite de tamaño, caché y hash SHA-256 del archivo oficial.
3. Extracción: primero texto nativo; después visión OpenAI Responses API con
   gpt-6-luna si hay clave OPENAI_API_KEY en los secretos de GitHub Actions.
4. Doble verificación: dos lecturas independientes deben coincidir en actividad,
   fecha, hora, recinto, archivo y página. Las respuestas originales y la
   huella del PDF real se cotejan de nuevo antes de publicar.
5. Publicación: sync_events.py importa solo los actos que superen esa
   verificación; retira registros PDF de prueba u obsoletos que no la cumplan.
6. Coste limitado: hasta 2 documentos, 3 páginas por documento, 4 llamadas
   IA y presupuesto nominal 0,05 USD por revisión automática diaria.

Los PDFs históricos, ilegibles o sin actuaciones futuras comprobables
no crean fichas, aunque estén descubiertos en el inventario.

#### Prioridad de PDF futuros y archivo histórico

- El extractor da prioridad a los PDF que ya muestran actividades con fechas
  futuras y después a los programas todavía no inspeccionados. La fecha de
  subida de un PDF **no** demuestra la fecha de sus eventos.
- Los actos con fecha vencida se trasladan de pending_review.json (o
  verified_events.json) a data/telde_pdf_pilot/expired_archive.json. Se
  conservan título, fecha, PDF, SHA-256 y página original, pero ya no son
  candidatos de publicación. Archivar varias veces es seguro e idempotente.
- Si una extracción parcial solo contiene actos cuya última fecha conocida
  venció hace más de siete días, se aplaza el resto de ese PDF durante siete
  días. **No se declara finalizado**: podrían quedar actos futuros en páginas
  aún no leídas. El PDF sigue elegible tras la pausa y un PDF nuevo puede
  adelantarlo. La opción --filename permite inspeccionarlo explícitamente.
- Una fecha final solo permite declarar un programa terminado cuando existe
  una fecha de fin verificada con fuente PDF oficial y asociada al SHA-256
  exacto, nunca por inferencia del nombre o la ruta.
- python scripts/telde_pdf_auto.py --archive-only realiza el mantenimiento
  histórico y los aplazamientos a partir de evidencias existentes, sin
  descargar documentos ni llamar a IA, incluso sin OPENAI_API_KEY.
- El workflow diario guarda el archivo histórico y el informe de
  aplazamientos, y mantiene el tope nominal de gasto de IA.

### Programas oficiales PDF de más ayuntamientos

El motor de PDF municipal reutiliza extracción visual, doble lectura
independiente, caché por SHA-256/página, validación de recinto y control de
gasto. La lista de nuevas fuentes está en scripts/municipal_pdf_sources.py:
Santa Lucía de Tirajana, Agüimes y Gáldar. Las URLs proceden de sus páginas
oficiales y están limitadas al dominio HTTPS municipal.

- python scripts/refresh_municipal_pdf_index.py: inventario oficial.
- python scripts/municipal_pdf_auto.py --archive-only: mantenimiento sin IA.
- python scripts/municipal_pdf_auto.py --api: extracción de páginas futuras
  con doble lectura visual, con OPENAI_API_KEY configurada.
- Los programas del Rosario de Agüimes y Santiago de Gáldar 2026 tienen
  fecha final documentada en portadas oficiales y se omiten en trabajos de IA
  una vez terminados, sin eliminarlos del inventario.
- Cada actividad se revalida contra las dos lecturas guardadas, la página
  de origen y la huella del archivo; no se sobreescriben registros de otra
  fuente con igual título y fecha.
- Presupuesto de este nuevo trabajo: máximo 4 llamadas y 0,05 USD nominales
  por ejecución, independiente de los límites de Telde.

La fecha de subida del PDF nunca determina la fecha de una actividad.
No se aceptan PDFs externos ni anexos sin enlazar desde fuente municipal.

### 21 municipios: control de cobertura y hechos municipales verificados

El archivo public/municipal_coverage.json actualiza a diario la matriz de
cobertura con el inventario de los **21 municipios**. Diferencia fichas
procedentes de ayuntamientos de fichas de terceros o del Cabildo y no
declara completa la cobertura donde solo hay noticias parciales.

El módulo scripts/gc_documented_events.py incorpora actividades de 2026
de Agaete, Vega de San Mateo, Santa María de Guía y San Bartolomé de
Tirajana, siempre con evidencia de fecha, hora, recinto y artículo oficial.
En cada actualización vuelve a leer las páginas institucionales y desactiva
las entradas cuya fecha ya pasó o cuya evidencia desapareció.
No inventa precios ni gratuidad. Los anuncios revisados de 2026 son
hechos documentados, no un conector que permita asumir futuras ediciones.
Cuando la información oficial no es suficiente, el acto queda excluido.

El conector municipal PDF guarda un checkpoint por cada página confirmada;
si una segunda página da error, la evidencia de la anterior permanece.
El monitor y las pruebas no implican que todos los ayuntamientos ya
publiquen una agenda completa. La prioridad pendiente es ampliar fuentes,
mejorar los recintos sin verificar y confirmar la ejecución diaria.

### Radar de noticias para ayuntamientos pendientes

python scripts/gc_source_radar.py --max-sites 8 revisa progresivamente
hasta ocho municipios con cobertura incompleta por ejecución y conserva
candidatos en data/gc_radar_leads.json. Comprueba robots.txt, exige
enlaces HTTPS del propio dominio municipal y no sigue enlaces externos.

Los resultados del radar son titulares pendientes de contrastar,
no son eventos ni entran en el calendario. Permiten localizar nuevas
fuentes de noticias, programas y agendas sin inventar fechas ni horas.
El informe conserva la fecha de cada comprobación y los errores de
acceso, para distinguir municipios sin cobertura de webs temporalmente
inaccesibles.

### Recuperación conservadora de recintos sin identificar (octubre 2026)

La prioridad es reducir data/venue_review_gc.json, no publicar
fichas con un centro municipal inventado.

- cross_source_venue_facts.py admite variaciones acotadas del título
  (Concierto, San Rafael o Telde) cuando existe otra ficha con
  fecha, municipio y horario compatibles y un recinto concreto. Rechaza
  conflictos entre recintos. No se comparan títulos con IA.
- official_venue_confirmations.py revisa exclusivamente artículos
  institucionales de Gáldar e Infecar y corrobora recintos de Oliva Lara,
  Frontón King y ExpoDeca. Si la fuente falla, se mantiene pendiente.
- Las fuentes de venta no bastan para corregir recintos, salvo cuando
  el evento enlaza además a la página oficial de Telde Cultura y coincide
  específicamente el acto, día y municipio.
- Las rutas con varios puntos y ubicaciones contradictorias siguen en
  la cola de revisión.

### Recintos que aparecen solo en carteles de actos

El extractor visual restringido scripts/poster_venues.py verifica el original
de la imagen asociada a un evento del Cabildo, admite tres carteles por
ejecución, seis llamadas visuales y un coste nominal máximo de 0,035 USD.
Requiere dos lecturas de imagen que coincidan en título, fecha y nombre del
recinto antes de publicar el lugar; no deduce fechas ni sedes.

El cartel de Noche de Finaos (Mogán, 31/10/2026, 19:00) anuncia Parque
Nicolás Quesada; una persona lo verificó en la imagen aportada y su
huella SHA256 original se comprueba antes de aplicar la corrección.
Si cambia el cartel o aparece una ubicación ambigua, se mantiene pendiente.
Solo se almacena prueba textual mínima e identificadores, nunca los
ficheros de imagen ni la clave API. La auditoría queda registrada en
data/poster_venue_pilot.

### Agendas culturales directas: LPA Cultura, Teatro Pérez Galdós, Auditorio Alfredo Kraus y Sociedad Filarmónica

El conector scripts/official_culture_calendars.py consulta cada noche
los listados y las fechas impresas por estas cuatro entidades oficiales:

- Teatro Pérez Galdós: lee las fechas y sesiones concretas de cada
  espectáculo desde su página individual, conservando varios horarios
  anunciados del mismo día en una sola ficha, sin inventar funciones
  intermedias. Incluye musicales y programación familiar de 2027.
- LPA Cultura: selecciona conciertos, actividades culturales y
  sesiones especiales con recinto reconocido. Rechaza recorridos con
  varios puntos y convocatorias sin sede confirmada.
- Sociedad Filarmónica: importa conciertos con fecha, hora y
  sala publicados en la agenda de la propia sociedad.
- Auditorio Alfredo Kraus: consulta la agenda oficial y las fichas
  de cada espectáculo, con días y horarios concretos para conciertos,
  musicales y programación familiar; no inventa sesiones.

Respeta robots.txt, HTTPS, dominios exactos, sin redirecciones,
límites de tamaño y máximo de páginas. No copia sinopsis ni imágenes.
Los datos de precio no publicados quedan desconocidos. Las fuentes
se comprueban y registran de forma independiente para que un fallo
en un teatro no afecte a los demás municipios. Las 108 fichas
sin recinto que estaban apartadas quedan fuera de este trabajo.

### Agenda de Teatro Cuyás y Sala Insular

El módulo scripts/official_stage_agendas.py lee las agendas oficiales
de https://teatrocuyas.com/agenda.html y
https://salainsulardeteatro.com/agenda.html. Verifica robots.txt y extrae
cada función con fecha, hora, título, sala y su enlace oficial.
Excluye campañas de venta de entradas y las fechas pasadas.
No presupone acceso gratis ni tarifas.

Al conciliar, se prefiere el recinto indicado por la cartelera
original frente a una ficha idéntica del Cabildo, únicamente cuando
la fecha y la hora no son contradictorias. El registro original
queda en SQLite para trazabilidad.

### Importación de fuentes culturales por isla y seguimiento de productoras

La sincronización diaria de GitHub Actions incorpora automáticamente
el Festival Internacional de Música de Canarias, comprobando isla, fecha
y hora tanto en el índice como en la ficha individual; únicamente los
conciertos verificados de Gran Canaria se publican por ahora.

También incorpora los calendarios municipales estructurados de los teatros
Auditorio Agüimes y Cruce de Culturas, y del Centro Cultural Guaires.
No crea funciones a partir de carteles generales sin hora.

Camino Viejo Producciones: su web estaba en construcción en octubre de
2026. El sistema sigue los créditos que figuran en las agendas oficiales
de recintos y ayuntamientos, incluido Blancanieves, más allá del espejo
del 7 de noviembre de 2026 en Agüimes; no publica su repertorio
sin fecha ni recinto.

Teatro Víctor Jara: la noticia municipal oficial de septiembre de 2026
verifica siete actuaciones con fecha y recinto. Los horarios no presentes
se dejan sin concretar; las seis funciones que ya tenían horarios
contrastados conservan sus fichas. La página monográfica de
programación aún muestra la temporada de 2025, y no se reutiliza
como fuente de los nuevos actos. Las próximas publicaciones se
revisarán de nuevo antes de su importación.

El inventario data/island_source_registry.json enumera las ocho islas y
prioriza cada búsqueda por organizador oficial, recinto, festival,
productora y ticketing. El informe public/island_source_status.json
distingue conexiones activas, solo monitorizadas, incidencias y
créditos de productoras explícitamente contrastados. Solo Gran Canaria
tiene activada la publicación. Para añadir otra isla se requiere
un mapa completo de municipios y recintos con coordenadas, reglas de
deduplicación insular y pruebas antes de habilitarla.

Regla: fecha, isla, municipio, recinto y URL oficial verificables;
no se inventan horas o precios. No se importan eventos pasados
como si fueran futuros ni conciertos anunciados para otras islas.

### Telegram: avisos automáticos de errores de importación

El flujo independiente .github/workflows/telegram-sync-alerts.yml se
activa al terminar Actualizar eventos oficiales, incluso si este falla.

- Una sincronización fallida genera un aviso inmediato, también si el
  trabajo se inició por un cambio de código.
- La sincronización programada cada día con errores técnicos en fuentes
  genera un único resumen con la lista de conectores afectados y enlace
  a la ejecución de GitHub.
- Una ejecución correcta sin incidencias no envía mensajes.
- Una falta de recinto, un precio no confirmado o una fuente sin nuevos
  eventos no son por sí solos errores técnicos.
- La vigilancia omite los errores parciales repetidos durante los
  frecuentes pushes, pero sí comunica cualquier fallo completo.

CONFIGURACIÓN PRIVADA UNA SOLA VEZ:

1. En Telegram abre @BotFather y envía /newbot. Crea un bot para la
   aplicación y conserva el token de forma privada.
2. Abre el nuevo bot en Telegram y pulsa Iniciar o envía /start.
3. Obtén el ID del chat donde quieres recibir los avisos. No reveles
   el token a bots externos ni lo pegues en esta conversación.
4. En GitHub, repositorio talaverilla85/CanaryEvent, abre
   Settings > Secrets and variables > Actions > New repository secret.
   Crea TELEGRAM_BOT_TOKEN con el token de BotFather y
   TELEGRAM_CHAT_ID con el ID del chat de destino.
5. En Actions > Avisar por Telegram de incidencias de CanaryEvent >
   Run workflow, ejecuta la prueba manual. Llegará una notificación
   de prueba si las credenciales son correctas.

La integración queda preparada, pero no se puede confirmar ningún
envío de mensajes hasta configurar ambos secretos.

### Recintos en el texto completo del Cabildo: recuperación de octubre 2026

La ficha de Taller infantil: Repostería encantada (30/10/2026)
tiene una descripción estructurada cortada a 500 caracteres, aunque
la página visible incluye Biblioteca Insular de Gran Canaria,
Remedios 7, 35002 Las Palmas, acceso gratuito y las sesiones 16:30 y
18:30. En Moya, una presentación literaria confirma la Casa-Museo
Tomás Morales, Plaza Tomás Morales s/n, 35420.

El lector utiliza el panel de información completo de cada ficha
además del esquema abreviado. El módulo official_address_locations.py
comprueba nombre institucional, calle, número y código postal
en un mismo bloque antes de aceptar una dirección documentada.
venue_facts.py sigue leyendo ubicaciones inequívocas dentro del
texto completo. Una mera mención al organizador no es una prueba.

Las fichas ya escaneadas sin recinto se vuelven a revisar usando
la marca versionada cabildo_scans.full_text_v2; se mantiene el máximo
de 75 páginas por ejecución y una pausa respetuosa entre consultas.
Los lugares ambiguos permanecen fuera del catálogo. Dos sesiones
no se convierten en una duración continua falsa: se guarda la
primera hora de inicio y se indican las demás en el resumen.
No se asignan coordenadas exactas sin verificación independiente.

### Carteles y calendario oficial de Telde: octubre de 2026

El cartel oficial de El lago de los cisnes - International Ballet
Company confirma el Teatro Municipal Juan Ramón Jiménez (Telde),
1 de noviembre de 2026, 18:00. La ficha del Cabildo muestra sólo Telde.

El módulo scripts/telde_hall_venues.py coteja el enlace exacto, el
título, la fecha y la hora de la función con la lista de eventos
vinculados al Teatro Juan Ramón Jiménez en la web original de
Telde Cultura. No infiere el lugar de la casilla Organiza, ni
utiliza fechas de una edición distinta.

El lector visual scripts/poster_venues.py pasa de 3 a 10 carteles
por ejecución, con un límite de 20 consultas de IA (dos lecturas
independientes por cartel), coste nominal máximo 0,075 USD y caché
para evitar gastar repetidamente en carteles no concluyentes o
defectuosos. Acepta títulos principales distintivos sin el sufijo
de una productora; comprueba la fecha y rechaza lugares ambiguos.
La ausencia de recinto verificable sigue excluyendo al evento.
No se guardan imágenes ni claves API en GitHub.

### Recintos en enlaces originales de Cultura Canarias

La ficha del Cabildo puede enlazar una página cultural con sede
precisa expresada en una frase, no en un campo Lugar:.

Caso confirmado: taller de tarantismo y pizzica, 30/10/2026
a las 17:00. La fuente oficial indica Gimnasio del Aulario de
Santa Teresa, Campus del Obelisco, ULPGC: no Teatro Guiniguada.

El lector ya consultaba la web del organizador, pero rechazaba
frases como «La sede del taller será el ...». Ahora el adaptador
del dominio cultura.icdcultural.org lee el contenido del evento
y comprueba la fecha, la hora y una frase explícita de recinto.
No se toman ubicaciones desde el pie de página ni por la simple
presencia del nombre de un organizador.

Se renueva la versión del analizador para volver a revisar las
fichas previamente descartadas, sin depender de que venza la
caché negativa. Las pruebas comprueban fecha, hora, municipio,
lugar contradictorio y dominios no autorizados.

### PDF oficiales de Telde de más de 8 MB

El lector de programas en PDF conserva su límite de seguridad de
8 MB por archivo. Un PDF mayor no se acepta ni se interpreta
parcialmente: se registra como `pdf_oversize` en el informe
de la ejecución, se aplaza una semana y se reintenta después.
Otros PDF elegibles se pueden procesar en la misma ejecución,
sin desperdiciar el presupuesto de llamadas a IA.

GitHub Actions muestra un aviso amarillo (en lugar de un
error rojo) y el informe `data/telde_pdf_pilot/auto_report.json`
conserva la URL y el momento de reintento. Esto es un aplazamiento
explícito: no se afirma que el PDF se haya importado.

### Fuente original de la ULPGC bloqueada: cine Los modernos 2026

La agenda individual de la ULPGC puede responder HTTP 403, pero el
blog oficial de su Biblioteca confirma que las nueve proyecciones del
ciclo Los modernos (23/10-18/12/2026) tienen lugar a las 19:00 en
el Salon de Actos del Edificio de Humanidades.

El modulo scripts/ulpgc_cinema_venues.py lee esa evidencia original
accesible sin burlar el 403 y la aplica exclusivamente a ocho
fichas concretas aun sin recinto, cotejadas por titulo, dia,
municipio, fuente original y enlace de la agenda de la ULPGC.
No se utiliza el domicilio de la universidad ni el del pie de pagina.
Si la fuente independiente deja de confirmar el programa, los casos
permanecen retenidos. La revision se ejecuta diariamente antes del
lector visual de carteles, ahorrando consultas de IA.

### Reconciliar Teatro Cuyas frente a enlaces y listados de Sala Insular

Janto es la taquilla del Teatro Cuyas, no la fuente mas fiable de
datos estructurados: la agenda principal y la del Circuito de
Artes Escenicas proporcionan las funciones y su recinto original.
Algunos enlaces del Cabildo apuntan a una URL de la Sala Insular
porque comparten identificador numerico en el CMS. El dominio del
enlace no prueba que esa sala acoja la funcion.

El modulo cuyas_corroboration.py coteja el ID numerico completo del
espectaculo, titulo exacto normalizado, municipio y el conjunto de
fechas verificadas por los organizadores. Solo si todos coinciden
recupera el recinto para la copia del Cabildo sin resolver.
Los eventos originales permanecen como tarjetas prioritarias.
Las copias del Cabildo con una sede contradictoria Sala Insular /
Teatro Cuyas quedan excluidas del catalogo publico (sin borrar
SQLite), registradas en program_review_gc.json bajo
source_venue_conflicts. Asi no se publican dias o escenarios falsos
como la supuesta tercera funcion del 22 de noviembre de Escape Room.
Los datos de fuentes ambiguas o fechas distintas no se deducen.

### Fuente multisisla anotada: EcoEntradas (octubre de 2026)

**No olvidar para la expansion a Tenerife, Lanzarote, Fuerteventura y
resto de Canarias:** [EcoEntradas](https://www.ecoentradas.com/)
publica espectaculos y entradas de recintos situados en distintas islas.
Puede reutilizarse una vez exista el mapa de islas, municipios y
recintos y se comprueben fechas y horas de cada funcion con la pagina
de sesion y el selector de zona. La fuente esta anotada como
`ecoentradas-interinsular` en `data/island_source_registry.json`.

**Estado actual:** conector `scripts/aldea_ecoentradas.py` habilitado
solo para Centro Municipal de Cultura de La Aldea (Gran Canaria),
recinto EcoEntradas 132. El propio municipio tiene un error TLS en
su web; por eso usamos la taquilla original, no ignoramos el aviso de
certificado. La fuente confirma Kike Perez, 14/11/2026 a las 20:00,
entradas desde 10 euros y coordenadas del recinto. Se respeta robots.txt
y se exigen titulo, fecha completa, hora, isla, municipio y recinto.

**Para otras islas:** fuente candidata para descubrimiento, NO importador
activo. Ni la presencia de un recinto en EcoEntradas ni una cuenta
de eventos es evidencia de cobertura integral de esa isla.

### Cierre de las lagunas de municipios de Gran Canaria (octubre 2026)

Cada municipio de los 21 tiene una entrada en el registro municipal;
esto NO implica una cobertura completa de todos sus eventos.

- **Artenara**: VI Feria de las Tradiciones del 1/11/2026 en Plaza
  de San Matias, cotejada con un anuncio del Ayuntamiento y una ficha
  independiente del mismo acto. El mercadillo 31/10 sigue pendiente
  por sede no demostrada.
- **Moya**: siete actos de su folleto Otono es Cultura 2026 (31/10
  al 27/11), revisados pagina a pagina con sus recintos, precios
  por confirmar y horas solo donde aparecen. NO descargar
  automaticamente: el robots.txt de villademoya.es proh?be / .
- **Valsequillo**: actividad municipal de narracion oral 30/10/2026
  en Biblioteca Municipal, confirmada en el ICS que el Ayuntamiento
  enlaza. Los datos futuros de Google Calendar NO se rastrean: su
  robots.txt marca Disallow /. Esta es una ficha 2026 revisada,
  no un conector continuo.
- **Mogan**: Dia de la Infancia el 14/11/2026 a las 10:00 en Plaza
  Perez Galdos, confirmado en noticia municipal 27/10. No se supone
  un feed completo por un solo articulo.
- **La Aldea**: EcoEntradas permite importar sesiones del Centro
  Municipal de Cultura; falta reparar la confianza TLS de la fuente
  municipal, sin desactivar SSL.
- **Firgas**: su agenda oficial publica no ofrece actos culturales
  futuros confirmados en la revision actual. Mantener en radar y
  NO confundir gestiones administrativas con ocio cultural.

El objetivo es 21/21 municipios con eventos contrastados cuando
existan y, de forma separada, fuentes municipales activas y
actualizables. Las fuentes que proh?ben rastreo o tienen contenido
caducado se declaran parciales, no completas.

### Firgas: Noche de Finaos 2026 por corroboracion independiente

La noche del 31 de octubre de 2026 a las 21:00, la Casa de los
Mayores de Firgas acoge un asadero de castanas con la Agrupacion
Folclorica Tacande. Coinciden tres publicaciones locales,
consultables en scripts/firgas_local_confirmed.py. Esta entrada
tiene origen **no municipal**, etiqueta propia y caduca al pasar
el dia. Firgas sigue sin una agenda del Ayuntamiento que publique
actos culturales futuros con regularidad: NO proclamar cobertura
municipal exhaustiva por este evento aislado.
