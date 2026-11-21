import { db } from '../lib/admin-auth.js';
import { pageForKey, renderLanding } from '../lib/seo-pages.js';

// Controlled public SEO routes; the existing app and administration are untouched.
export default async function handler(req, res) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    res.setHeader('Cache-Control', 'no-store');
    return res.status(405).end('Método no permitido');
  }
  const pageKey = typeof req.query?.page === 'string' ? req.query.page : '';
  const page = pageForKey(pageKey);
  if (!page) {
    res.setHeader('X-Robots-Tag', 'noindex');
    res.setHeader('Cache-Control', 'no-store');
    return res.status(404).end('Página no encontrada');
  }
  const sql = db();
  if (!sql) {
    res.setHeader('X-Robots-Tag', 'noindex');
    res.setHeader('Cache-Control', 'no-store');
    return res.status(503).end('Agenda temporalmente no disponible');
  }
  try {
    const rows = await sql`SELECT p.payload,
      o.title_override, o.details_override, o.venue_override,
      o.price_override, o.free_override, o.category_override
      FROM published_events p LEFT JOIN event_overrides o ON o.event_id = p.id
      WHERE p.active AND COALESCE(o.hidden,FALSE)=FALSE
        AND o.canonical_event_id IS NULL
      ORDER BY p.payload->>'start',p.id LIMIT 3500`;
    const events = rows.map(({payload, ...overrides}) => {
      const event = {...payload};
      for (const [source, dest] of [
        ['title_override','title'],['details_override','details'],
        ['venue_override','venue'],['price_override','price'],
        ['category_override','category']
      ]) {
        if (overrides[source] !== null && overrides[source] !== undefined)
          event[dest] = overrides[source];
      }
      if (overrides.free_override !== null && overrides.free_override !== undefined)
        event.free = Number(overrides.free_override);
      return event;
    });
    const rendered = renderLanding(page, events);
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    if (!rendered.indexable) res.setHeader('X-Robots-Tag', 'noindex, follow');
    return res.status(200).end(req.method === 'HEAD' ? '' : rendered.html);
  } catch (error) {
    // Do not expose SQL error details or return an apparently indexable empty page.
    console.error('SEO landing query failed', error?.name || 'Error');
    res.setHeader('X-Robots-Tag', 'noindex');
    res.setHeader('Cache-Control', 'no-store');
    return res.status(503).end('Agenda temporalmente no disponible');
  }
}
