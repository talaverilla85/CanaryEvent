// Automatically generated SEO collections for official shopping-centre programmes.
// No per-centre static pages, images copied to Drive, or invented activities.
import {
  SITE, escapeHtml, normalizePlace, canaryToday, christmasRelated,
  upcomingEvents, landingIndexable, renderLanding
} from './seo-pages.js';

const DATE_TIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/;
const OFFICIAL_MALL_SOURCE = /^Centro Comercial .+? · /i;
const OFFICIAL_MESA_SOURCE = /^El Corte Inglés Mesa y López · /i;

function mallSlug(name) {
  if (normalizePlace(name) === 'el corte ingles jose mesa y lopez') return 'mesa-y-lopez';
  if (!/^Centro Comercial /i.test(name)) return '';
  const shortName = name.replace(/^Centro Comercial\s+/i, '').trim();
  const slug = normalizePlace(shortName).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return slug.length >= 3 && slug.length <= 75 ? slug : '';
}

function isoDay(raw) { return String(raw || '').slice(0, 10); }

export function mallEventIdentity(event) {
  if (!event || event.paid_promotion || event.status === 'cancelled') return null;
  if (!Number.isSafeInteger(event.id) || event.id <= 0) return null;
  if (!DATE_TIME.test(String(event.start || ''))) return null;
  if (!/^https:\/\//i.test(String(event.source_url || ''))) return null;
  if (String(event.title || '').trim().length < 5 ||
      String(event.details || '').trim().length < 90) return null;
  const venue = String(event.venue || '').trim();
  const sourceName = String(event.source_name || '').trim();
  const validCentre = OFFICIAL_MALL_SOURCE.test(sourceName) &&
    /^Centro Comercial /i.test(venue);
  const mesa = OFFICIAL_MESA_SOURCE.test(sourceName) &&
    normalizePlace(venue) === 'el corte ingles jose mesa y lopez';
  if (!validCentre && !mesa) return null;
  const slug = mallSlug(venue);
  if (!slug) return null;
  // Require the centre's name to appear in the approved importer attribution.
  if (validCentre) {
    const sourceCentre = sourceName.split(' · ')[0];
    if (normalizePlace(sourceCentre) !== normalizePlace(venue)) return null;
  }
  return {slug, venue, municipality: String(event.municipality || '').trim()};
}

export function mallGroups(allEvents, today = canaryToday()) {
  const groups = new Map();
  for (const event of Array.isArray(allEvents) ? allEvents : []) {
    const identity = mallEventIdentity(event);
    if (!identity) continue;
    if ((isoDay(event.end) || isoDay(event.start)) < today) continue;
    const group = groups.get(identity.slug) || {
      slug: identity.slug, venue: identity.venue,
      municipality: identity.municipality, events: []
    };
    // Never merge two distinct venues or municipalities sharing a slug.
    if (normalizePlace(group.venue) !== normalizePlace(identity.venue) ||
        normalizePlace(group.municipality) !== normalizePlace(identity.municipality)) continue;
    group.events.push(event);
    groups.set(identity.slug, group);
  }
  return [...groups.values()].sort((a,b) => a.slug.localeCompare(b.slug));
}

function yearOfChristmas(today) {
  const year = Number(today.slice(0, 4));
  return Number(today.slice(5, 7)) <= 1 ? year - 1 : year;
}

export function mallPageForSlug(allEvents, slug, today = canaryToday()) {
  if (typeof slug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug) ||
      slug.length > 75) return null;
  const group = mallGroups(allEvents, today).find(item => item.slug === slug);
  if (!group?.events.length) return null;
  const upcoming = group.events.filter(e =>
    (isoDay(e.end) || isoDay(e.start)) >= today);
  const christmasCount = upcoming.filter(christmasRelated).length;
  const christmas = christmasCount >= 1 && christmasCount * 2 >= upcoming.length;
  const season = yearOfChristmas(today);
  const venue = group.venue;
  const place = group.municipality || 'Gran Canaria';
  const heading = christmas
    ? 'Navidad en ' + venue + ' ' + season + '–' + (season + 1)
    : 'Eventos en ' + venue;
  const desc = christmas
    ? 'Consulta el programa de Navidad de ' + venue + ': talleres, espectáculos y otras actividades verificadas con fechas, horarios, imágenes oficiales y fuentes originales en D’Parranda.'
    : 'Próximas actividades en ' + venue + ', ' + place + '. Fechas, horarios, imágenes oficiales cuando estén disponibles y enlaces a los organizadores en D’Parranda.';
  return {
    key:'centro-'+slug, kind:'mall',
    path:'/centros-comerciales/'+slug,
    place:venue, venue, municipality:null,
    title:heading + ' | Programación y horarios | D’Parranda',
    heading, description:desc,
    intro:christmas
      ? 'Talleres, espectáculos y otras actividades navideñas anunciadas por el centro. Consulta fechas y horarios antes de acudir.'
      : 'Descubre las próximas actividades anunciadas por el centro y consulta sus horarios y fuentes oficiales.',
    agendaHeading:christmas ? 'Programa de Navidad en ' + venue : 'Programación de ' + venue,
    editorial:'Agenda de ' + venue + ', en ' + place + '. Las actividades se actualizan a partir de las fuentes oficiales. Cada ficha indica día, horario, recinto y acceso a la programación original; las imágenes pertenecen a sus fuentes y no se archivan en Drive.'
  };
}

export function mallPagesWithContent(allEvents, today=canaryToday()) {
  const pages = mallGroups(allEvents, today).map(group =>
    mallPageForSlug(allEvents, group.slug, today)).filter(Boolean);
  return pages.filter(page => {
    const events = mallGroups(allEvents, today).find(g => g.slug === page.path.split('/').pop())?.events || [];
    return landingIndexable(page, upcomingEvents(events, page, today));
  });
}

export function renderMallPage(slug, allEvents, opts={}) {
  const today=opts.today || canaryToday();
  const page=mallPageForSlug(allEvents, slug, today);
  if (!page) return null;
  const matching=mallGroups(allEvents, today).find(group => group.slug === slug);
  return renderLanding(page, matching.events, {today});
}

export function renderMallSitemap(allEvents, today=canaryToday()) {
  const urls=mallPagesWithContent(allEvents,today).map(page => SITE+page.path);
  return '<?xml version="1.0" encoding="UTF-8"?>\n'
    + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + urls.map(url => '  <url><loc>' + escapeHtml(url) + '</loc></url>').join('\n')
    + '\n</urlset>\n';
}

export function mallNavigationLinks(allEvents, today=canaryToday()) {
  return mallPagesWithContent(allEvents,today).map(page => ({
    href:page.path, title:page.heading
  }));
}
