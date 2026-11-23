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
  },
  {
    key: 'fin-de-semana',
    kind: 'weekend',
    path: '/que-hacer-este-fin-de-semana-gran-canaria',
    municipality: null,
    place: 'Este fin de semana',
    title: 'Qué hacer este fin de semana en Gran Canaria | D’Parranda',
    heading: 'Qué hacer este fin de semana en Gran Canaria',
    description: 'Planes y eventos para este fin de semana en Gran Canaria: conciertos, cultura, actividades y propuestas con fecha concreta y enlace al organizador.',
    editorial: '¿Tienes libre el viernes, sábado o domingo? Reunimos los planes con sesión fechada para el fin de semana correspondiente en Gran Canaria. Los programas de varias semanas sin sesiones confirmadas quedan fuera de esta selección para no inducir a error.'
  },
  {
    key: 'hoy',
    kind: 'today',
    path: '/que-hacer-hoy-gran-canaria',
    municipality: null,
    place: 'Hoy',
    title: 'Qué hacer hoy en Gran Canaria | Planes de hoy | D’Parranda',
    heading: 'Qué hacer hoy en Gran Canaria',
    description: 'Descubre planes, conciertos, actividades y eventos con fecha confirmada para hoy en Gran Canaria. Agenda del día actualizada automáticamente.',
    editorial: '¿Qué puedes hacer hoy en Gran Canaria? Esta página muestra las actividades cuya sesión comienza hoy, según la fecha de Canarias. No presupone que un curso o exposición de varias semanas se celebra diariamente: consulta siempre el horario oficial.'
  },
  {
    key: 'con-ninos',
    kind: 'kids',
    path: '/que-hacer-con-ninos-gran-canaria',
    municipality: null,
    place: 'Con niños',
    title: 'Qué hacer con niños en Gran Canaria | Planes en familia | D’Parranda',
    heading: 'Qué hacer con niños en Gran Canaria',
    description: 'Ideas para salir con niños en Gran Canaria: teatro familiar, actividades infantiles, musicales y planes en familia anunciados por sus organizadores.',
    editorial: 'Descubre propuestas anunciadas expresamente como infantiles o familiares: teatro, musicales, actividades y experiencias en Gran Canaria. No basta con que una actividad mencione la palabra familia: revisa la edad recomendada y las condiciones con cada organizador antes de acudir.'
  },
  {
    key: 'navidad',
    kind: 'christmas',
    path: '/navidad-gran-canaria',
    municipality: null,
    place: 'Navidad',
    title: 'Navidad en Gran Canaria | Papá Noel, Reyes Magos y planes | D’Parranda',
    heading: 'Navidad en Gran Canaria: actividades y eventos',
    description: 'Descubre la agenda de Navidad en Gran Canaria: encendidos, talleres, mercadillos, conciertos, Papá Noel, Reyes Magos y planes familiares por municipios.',
    editorial: 'La Navidad se vive en toda Gran Canaria. Encuentra talleres infantiles, encendidos, mercados, espectáculos, visitas de Papá Noel y los Reyes Magos anunciados por ayuntamientos, recintos y centros comerciales. Incluimos únicamente actividades con fecha publicada y enlazamos las fuentes. Comprueba horarios, reserva y posibles cambios antes de salir.'
  },
  {
    key: 'gratis',
    kind: 'free',
    path: '/planes-gratis-gran-canaria',
    municipality: null,
    place: 'Gratis',
    title: 'Planes gratis en Gran Canaria | Eventos gratuitos | D’Parranda',
    heading: 'Planes gratis en Gran Canaria',
    description: 'Encuentra eventos y actividades gratis en Gran Canaria. Selección de planes que figuran expresamente como gratuitos en las fuentes consultadas.',
    editorial: 'Salir y disfrutar no siempre requiere gastar dinero. Esta selección incluye únicamente eventos señalados expresamente como gratuitos, no aquellos sin precio publicado. Algunas actividades pueden necesitar reserva previa o tener plazas limitadas: comprueba los requisitos en la fuente oficial.'
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

const FAMILY_FRIENDLY = /\b(?:teatro familiar|musical familiar|espect[aá]culo familiar|actividades? familiares?|programa familiar|senderos? en familia|rutas? en familia|en familia|para toda la familia|para niños|para niñas|para peques|público familiar|público infantil|infantiles?|cuentacuentos|para todas las edades|para todos los públicos)\b/i;
const CHRISTMAS_TERMS = /(?:navidad|navideñ[oa]s?|pap[aá] noel|santa claus|reyes magos|cabalgata de reyes|belenes? navideñ[oa]s?|bel[eé]n viviente|villancicos|nochebuena|nochevieja|rosc[oó]n de reyes|encendido (?:de )?(?:luces|navideñ[oa])|alumbrado navideñ[oa]|cascanueces|tren de renos|taller de renos|taller de elfo|taller el grinch|mercadillo? navideñ[oa])/i;
export function christmasRelated(event) {
  return CHRISTMAS_TERMS.test(String(event?.title||'')+' '+String(event?.details||''));
}
const GENERIC_DESCRIPTION = /^(?:actividad en |actividad publicada|información básica facilitada|periodo de actividad|consulta la fuente |información del evento|evento publicado |fecha y hora extraídas)/i;
const isoOffset = (iso, days) => {
  const stamp = new Date(iso + 'T12:00:00Z');
  if (Number.isNaN(stamp.getTime())) return '';
  stamp.setUTCDate(stamp.getUTCDate() + days);
  return stamp.toISOString().slice(0, 10);
};
const longDay = iso => new Intl.DateTimeFormat('es-ES', {
  timeZone:'UTC', weekday:'long', day:'numeric', month:'long', year:'numeric'
}).format(new Date(iso + 'T12:00:00Z'));
export function intentPeriod(page, today=canaryToday()) {
  if (page?.kind === 'today') return {start:today,end:today,
    label:'Planes para hoy: ' + longDay(today)};
  if (page?.kind === 'weekend') {
    const dow = new Date(today + 'T12:00:00Z').getUTCDay();
    const fridayShift = dow === 0 ? -2 : 5 - dow;
    const fri = isoOffset(today, fridayShift);
    const sun = isoOffset(fri, 2);
    return {start:fri,end:sun,label:'Del ' + longDay(fri) + ' al ' + longDay(sun)};
  }
  return null;
}
export function familyFriendly(event) {
  return FAMILY_FRIENDLY.test(String(event?.title||'') + ' ' + String(event?.details||''));
}
export function landingIndexable(page, events) {
  if (!page?.kind) return events.length >= 3;
  const useful = events.filter(e => Number.isSafeInteger(e.id) && e.id>0 &&
    String(e.title||'').trim().length>=5 &&
    String(e.venue||'').trim().length>=5 &&
    /^https:\/\//i.test(String(e.source_url||'')) &&
    String(e.details||'').trim().length>=90 &&
    !GENERIC_DESCRIPTION.test(String(e.details||'').trim()));
  return new Set(useful.map(e => normalizePlace(e.title))).size >= 3;
}

export function upcomingEvents(allEvents, page, today = canaryToday()) {
  if (!Array.isArray(allEvents) || !page) return [];
  const target = page.municipality ? normalizePlace(page.municipality) : '';
  const intent = intentPeriod(page, today);
  return allEvents.filter(event => {
    if (!event || event.id == null || !event.title || !isoDay(event.start)) return false;
    if (event.paid_promotion === true) return false;
    if (target && normalizePlace(event.municipality) !== target) return false;
    const lastDate = isoDay(event.end) || isoDay(event.start);
    if (lastDate < today) return false;
    // Time-based SEO requires an actual session start in the selected window.
    // No assumption that a month-long listing runs on every day in the range.
    if (intent && (isoDay(event.start) < today || isoDay(event.start) < intent.start ||
      isoDay(event.start) > intent.end)) return false;
    if (page.kind === 'kids' && !familyFriendly(event)) return false;
    if (page.kind === 'christmas' && !christmasRelated(event)) return false;
    if (page.kind === 'free' && event.free !== 1 && event.free !== true) return false;
    if (page.kind && (!Number.isSafeInteger(event.id) || event.id <= 0)) return false;
    return true;
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
  'santamariadeguia.es','www.vegadesanmateo.es','vegadesanmateo.es',
  'api.sociedadfilarmonicalpgc.com','teror.es',
  'www.galdar.es','www.arucas.org','lpabibliotecas.com','www.maspalomas.com',
  'www.santaluciagc.com','www.telde.es',
  'cclasarenas.com','www.centroscomerciales.elcorteingles.es'
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
  // Some official programmes advertise two *separate* sessions on one day.
  // Show both sessions on the card; never imply an uninterrupted 11–20 event.
  const sessions = /Horario anunciado:\s*((?:\d{2}:\d{2}[–-]\d{2}:\d{2})(?:,\s*\d{2}:\d{2}[–-]\d{2}:\d{2})+)/.exec(
    String(event.details || ''));
  if (sessions) return dateText(event.start).split(' · ')[0] +
    ' · Dos sesiones: ' + sessions[1].replace(/,\s*/g, ' y ');
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
  const eventLink = '/evento/' + encodeURIComponent(String(event.id));
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
    + '<strong class="open">Ver detalles del evento →</strong></div></a>'
    + (sourceLink ? '<div class="source-line">' + sourceLink + '</div>' : '') + '</article>';
}

export function renderIntentSitemap(allEvents, today=canaryToday()) {
  const urls = SEO_PAGES.filter(page => page.kind &&
    landingIndexable(page, upcomingEvents(allEvents, page, today)))
    .map(page => SITE + page.path);
  return '<?xml version="1.0" encoding="UTF-8"?>\n'
    + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + urls.map(url => '  <url><loc>' + escapeHtml(url) + '</loc></url>').join('\n')
    + '\n</urlset>\n';
}

function christmasSponsor(ad) {
  // Editorial events and paid placements must never be interchangeable.
  if (!ad || ad.id !== 'arimar-fundador' || ad.enabled !== true) return '';
  let link;
  try {
    link = new URL(String(ad.button_url || ''));
    if (link.protocol !== 'https:') return '';
    link.searchParams.set('utm_source', 'dparranda');
    link.searchParams.set('utm_medium', 'banner');
    link.searchParams.set('utm_campaign', 'arimar');
    link.searchParams.set('utm_content', 'navidad');
  } catch { return ''; }
  const image = /^\/sponsors\/[a-z0-9._/-]+\.(?:webp|png|jpe?g)$/i.test(String(ad.image || ''))
    ? '<img src="' + escapeHtml(ad.image) + '" loading="lazy" decoding="async" alt="' + escapeHtml(ad.image_alt || 'Imagen de AriMar') + '">'
    : '';
  return '<aside class="christmas-sponsored" aria-label="Publicidad de AriMar">' +
    '<span class="christmas-sponsored-label">ESPACIO PATROCINADO · PUBLICIDAD</span>' +
    '<a href="' + escapeHtml(link.href) + '" data-sponsored-click="arimar-fundador" target="_blank" rel="sponsored noopener noreferrer">' +
    '<span class="christmas-sponsored-image">' + image + '</span>' +
    '<span class="christmas-sponsored-copy"><strong>' + escapeHtml(ad.headline || 'AriMar') + '</strong>' +
    '<small>' + escapeHtml(ad.description || '') + '</small>' +
    '<span class="christmas-sponsored-cta">' + escapeHtml(ad.button_text || 'Ver más') + '</span></span></a></aside>';
}

export function renderLanding(page, allEvents, opts = {}) {
  const today = opts.today || canaryToday();
  const events = upcomingEvents(allEvents, page, today);
  const maxCards = page.kind === 'christmas' ? 120 : 48;
  const limited = events.slice(0, maxCards);
  const indexable = landingIndexable(page, events);
  const period = intentPeriod(page, today);
  const heroIntro = period ? period.label : 'Conciertos, cultura y experiencias. Encuentra tu próximo plan.';
  const agendaHeading = ({weekend:'Planes de este fin de semana',today:'Planes para hoy',
    kids:'Próximos planes para disfrutar en familia',free:'Próximos planes gratuitos',
    christmas:'Próximas actividades de Navidad en Gran Canaria'})[page.kind] || 'Próximos planes';
  const canonical = SITE + page.path;
  const year = today.slice(5,7) === '01' ? Number(today.slice(0,4))-1 : Number(today.slice(0,4));
  const pageTitle = page.kind === 'christmas'
    ? 'Navidad en Gran Canaria ' + year + ' | Papá Noel, Reyes Magos y planes | D’Parranda'
    : page.title;
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
  const empty = '<div class="empty"><h2>Próximamente más planes</h2><p>Ahora mismo no hay suficientes actividades confirmadas para esta selección. Consulta la portada para descubrir otros planes de Gran Canaria.</p><a href="/">Explorar todos los planes →</a></div>';
  const sponsor = page.kind === 'christmas' ? christmasSponsor(opts.sponsor) : '';
  const cards = limited.map((event,i) => (i===3 ? sponsor : '') + eventCard(event, today)).join('') +
    (limited.length<4 ? sponsor : '');
  const countContext = page.kind === 'today' ? ' con fecha de hoy' :
    page.kind === 'weekend' ? ' con sesión para este fin de semana' :
    page.kind === 'kids' ? ' identificados como familiares o infantiles' :
    page.kind === 'free' ? ' confirmados como gratuitos' :
    page.kind === 'christmas' ? ' relacionados con Navidad' : ' con fecha actual o futura';
  const summary = events.length
    ? '<p class="result-count">' + events.length + ' ' + (events.length === 1 ? 'plan publicado' : 'planes publicados') + countContext + (events.length > limited.length ? ' · Mostrando los ' + limited.length + ' más próximos' : '') + '</p>'
    : '';
  const html = [
    '<!doctype html><html lang="es"><head><meta charset="utf-8">',
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
    '<title>', escapeHtml(pageTitle), '</title>',
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
    '<section class="hero shell"><div class="shell"><div class="kicker">D’PARRANDA · GRAN CANARIA</div><h1>', escapeHtml(page.heading), '</h1><p>', escapeHtml(heroIntro), '</p></div></section>',
    '<main class="shell"><section class="towns-wrap"><p class="towns-title">Explora otros planes</p><nav aria-label="Explorar planes por municipio, fecha o tipo" class="towns">', pageLinks, '</nav></section>',
    '<section class="agenda" id="agenda" aria-labelledby="agenda-title"><div class="agenda-head"><p class="agenda-eyebrow">La isla no para</p><h2 id="agenda-title">', escapeHtml(agendaHeading), '</h2>', summary, '</div>',
    '<div class="cards">', cards, '</div>', page.kind ? (events.length ? '' : empty) : (indexable ? '' : empty), '</section>',
    '<section class="editorial" aria-labelledby="about-local"><h2 id="about-local">', escapeHtml(page.kind ? page.heading : 'Descubre qué hacer en ' + page.place), '</h2><p>', escapeHtml(page.editorial), '</p></section></main>',
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
    ...(sponsor ? ['<script>document.querySelectorAll("[data-sponsored-click]").forEach(function(el){el.addEventListener("click",function(){var body=JSON.stringify({id:"arimar-fundador"});try{if(navigator.sendBeacon&&navigator.sendBeacon("/api/ads?op=click",new Blob([body],{type:"application/json"})))return;}catch(e){}fetch("/api/ads?op=click",{method:"POST",headers:{"Content-Type":"application/json"},body:body,keepalive:true,credentials:"same-origin"}).catch(function(){});});});</script>'] : []),
    '</body></html>'
  ].join('');
  return { html, indexable, total: events.length, displayed: limited.length };
}
