// D'Parranda: SEO landing pages for Gran Canaria (first, deliberately limited rollout).
// Pure rendering helpers; no database writes or dependency on the main SPA.
export const SITE = 'https://dparranda.es';

export const SEO_PAGES = Object.freeze([
  {
    key: 'gran-canaria',
    path: '/que-hacer-en-gran-canaria',
    municipality: null,
    place: 'Gran Canaria',
    title: 'Qué hacer en Gran Canaria | Planes y eventos | D’Parranda',
    heading: 'Qué hacer en Gran Canaria',
    description: 'Descubre eventos, conciertos, cultura, fiestas y planes en Gran Canaria. Consulta próximas actividades por municipio y encuentra qué hacer con D’Parranda.',
    editorial: '¿Tienes un rato libre y no sabes qué hacer? Explora los próximos planes publicados en Gran Canaria: propuestas culturales, musicales, familiares y actividades en distintos municipios. Selecciona una localidad para acercarte a los planes que más te interesan.'
  },
  {
    key: 'las-palmas-de-gran-canaria',
    path: '/eventos-en-las-palmas-de-gran-canaria',
    municipality: 'Las Palmas de Gran Canaria',
    place: 'Las Palmas de Gran Canaria',
    title: 'Eventos en Las Palmas de Gran Canaria | D’Parranda',
    heading: 'Eventos en Las Palmas de Gran Canaria',
    description: 'Consulta la agenda de eventos en Las Palmas de Gran Canaria: conciertos, teatro, exposiciones y planes próximos con enlaces a sus fuentes.',
    editorial: 'La capital reúne propuestas culturales, música, teatro y actividades durante todo el año. Aquí puedes descubrir próximas citas en Las Palmas de Gran Canaria, consultar sus datos y decidir qué plan encaja contigo. Comprueba siempre la información del organizador antes de desplazarte.'
  },
  {
    key: 'ingenio',
    path: '/que-hacer-en-ingenio',
    municipality: 'Ingenio',
    place: 'Ingenio',
    title: 'Qué hacer en Ingenio | Agenda de eventos | D’Parranda',
    heading: 'Qué hacer en Ingenio',
    description: 'Encuentra eventos en Ingenio y Carrizal: actividades culturales, música, fiestas y planes para disfrutar del municipio de Gran Canaria.',
    editorial: 'En Ingenio, Carrizal y su entorno hay planes para diferentes momentos de la semana. Reunimos las próximas actividades publicadas del municipio para que descubras propuestas de cultura, ocio y vida local sin tener que consultar muchas agendas por separado.'
  },
  {
    key: 'telde',
    path: '/eventos-en-telde',
    municipality: 'Telde',
    place: 'Telde',
    title: 'Eventos en Telde | Qué hacer en Telde | D’Parranda',
    heading: 'Eventos en Telde',
    description: 'Descubre qué hacer en Telde: agenda de conciertos, teatro, actividades y planes próximos, con fecha, lugar y acceso a la información oficial.',
    editorial: 'Si buscas un plan en Telde, empieza por la agenda del municipio. Consulta próximas actividades culturales y de ocio, revisa la fecha y el recinto y comparte las que te interesen. Los eventos cambian: te recomendamos verificar los detalles en la fuente enlazada.'
  },
  {
    key: 'aguimes',
    path: '/que-hacer-en-aguimes',
    municipality: 'Agüimes',
    place: 'Agüimes',
    title: 'Qué hacer en Agüimes y Arinaga | D’Parranda',
    heading: 'Qué hacer en Agüimes',
    description: 'Consulta eventos y planes en Agüimes, Cruce de Arinaga y Playa de Arinaga: cultura, fiestas, música y actividades del sureste de Gran Canaria.',
    editorial: '¿Buscas algo que hacer por Agüimes, Cruce de Arinaga o Playa de Arinaga? Esta agenda reúne actividades publicadas en el municipio para descubrir planes cerca de casa, organizar una salida o compartir una propuesta con amigos y familia.'
  }
]);

export const pageForKey = key => SEO_PAGES.find(page => page.key === key) || null;
export const escapeHtml = value => String(value ?? '')
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

