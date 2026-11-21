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
  }).sort((a, b) => String(a.start).localeCompare(String(b.start)) || String(a.id).localeCompare(String(b.id)));
}

function eventCard(event) {
  const title = escapeHtml(event.title);
  const city = escapeHtml(event.municipality);
  const venue = escapeHtml(event.venue || 'Consulta el lugar en la fuente');
  const date = escapeHtml(dateText(event.start));
  const category = escapeHtml(categoryNames[event.category] || 'Plan');
  const eventLink = '/?evento=' + encodeURIComponent(String(event.id));
  const source = safeUrl(event.source_url);
  const sourceLink = source
    ? '<a class="source" target="_blank" rel="noopener noreferrer" href="' + escapeHtml(source) + '">Fuente del evento</a>'
    : '';
  const photo = safeUrl(event.image_url);
  const cover = event.image_status === 'verified' && photo
    ? '<img loading="lazy" decoding="async" src="' + escapeHtml(photo) + '" alt="' + escapeHtml(event.image_alt || ('Cartel: ' + event.title)) + '">'
    : '<span class="card-symbol" aria-hidden="true">✳</span>';
  return '<article class="event-card"><a class="event-primary" href="' + eventLink + '">'
    + '<div class="cover">' + cover + '</div>'
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
  const cards = limited.map(eventCard).join('');
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
    '<meta name="theme-color" content="#183831">',
    '<link rel="icon" href="/favicon.png" type="image/png">',
    '<link rel="manifest" href="/manifest.webmanifest">',
    '<script type="application/ld+json">', schema, '</script>',
    '<style>',
    '*{box-sizing:border-box}body{margin:0;background:#f7f8f4;color:#192723;font-family:system-ui,-apple-system,Segoe UI,sans-serif;line-height:1.55}a{color:inherit;text-decoration:none}a:focus-visible{outline:3px solid #3e9862;outline-offset:3px}.shell{width:min(1140px,calc(100% - 32px));margin:auto}.top{background:#fff;border-bottom:1px solid #e2e8e1}.top .shell{padding:18px 0;display:flex;justify-content:space-between;align-items:center;gap:15px}.logo{font-size:23px;font-weight:900;letter-spacing:-1px;color:#183831}.back{font-size:14px;font-weight:700;color:#386f4c}.hero{background:linear-gradient(120deg,#183831,#214c3b);color:#fff;padding:46px 0 48px}.kicker{letter-spacing:2px;text-transform:uppercase;color:#c6f1b8;font-size:12px;font-weight:800}.hero h1{font-size:clamp(32px,5vw,54px);line-height:1.1;letter-spacing:-1.5px;margin:12px 0 18px}.hero p{max-width:780px;color:#dbeadf;margin:0;font-size:16px}.intro{padding:26px 0 10px;max-width:860px;color:#475e50;font-size:16px}.towns{display:flex;gap:9px;flex-wrap:wrap;margin:20px 0 30px}.towns a{border:1px solid #d7e3d7;border-radius:100px;padding:8px 14px;background:white;font-weight:700;font-size:13px}.towns a[aria-current="page"]{background:#183831;border-color:#183831;color:white}h2{font-size:clamp(25px,3.5vw,33px);letter-spacing:-.6px;margin:0 0 6px}.result-count{color:#687b6d;font-size:14px;margin:0 0 22px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;padding-bottom:45px}.event-card{background:#fff;border:1px solid #e2e8e1;border-radius:20px;overflow:hidden;min-width:0;display:flex;flex-direction:column}.event-primary{display:block;flex:1}.cover{height:160px;background:radial-gradient(circle at 75% 20%,#b4e6a8,#245442 75%);display:grid;place-items:center;overflow:hidden}.cover img{width:100%;height:100%;object-fit:cover}.card-symbol{color:#c6f1b8;font-size:74px}.event-content{padding:17px}.category{color:#387b52;font-size:11px;text-transform:uppercase;letter-spacing:1px;font-weight:800}.event-card h3{font-size:18px;line-height:1.3;margin:9px 0 12px}.date{font-weight:800;font-size:13px;margin:0 0 6px}.venue{color:#66766b;font-size:13px;margin:0 0 14px}.open{color:#245e42;font-size:13px}.source-line{border-top:1px solid #ecf0e9;padding:9px 17px}.source{color:#416c50;font-size:12px;text-decoration:underline}.empty{background:#fff;padding:35px;border-radius:20px;margin-bottom:40px}.empty p{color:#52685b}.empty a{font-weight:800;color:#2f704e}.foot{padding:25px 0 45px;border-top:1px solid #e0e8de;font-size:13px;color:#66766b}.foot a{text-decoration:underline}.foot strong{color:#183831}@media(max-width:820px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:540px){.cards{grid-template-columns:1fr}.hero{padding:30px 0 36px}.cover{height:175px}.top .shell{padding:14px 0}.logo{font-size:21px}}',
    '</style></head><body>',
    '<header class="top"><div class="shell"><a class="logo" href="/" aria-label="D’Parranda - inicio">✳ D’Parranda</a><a class="back" href="/">Todos los planes →</a></div></header>',
    '<section class="hero"><div class="shell"><div class="kicker">D’Parranda · Gran Canaria</div><h1>', escapeHtml(page.heading), '</h1><p>', escapeHtml(page.description), '</p></div></section>',
    '<main class="shell"><p class="intro">', escapeHtml(page.editorial), '</p>',
    '<nav aria-label="Planes por municipio" class="towns">', pageLinks, '</nav>',
    '<section id="agenda" aria-labelledby="agenda-title"><h2 id="agenda-title">Próximos planes</h2>', summary,
    '<div class="cards">', cards, '</div>', indexable ? '' : empty, '</section></main>',
    '<footer class="foot"><div class="shell"><strong>D’Parranda</strong> · Descubre qué hacer cuando tienes tiempo libre. ',
    '<a href="/">Volver al buscador, mapa y favoritos</a><p>Fechas y horarios sujetos a cambios. Consulta la fuente de cada evento antes de asistir.</p></div></footer>',
    '</body></html>'
  ].join('');
  return { html, indexable, total: events.length, displayed: limited.length };
}
