# D’Parranda — fase 1 SEO local (Gran Canaria)

Fecha de preparación: 21/11/2026.

## Estado
- Trabajo en la rama `seo/gran-canaria-pages-pilot-20261121`. Publicación en producción **pendiente de revisión de preview**.
- La portada actual y su JavaScript permanecen intactos salvo una navegación ligera a las cinco nuevas rutas.
- Cinco URLs piloto con HTML renderizado en servidor y eventos publicados de PostgreSQL:
  - `/que-hacer-en-gran-canaria`
  - `/eventos-en-las-palmas-de-gran-canaria`
  - `/que-hacer-en-ingenio`
  - `/eventos-en-telde`
  - `/que-hacer-en-aguimes`
- Sitemap actualizado con las cinco nuevas URLs y la portada.
- Las landing incluyen canonical, title, description, Open Graph, JSON-LD `CollectionPage` y `BreadcrumbList`, y enlaces a la fuente.
- `noindex` automático si hay menos de tres eventos futuros o vigentes del municipio; error HTTP 503 si falla PostgreSQL. No se publican cientos de páginas repetidas.
- Respuesta cacheada en CDN durante 5 minutos para proteger rendimiento y PostgreSQL.
- No se modificaron pagos, panel de administración, contrataciones comerciales ni secretos.

## Antes de fusionar con main
1. Ejecutar `node --test tests/seo-pages.test.mjs`.
2. Revisar HTTP 200 en la preview de Vercel para las cinco nuevas rutas, canonical, robots, encabezados y eventos.
3. Confirmar que home, mapa, favoritos, PWA, /api/catalog y /admin/ siguen funcionando.
4. Comprobar que /anunciate/ sigue fuera de la navegación pública: su protección de URL directa se abordará por separado.
5. Probar en móvil, incluyendo LCP, CLS e INP antes y después de fusionar.
6. Verificar Search Console tras la publicación: indexación, impresiones y sitemaps.
7. Si hay menos de tres registros futuros en alguna localidad, retirarla del sitemap hasta completar la cobertura.

## Fases siguientes
- Dar URL HTML única a cada evento con `Event` JSON-LD válido cuando haya fecha, recinto y datos verificables.
- Actualizar sitemap de eventos a partir del catálogo real, excluir páginas caducadas/pobres y cuidar la estabilidad de URLs.
- Ampliar municipios con suficiente cobertura: Santa Lucía de Tirajana, Santa Brígida, Gáldar, Teror, San Bartolomé de Tirajana y Arucas.
- Crear páginas de intención (hoy, fin de semana, gratis, en familia) solamente cuando puedan aportar contenido útil propio.
- Instrumentar GA4 con consentimiento y eventos de uso, PWA, favoritos, clics a los planes y campañas.
- Abrir el resto de islas cuando exista catálogo real suficiente y verificado en cada una.

## Fuentes de datos
`published_events` y `event_overrides` (mismos criterios de publicación que `api/catalog.js`).
Los datos de organizadores, fecha y fuente se muestran solo si figuran en el catálogo.