export function normalizePlace(value) {
  return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es').replace(/\s+/g, ' ').trim();
}

export function canaryToday(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Atlantic/Canary', year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(date);
  const part = key => parts.find(p => p.type === key)?.value || '';
  return part('year') + '-' + part('month') + '-' + part('day');
}

function isoDay(value) {
  const match = /^(\d{4}-\d{2}-\d{2})/.exec(String(value || ''));
  return match ? match[1] : '';
}
function safeUrl(value) {
  try {
    const url = new URL(String(value || ''));
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : '';
  } catch { return ''; }
}
function dateText(value) {
  const day = isoDay(value);
  if (!day) return 'Fecha por confirmar';
  const date = new Date(day + 'T12:00:00Z');
  const label = new Intl.DateTimeFormat('es-ES', {
    timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric'
  }).format(date);
  const time = /T(\d{2}):(\d{2})/.exec(String(value || ''));
  return label + (time ? ' · ' + time[1] + ':' + time[2] : '');
}
const categoryNames = {
  musica:'Música', cultura:'Cultura', familia:'En familia',
  gastronomia:'Gastronomía', deporte:'Deporte', naturaleza:'Naturaleza',
  ocio:'Ocio', otros:'Otros'
};

export function upcomingEvents(allEvents, page, today = canaryToday()) {
  if (!Array.isArray(allEvents) || !page) return [];
  const target = page.municipality ? normalizePlace(page.municipality) : '';
  return allEvents.filter(event => {
    if (!event || event.id == null || !event.title || !isoDay(event.start)) return false;
    if (event.paid_promotion === true) return false;
    if (target && normalizePlace(event.municipality) !== target) return false;
    const lastDate = isoDay(event.end) || isoDay(event.start);
    return lastDate >= today;
  }).sort((a, b) => {
    // Prefer future sessions; long-running activities that began weeks ago go later.
    const futureA = isoDay(a.start) >= today;
    const futureB = isoDay(b.start) >= today;
    if (futureA !== futureB) return futureA ? -1 : 1;
    const keyA = futureA ? String(a.start) : (isoDay(a.end) || isoDay(a.start));
    const keyB = futureB ? String(b.start) : (isoDay(b.end) || isoDay(b.start));
    return keyA.localeCompare(keyB) || String(a.id).localeCompare(String(b.id));
  });
}

// Keep the same official-image eligibility as the public D'Parranda catalog.
// Never display an unverified external image or a URL from an unknown host.
const OFFICIAL_IMAGE_HOSTS = new Set([
  'ingenio.es','www.ingenio.es','eventos.aguimes.es',
  'actividadesjuventud.laspalmasgc.es','artesescenicasgrancanaria.com',
  'www.artesescenicasgrancanaria.com','www.eventosgrancanaria.com',
  'www.tureservaonline.es','auditorioalfredokraus.es','teatroperezgaldos.es',
  'salainsulardeteatro.com','teatrocuyas.com','eventos.santabrigida.es',
  'lpacultura.com','cdn.prod.website-files.com','tejeda.eu','valleseco.es',
  'santamariadeguia.es','api.sociedadfilarmonicalpgc.com','teror.es',
  'www.galdar.es','www.arucas.org','lpabibliotecas.com','www.maspalomas.com',
  'www.santaluciagc.com','www.telde.es'
]);

export function officialPosterUrl(event) {
  if (!event || event.image_status !== 'official_remote' || !event.image_url) return '';
  try {
    const url = new URL(String(event.image_url));
    return url.protocol === 'https:' && OFFICIAL_IMAGE_HOSTS.has(url.hostname)
      ? url.href : '';
  } catch { return ''; }
}

function eventDateLabel(event, today) {
  const start = isoDay(event.start);
  const end = isoDay(event.end);
  if (end && end > start) {
    if (start < today) return 'En curso · Hasta el ' + dateText(event.end).split(' · ')[0];
    return 'Del ' + dateText(event.start).split(' · ')[0] + ' al ' + dateText(event.end).split(' · ')[0];
  }
  return dateText(event.start);
}

