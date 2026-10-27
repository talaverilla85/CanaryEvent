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
