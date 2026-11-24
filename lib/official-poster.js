// Strictly scoped same-origin delivery for the two official Mesa y López
// Christmas programmes. The extractor/database keep the publisher image URL.
// This helper does not download, archive or persist any image on Google Drive.
export const ECI_IMAGE_HOST = 'www.centroscomerciales.elcorteingles.es';
export const ECI_IMAGE_PATH = '/centroscomerciales/uploads/events/';
export const ECI_PROGRAMMES = Object.freeze({
  market:Object.freeze({
    source_name:'El Corte Inglés Mesa y López · Mercado de Navidad',
    source_url:'https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/mercado-navideno-las-palmas'
  }),
  shows:Object.freeze({
    source_name:'El Corte Inglés Mesa y López · Espectáculos de Navidad',
    source_url:'https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/una-navidad-llena-de-magia-risas-y-diversion-para-toda-la-familia'
  })
});

export function eciOfficialImageUrl(event, kind) {
  const rule=Object.hasOwn(ECI_PROGRAMMES,kind) ? ECI_PROGRAMMES[kind] : null;
  if (!rule || !event || event.paid_promotion === true ||
      event.image_status !== 'official_remote' ||
      event.source_name !== rule.source_name ||
      event.source_url !== rule.source_url ||
      event.image_origin !== rule.source_url) return '';
  try {
    const u=new URL(event.image_url);
    if (u.protocol !== 'https:' || u.hostname !== ECI_IMAGE_HOST ||
        u.username || u.password || u.port || u.search || u.hash ||
        !u.pathname.startsWith(ECI_IMAGE_PATH) ||
        !/\.(?:jpe?g|png|webp)$/i.test(u.pathname)) return '';
    return u.href;
  } catch { return ''; }
}

export function eciOfficialImageKind(event) {
  return Object.keys(ECI_PROGRAMMES).find(kind=>!!eciOfficialImageUrl(event,kind)) || '';
}

export function browserPosterUrl(event, originalUrl) {
  if (!originalUrl) return '';
  if (!Number.isSafeInteger(event?.id) || event.id < 1) return originalUrl;
  const kind=eciOfficialImageKind(event);
  return kind ? '/api/official-poster?kind='+kind : originalUrl;
}