function eventCard(event, today) {
  const title = escapeHtml(event.title);
  const city = escapeHtml(event.municipality);
  const venue = escapeHtml(event.venue || 'Consulta el lugar en la fuente');
  const date = escapeHtml(eventDateLabel(event, today));
  const category = escapeHtml(categoryNames[event.category] || 'Plan');
  const eventLink = '/?evento=' + encodeURIComponent(String(event.id));
  const source = safeUrl(event.source_url);
  const sourceLink = source
    ? '<a class="source" target="_blank" rel="noopener noreferrer" href="' + escapeHtml(source) + '">Fuente del evento</a>'
    : '';
  const photo = officialPosterUrl(event);
  const poster = photo && (/\/plot\/event_/.test(photo) ||
    /https:\/\/(?:eventos\.santabrigida\.es|lpacultura\.com|teror\.es|tejeda\.eu|www\.galdar\.es|www\.arucas\.org|santamariadeguia\.es)\//.test(photo));
  const cover = '<div class="cover-fallback" aria-hidden="true">'
    + '<span class="cover-top">D’PARRANDA · GRAN CANARIA</span>'
    + '<strong class="cover-name">' + title + '</strong>'
    + '<span class="cover-bottom">' + category + ' · ' + city + '</span></div>'
    + (photo ? '<img class="official-cover' + (poster ? ' poster-art' : '') + '" '
      + 'src="' + escapeHtml(photo) + '" data-poster-source="' + escapeHtml(photo) + '" '
      + 'loading="lazy" decoding="async" referrerpolicy="strict-origin-when-cross-origin" '
      + 'alt="' + escapeHtml(event.image_alt || ('Cartel del evento: ' + event.title)) + '">'
      : '');
  return '<article class="event-card"><a class="event-primary" href="' + eventLink + '">'
    + '<div class="cover" data-category="' + escapeHtml(event.category || 'otros') + '">' + cover + '</div>'
    + '<div class="event-content"><span class="category">' + category + '</span>'
    + '<h3>' + title + '</h3><p class="date">' + date + '</p>'
    + '<p class="venue">' + venue + ' · ' + city + '</p>'
    + '<strong class="open">Ver el plan en D’Parranda →</strong></div></a>'
    + (sourceLink ? '<div class="source-line">' + sourceLink + '</div>' : '') + '</article>';
}

export function renderLanding(page, allEvents, opts = {}) {
  const today = opts.today || canaryToday();
  const events = upcomingEvents(allEvents, page, today);
  const limited = events.slice(0, 48);
  const indexable = events.length >= 3;
  const canonical = SITE + page.path;
  const pageLinks = SEO_PAGES.map(item => '<a' + (item.key === page.key ? ' aria-current="page"' : '') +
    ' href="' + escapeHtml(item.path) + '">' + escapeHtml(item.place) + '</a>').join('');
  const schema = JSON.stringify([
    {
      '@context':'https://schema.org', '@type':'CollectionPage', '@id':canonical + '#page',
      name:page.heading, description:page.description, url:canonical, inLanguage:'es-ES',
      isPartOf:{ '@type':'WebSite', name:'D’Parranda', url:SITE }
    },
    {
      '@context':'https://schema.org', '@type':'BreadcrumbList',
      itemListElement: [
        { '@type':'ListItem', position:1, name:'Inicio', item:SITE + '/' },
        { '@type':'ListItem', position:2, name:page.place, item:canonical }
      ]
    }
  ]).replace(/</g, '\\u003c');
  const empty = '<div class="empty"><h2>Próximamente más planes</h2><p>Ahora mismo no hay suficientes actividades próximas verificadas en esta zona. Consulta la portada para descubrir otros planes de Gran Canaria.</p><a href="/">Explorar todos los planes →</a></div>';
  const cards = limited.map(event => eventCard(event, today)).join('');
  const summary = events.length
    ? '<p class="result-count">' + events.length + ' ' + (events.length === 1 ? 'plan publicado' : 'planes publicados') + ' con fecha actual o futura' + (events.length > limited.length ? ' · Mostrando los 48 más próximos' : '') + '</p>'
    : '';
  const html = [
    '<!doctype html><html lang="es"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
    '<title>', escapeHtml(page.title), '</title>',
    '<meta name="description" content="', escapeHtml(page.description), '">',
    '<meta name="robots" content="', indexable ? 'index,follow,max-image-preview:large' : 'noindex,follow', '">',
    '<link rel="canonical" href="', escapeHtml(canonical), '">',
    '<meta property="og:type" content="website"><meta property="og:title" content="', escapeHtml(page.title), '">',
    '<meta property="og:description" content="', escapeHtml(page.description), '">',
    '<meta property="og:url" content="', escapeHtml(canonical), '">',
    '<meta name="theme-color" content="#10364D">',
    '<link rel="icon" href="/favicon.png" type="image/png">',
    '<link rel="manifest" href="/manifest.webmanifest">',
    '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&amp;family=Outfit:wght@400;600;700;800;900&amp;display=swap" media="print" onload="this.media=\'all\'">',
    '<script type="application/ld+json">', schema, '</script>',
    '<link rel="stylesheet" href="/brand/seo-local.css?v=1">',
    '</head><body>',
    '<header class="top"><div class="shell"><a class="logo" href="/" aria-label="D’Parranda, volver al inicio"><img src="/brand/dparranda-logo.svg?v=6" alt="D’Parranda" width="845" height="294"></a><div class="top-aside"><small>UNA ISLA. MIL PLANES.</small><a class="back" href="/">Todos los planes →</a></div></div></header>',
    '<section class="hero shell"><div class="shell"><div class="kicker">D’PARRANDA · GRAN CANARIA</div><h1>', escapeHtml(page.heading), '</h1><p>Conciertos, cultura y experiencias. Encuentra tu próximo plan.</p></div></section>',
    '<main class="shell"><section class="towns-wrap"><p class="towns-title">Explora cerca de ti</p><nav aria-label="Planes por municipio" class="towns">', pageLinks, '</nav></section>',
    '<section class="agenda" id="agenda" aria-labelledby="agenda-title"><div class="agenda-head"><p class="agenda-eyebrow">La isla no para</p><h2 id="agenda-title">Próximos planes</h2>', summary, '</div>',
    '<div class="cards">', cards, '</div>', indexable ? '' : empty, '</section>',
    '<section class="editorial" aria-labelledby="about-local"><h2 id="about-local">Descubre qué hacer en ', escapeHtml(page.place), '</h2><p>', escapeHtml(page.editorial), '</p></section></main>',
    '<footer class="foot"><div class="shell"><strong>D’Parranda</strong> · Descubre qué hacer cuando tienes tiempo libre. ',
    '<a href="/">Volver al buscador, mapa y favoritos</a><p>Fechas y horarios sujetos a cambios. Consulta la fuente de cada evento antes de asistir.</p></div></footer>',
    '<script defer src="/posters/manifest.js"></script><script defer src="/posters/remote-manifest.js"></script>',
    '<script>document.addEventListener("DOMContentLoaded",function(){',
    'document.querySelectorAll("img[data-poster-source]").forEach(function(img){',
    'img.addEventListener("error",function(){img.remove()},{once:true});',
    'if(img.complete&&img.naturalWidth===0){img.remove();return;}',
    'var source=img.getAttribute("data-poster-source");',
    'var record=window.DParrandaPosterThumbs?.[source]||window.DParrandaExtraPosterThumbs?.[source];',
    'if(record&&typeof record==="object"&&/^\\/posters\\/(?:r-)?[a-f0-9]{24}-320\\.webp$/.test(record.thumb)){',
    'img.src=record.thumb;',
    'if(/^\\/posters\\/(?:r-)?[a-f0-9]{24}-480\\.webp$/.test(record.retina))img.srcset=record.thumb+" 320w, "+record.retina+" 480w";',
    'img.sizes="(max-width:620px) 145px, (max-width:860px) 44vw, 370px";',
    '}',
    '});});</script>',
    '</body></html>'
  ].join('');
  return { html, indexable, total: events.length, displayed: limited.length };
}
