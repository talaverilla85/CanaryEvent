# Páginas SEO de planes por intención de búsqueda — D’Parranda

Las páginas de búsquedas de ocio se generan en servidor con el catálogo **publicado y vigente** de PostgreSQL. No se crean URLs por cada día ni se cambia la aplicación principal, los anuncios, el panel o los extractores.

## Cuatro rutas permanentes

- `/que-hacer-este-fin-de-semana-gran-canaria` — selecciona los eventos con **fecha de inicio de sesión en el viernes, sábado o domingo** correspondiente a la fecha actual de Canarias. Viernes a domingo usa el fin de semana en curso; lunes a jueves usa el próximo. El domingo solo propone las sesiones que aún tienen fecha de ese día. No incluye un programa antiguo únicamente porque su fecha de fin cubra el fin de semana.
- `/que-hacer-hoy-gran-canaria` — selecciona los eventos con fecha de inicio hoy, según `Atlantic/Canary`. Una actividad mensual no aparece como disponible a diario si no consta una sesión concreta.
- `/que-hacer-con-ninos-gran-canaria` — selecciona planes con **mención explícita de destinatarios infantiles o familiares** en el título o la descripción del organizador. No basta la etiqueta genérica `familia` ni la palabra «familia» como tema de una obra para evitar falsos positivos en comedias para adultos. Cada ficha pide confirmar la edad recomendada.
- `/planes-gratis-gran-canaria` — selecciona solo registros explícitamente marcados con `free=true/1`. «Precio no disponible» no equivale a gratuito; puede haber reserva obligatoria según el organizador.

**No se crea «mañana» todavía:** los datos actuales apenas proporcionan una sesión publicada para el día siguiente y la intención de búsqueda podría producir una página pobre o repetida. Se priorizan estas cuatro rutas mejor diferenciadas.

## Indexación responsable y automatización

Cada página posee título, descripción, canonical, textos editoriales propios, enlaces internos y tarjetas con su fuente original. Se genera el HTML en servidor desde `lib/seo-pages.js`; no se requiere JavaScript para que Google vea los eventos.

Las páginas de intención usan un filtro SEO de al menos **tres planes distintos con contenido útil**, dirección del recinto, fecha, URL HTTPS y una descripción informativa de 90+ caracteres no genérica. Las sesiones repetidas de la misma obra no cuentan como planes distintos. Si un día no se alcanza, la URL sigue accesible para personas pero devuelve cabeceras y meta `noindex`. Se reevalúa automáticamente en cada petición y cuando cambie el catálogo.

El nuevo sitemap **dinámico** `https://dparranda.es/sitemap-planes.xml` contiene solo las páginas de intención que actualmente superan su filtro; `robots.txt` lo anuncia junto a los dos sitemaps existentes. Cuando una página deja de alcanzar la calidad (por ejemplo, «hoy» al cambiar de día), sale del sitemap, sin generar URLs históricas por fecha.

Se añaden enlaces desde la parte pública de la portada y desde la navegación de las páginas SEO existentes. Las fichas de eventos individuales mantienen sus propias reglas SEO; esta implementación **no rebaja el filtro de fichas** y tampoco modifica la eliminación HTTP 410 de las caducadas.

## Pruebas y mantenimiento

`node --test tests/seo-intent-pages.test.mjs tests/seo-pages.test.mjs tests/event-seo.test.mjs`

Los tests cubren cambios de semana y de año, domingo, horario de Canarias, itinerarios largos con fecha de fin posterior, eventos familiares realmente aptos, prohibición de inferir gratuidad, eventos repetidos, canonical y sitemap condicionado por calidad.

Para futuras islas, añadir datos y rutas locales solo cuando exista volumen y fiabilidad suficiente; estas páginas se limitan expresamente a Gran Canaria.
