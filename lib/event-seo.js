import { SITE, escapeHtml, officialPosterUrl, canaryToday } from './seo-pages.js';

const LOW_VALUE=/^(?:actividad en |actividad publicada|información básica facilitada|periodo de actividad|consulta la fuente |información del evento|evento publicado |fecha y hora extraídas)/i;
const DATE_TIME=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/;
const DATE=/^\d{4}-\d{2}-\d{2}$/;
const CAT={musica:'Música',cultura:'Cultura',familia:'Familia',gastronomia:'Gastronomía',deporte:'Deporte',naturaleza:'Naturaleza',ocio:'Ocio',otros:'Otros'};
export function parseEventId(raw){
 if(typeof raw!=='string'||!/^-?[1-9]\d{0,15}$/.test(raw))return null;
 const id=Number(raw);return Number.isSafeInteger(id)&&id!==0?id:null;
}
export function eventUrl(event){const id=typeof event==='object'?event?.id:event;return Number.isSafeInteger(id)?SITE+'/evento/'+String(id):null}
const day=value=>String(value||'').slice(0,10);
export function eventExpired(event,today=canaryToday()){
 const final=day(event?.end)||day(event?.start);
 // No date is a quality gap, not proof that an event has expired.
 return DATE.test(final) && final<today;
}
export function eventPageRemoved(event,active=true,today=canaryToday()){
 return !active || eventExpired(event,today);
}
export function eventIndexable(event,active=true,today=canaryToday()){
 const details=String(event?.details||'').trim();
 return !!(active && event && Number.isSafeInteger(event.id) && event.id>0 &&
  !event.paid_promotion && String(event.title||'').trim().length>=5 &&
  String(event.municipality||'').trim() && String(event.venue||'').trim() &&
  event.accuracy==='venue' && DATE_TIME.test(String(event.start||'')) &&
  details.length>=145 && !LOW_VALUE.test(details) &&
  /^https:\/\//i.test(String(event.source_url||'')) && !eventExpired(event,today));
}
function externalUrl(value){
 try{const u=new URL(String(value||''));return u.protocol==='https:'?u.href:''}catch{return ''}
}
function clean(value){return String(value||'').replace(/<[^>]*>/g,'').replace(/\s+/g,' ').trim()}
function isoCanary(value){
 if(!DATE_TIME.test(String(value||'')))return null;
 const fmt=new Intl.DateTimeFormat('en-US',{timeZone:'Atlantic/Canary',timeZoneName:'shortOffset'});
 const guessed=new Date(value.slice(0,16)+':00Z');
 const zone=fmt.formatToParts(guessed).find(p=>p.type==='timeZoneName')?.value||'GMT';
 const m=/GMT([+-])(\d{1,2})(?::(\d{2}))?/.exec(zone);
 const offset=m?m[1]+m[2].padStart(2,'0')+':'+(m[3]||'00'):'+00:00';
 return (value.length===16?value+':00':value)+offset;
}
function humanDate(value){
 const d=day(value);
 if(!DATE.test(d))return 'Fecha por confirmar';
 const label=new Intl.DateTimeFormat('es-ES',{timeZone:'UTC',weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(new Date(d+'T12:00:00Z'));
 const t=/T(\d{2}):(\d{2})/.exec(String(value));
 return label+(t?' · '+t[1]+':'+t[2]+' h':' · Horario por confirmar');
}
export function renderEventPage(event,{active=true,today=canaryToday()}={}){
 const indexable=eventIndexable(event,active,today);
 const expired=eventExpired(event,today);
 const available=active&&!expired;
 const url=eventUrl(event);if(!url)throw Error('Invalid event ID');
 const title=clean(event.title)||'Evento';
 const municipality=clean(event.municipality)||'Gran Canaria';
 const venue=clean(event.venue)||'Lugar por confirmar';
 const details=clean(event.details);
 const category=CAT[event.category]||'Planes';
 const source=externalUrl(event.source_url);
 const image=officialPosterUrl(event);
 const excerpt=(details.length>30?details:title+' en '+municipality+'. Consulta la fecha y los detalles del evento en D’Parranda.').slice(0,160);
 const status=!active?'Ya no figura en la agenda actual':expired?'Este evento ya ha terminado':'Próximo plan en Gran Canaria';
 const jsonld=indexable?JSON.stringify({
  '@context':'https://schema.org','@type':'Event','@id':url+'#event',
  name:title,url,description:details,startDate:isoCanary(event.start),
  eventStatus:'https://schema.org/EventScheduled',
  eventAttendanceMode:'https://schema.org/OfflineEventAttendanceMode',
  location:{'@type':'Place',name:venue,address:{'@type':'PostalAddress',addressLocality:municipality,addressRegion:'Las Palmas',addressCountry:'ES'}},
  ...(image?{image:[image]}:{})
 }).replace(/</g,'\\u003c').replace(/&/g,'\\u0026'):null;
 const cover='<div class="event-poster"><div class="cover-fallback" aria-hidden="true">'
  +'<span class="cover-top">D’PARRANDA · GRAN CANARIA</span><strong class="cover-name">'+escapeHtml(title)+'</strong><span class="cover-bottom">'+escapeHtml(category)+' · '+escapeHtml(municipality)+'</span></div>'
  +(image?'<img src="'+escapeHtml(image)+'" data-poster-source="'+escapeHtml(image)+'" alt="'+escapeHtml(event.image_alt||('Cartel del evento: '+title))+'" loading="lazy" decoding="async" referrerpolicy="strict-origin-when-cross-origin">':'')+'</div>';
 const html=[
  '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
  '<title>',escapeHtml(title+' en '+municipality+' | D’Parranda'),'</title>',
  '<meta name="description" content="',escapeHtml(excerpt),'">',
  '<meta name="robots" content="',indexable?'index,follow,max-image-preview:large':'noindex,follow','">',
  '<link rel="canonical" href="',escapeHtml(url),'">',
  '<meta property="og:type" content="website"><meta property="og:title" content="',escapeHtml(title),'">',
  '<meta property="og:description" content="',escapeHtml(excerpt),'">',
  '<meta property="og:url" content="',escapeHtml(url),'">',
  ...(image?['<meta property="og:image" content="',escapeHtml(image),'">']:[]),
  '<meta name="theme-color" content="#10364D">',
  '<link rel="icon" href="/favicon.png" type="image/png"><link rel="manifest" href="/manifest.webmanifest">',
  '<link rel="stylesheet" href="/brand/seo-local.css?v=1"><link rel="stylesheet" href="/brand/seo-event.css?v=1">',
  ...(jsonld?['<script type="application/ld+json">',jsonld,'</script>']:[]),
  '</head><body>',
  '<header class="top"><div class="shell"><a class="logo" href="/" aria-label="D’Parranda - inicio"><img src="/brand/dparranda-logo.svg?v=6" width="845" height="294" alt="D’Parranda"></a><div class="top-aside"><small>UNA ISLA. MIL PLANES.</small><a class="back" href="/">Todos los planes →</a></div></div></header>',
  '<main class="shell"><section class="hero event-hero"><div class="shell"><div class="kicker">',escapeHtml(status.toUpperCase()),'</div><h1>',escapeHtml(title),'</h1><p>',escapeHtml(category),' · ',escapeHtml(municipality),'</p></div></section>',
  '<section class="event-layout">',cover,'<div class="event-info-panel"><span class="event-label">CUÁNDO</span><p class="event-fact">',escapeHtml(humanDate(event.start)),'</p>',
  '<span class="event-label">DÓNDE</span><p class="event-fact">',escapeHtml(venue),'<small> · ',escapeHtml(municipality),'</small></p>',
  ...(available?[]:['<p class="event-ended">Este evento no está entre los planes próximos. Consulta nuestra agenda para descubrir otros.</p>']),
  '<div class="event-actions"><a class="event-main-link" href="',available?('/?evento='+encodeURIComponent(String(event.id))):'/que-hacer-en-gran-canaria','">',available?'Abrir en D’Parranda':'Descubrir próximos planes','</a>',
  ...(source?['<a class="event-source-link" href="',escapeHtml(source),'" target="_blank" rel="noopener noreferrer">Consultar la fuente ↗</a>']:[]),
  '</div><p class="event-hint">Desde la aplicación puedes guardar planes y configurar recordatorios.</p></div></section>',
  '<section class="event-description"><h2>Sobre este plan</h2><p>',escapeHtml(details||'Información pendiente de ampliación. Consulta la fuente de la actividad para confirmar los detalles.'),'</p>',
  '<p class="event-credit">Fuente: ',escapeHtml(event.source_name||'Información del organizador'),'</p>',
  '</section>',
  '<section class="event-more"><h2>¿Buscas otro plan?</h2><p>Descubre actividades, conciertos y experiencias en Gran Canaria.</p><a href="/que-hacer-en-gran-canaria">Ver más planes de Gran Canaria →</a></section></main>',
  '<footer class="foot"><div class="shell"><strong>D’Parranda</strong> · Disfruta de tus islas. <a href="/">Todos los planes</a></div></footer>',
  '<script defer src="/posters/manifest.js"></script><script defer src="/posters/remote-manifest.js"></script>',
  '<script>document.addEventListener("DOMContentLoaded",function(){var img=document.querySelector("img[data-poster-source]");if(!img)return;img.addEventListener("error",function(){img.remove()},{once:true});if(img.complete&&img.naturalWidth===0){img.remove();return;}var s=img.getAttribute("data-poster-source");var r=window.DParrandaPosterThumbs?.[s]||window.DParrandaExtraPosterThumbs?.[s];if(r&&typeof r==="object"&&/^\\/posters\\/(?:r-)?[a-f0-9]{24}-480\\.webp$/.test(r.retina))img.src=r.retina;});</script>',
  '</body></html>'
 ].join('');
 return {html,indexable,expired};
}

export function renderEventSitemap(events,today=canaryToday()){
 const urls=[...new Set(events.filter(e=>eventIndexable(e,true,today)).map(eventUrl))].sort();
 return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
  +urls.map(u=>'  <url><loc>'+escapeHtml(u)+'</loc></url>').join('\n')+'\n</urlset>\n';
}
