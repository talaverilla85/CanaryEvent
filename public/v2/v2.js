/* DParranda 2.0 – isolated client-side presentation using the existing public catalog. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const categoryNames = {
    musica:'Música', cultura:'Cultura', familia:'Familia', gastronomia:'Gastronomía',
    deporte:'Deporte', naturaleza:'Naturaleza', ocio:'Ocio', otros:'Otros'
  };
  const categorySymbols = {
    musica:'♫', cultura:'✦', familia:'☀', gastronomia:'✳', deporte:'↗',
    naturaleza:'❋', ocio:'✴', otros:'✧'
  };
  const state = {
    events: [], ads: [], view: 'home', period: 'all', category: 'all',
    query: '', coords: null, heroIndex: 0, featured: [], visible: 16,
    saved: new Set(), source: 'static'
  };
  try {
    const saved = JSON.parse(localStorage.getItem('dparranda-v2-saved') || '[]');
    if (Array.isArray(saved)) state.saved = new Set(saved.map(String));
  } catch { /* private browsing: continue without saved favorites */ }
  const html = (value) => String(value ?? '').replace(/[&<>"']/g, (char) =>
    ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[char]);
  const day = (value) => String(value || '').slice(0,10);
  const canaryToday = () => {
    const pieces = new Intl.DateTimeFormat('en-GB',{
      timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'
    }).formatToParts(new Date());
    const obj = Object.fromEntries(pieces.map((piece) => [piece.type,piece.value]));
    return obj.year + '-' + obj.month + '-' + obj.day;
  };
  const today = canaryToday();
  const isoOffset = (iso,offset) => {
    const d = new Date(day(iso) + 'T12:00:00Z');
    d.setUTCDate(d.getUTCDate() + offset);
    return d.toISOString().slice(0,10);
  };
  const getWeekend = () => {
    const d = new Date(today + 'T12:00:00Z');
    const weekday = d.getUTCDay();
    const daysUntilFriday = (5 - weekday + 7) % 7;
    return [isoOffset(today,daysUntilFriday), isoOffset(today,daysUntilFriday+2)];
  };
  const weekend = getWeekend();
  const eventDate = (e) => {
    const s = day(e.start);
    if (s && s < today && e.end && day(e.end) >= today) return today;
    return s;
  };
  const active = (e) => {
    const s = day(e.start);
    if (!s) return false;
    return (e.end && day(e.end) >= today) || s >= today;
  };
  const cap = (v) => String(v || '').replace(/\s+/g,' ').trim();
  const shortDate = (iso) => {
    const d = day(iso);
    if (!d) return 'Fecha por confirmar';
    const date = new Date(d + 'T12:00:00Z');
    return new Intl.DateTimeFormat('es-ES',{day:'numeric',month:'short',timeZone:'UTC'}).format(date);
  };
  const dateBadge = (e) => {
    if (day(e.start) <= today && e.end && day(e.end) > today) return 'Hasta ' + shortDate(e.end);
    const d = day(e.start);
    const time = String(e.start || '').match(/T(\d\d):(\d\d)/);
    return (d===today ? 'Hoy' : d===isoOffset(today,1) ? 'Mañana' : shortDate(d)) + (time ? ' · ' + time[1]+':'+time[2] : '');
  };
  const moneyLabel = (e) => e.free===1 || e.free===true || /gratis|gratuit/i.test(e.price||'') ? 'Gratis' : (cap(e.price) || 'Consultar condiciones');
  const safeUrl = (value) => {
    try {
      const url = new URL(String(value || ''), location.origin);
      return url.protocol==='https:' || (url.protocol==='http:' && url.origin===location.origin) ? url.href : '';
    } catch { return ''; }
  };
  const poster = (e, scale='thumb') => {
    const url = String(e.image_url || '');
    if (!url) return '';
    const thumbs = window.DParrandaPosterThumbs || {};
    const mapped = thumbs[url];
    return safeUrl((mapped && (mapped[scale] || mapped.thumb)) || url);
  };
  const isPosterArt = (e) => {
    const u = String(e.image_url||'').toLowerCase();
    return /cartel|poster|programa|afiche/.test(String(e.image_alt||'')+' '+u) ? 'poster-art' : '';
  };
  const eventImg = (e,cls,scale='thumb') => {
    const src = poster(e,scale);
    if (!src) return '';
    return '<img class="'+cls+' '+isPosterArt(e)+'" loading="lazy" decoding="async" src="'+html(src)+'" alt="'+html(e.image_alt || e.title || 'Cartel oficial')+'">';
  };
  const normalize = (text) => String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const title = (e) => cap(e.title) || 'Evento sin título';
  const contains = (e,q) => normalize([e.title,e.venue,e.municipality,e.category,e.details].join(' ')).includes(q);
  const distance = (e) => {
    if (!state.coords || !Number.isFinite(Number(e.lat)) || !Number.isFinite(Number(e.lng))) return null;
    const rad = Math.PI / 180;
    const a = Math.sin((Number(e.lat)-state.coords.lat)*rad/2)**2 +
      Math.cos(state.coords.lat*rad)*Math.cos(Number(e.lat)*rad) *
      Math.sin((Number(e.lng)-state.coords.lng)*rad/2)**2;
    return 6371*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));
  };
  const inWeekend = (e) => {
    const start=day(e.start), end=day(e.end)||start;
    return start<=weekend[1] && end>=weekend[0];
  };
  const isToday = (e) => day(e.start)<=today && (day(e.end)||day(e.start))>=today;
  const filterPeriod = (e,period) => {
    if (period==='today') return isToday(e);
    if (period==='weekend') return inWeekend(e);
    if (period==='free') return moneyLabel(e)==='Gratis';
    if (period==='near') { const km=distance(e);return km!==null && km<=50; }
    return true;
  };
  const organic = () => state.events.filter(e => !e.paid_promotion && active(e));
  const sorted = (items) => items.slice().sort((a,b) =>
    eventDate(a).localeCompare(eventDate(b)) || String(a.title).localeCompare(String(b.title),'es'));
  const favorites = () => sorted(organic().filter(e=>state.saved.has(String(e.id))));
  const toast = (message) => {
    const el=$('toast'); el.textContent=message;el.classList.add('visible');
    clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove('visible'),2800);
  };
  const tile = (e, sponsor=false) => {
    const id = html(e.id);
    const cover=poster(e,'thumb');
    const category=categoryNames[e.category]||'Agenda';
    const saved=state.saved.has(String(e.id));
    const art = cover ? eventImg(e,'tile-img') : '<div class="category-pattern" aria-hidden="true">'+html(categorySymbols[e.category]||'✦')+'</div>';
    const url = safeUrl(e.source_url || e.organizer_url);
    const label = sponsor ? 'Publicidad' : category;
    return '<article class="event-tile '+(sponsor?'tile-sponsor':'')+'">'+
      '<div class="tile-art '+(cover?'':'no-poster')+'" '+(sponsor?'':'data-open="'+id+'" role="button" tabindex="0" aria-label="Ver '+html(title(e))+'"')+'>'+
      art +'<span class="tile-date">'+html(sponsor?'Publicidad · contenido patrocinado':dateBadge(e))+'</span>'+
      (sponsor?'':'<button type="button" class="tile-fav '+(saved?'saved':'')+'" data-save="'+id+'" aria-label="'+(saved?'Quitar de guardados':'Guardar evento')+'" aria-pressed="'+saved+'">'+(saved?'♥':'♡')+'</button>')+
      '</div><div class="tile-details" '+(sponsor?'':'data-open="'+id+'" role="button" tabindex="0"')+'>'+
      '<span class="tile-category">'+html(label)+'</span>'+
      '<strong class="tile-title">'+html(title(e))+'</strong>'+
      '<span class="tile-subline">⌖ <span>'+html(e.municipality||e.venue||'Canarias')+'</span></span>'+
      (sponsor ? (url?'<a class="tile-price" href="'+html(url)+'" target="_blank" rel="noopener noreferrer">Conocer más ↗</a>':'') :
      '<span class="tile-price">'+html(moneyLabel(e))+(distance(e)!==null?' · '+Math.round(distance(e))+' km':'')+'</span>')+
      '</div></article>';
  };
  const empty = (msg,cta='Explorar todos los planes') =>
    '<div class="blank-slate"><span class="blank-icon">✳</span><strong>Aquí todavía no hay planes</strong><p>'+html(msg)+'</p><button type="button" data-reset="1">'+html(cta)+'</button></div>';

  function setView(view) {
    if (!['home','explore','saved','more'].includes(view)) return;
    state.view=view;
    document.body.dataset.view=view;
    for (const v of ['home','explore','saved','more']) {
      const elem=$(v+'View'); const selected=v===view;
      elem.hidden=!selected;elem.classList.toggle('active',selected);
    }
    document.querySelectorAll('[data-view]').forEach(btn=>{
      const selected=btn.dataset.view===view;
      btn.classList.toggle('selected',selected);
      if(selected)btn.setAttribute('aria-current','page');else btn.removeAttribute('aria-current');
    });
    if(view==='explore')renderExplore();
    if(view==='saved')renderSaved();
    window.scrollTo({top:0,behavior:'instant'});
  }

  function featureChoices() {
    // Choose a compact editorial selection of upcoming events with real official art.
    // Long-running activities shouldn't eclipse this week's performances.
    const nextMonth = isoOffset(today,30);
    const soon = sorted(organic().filter(e =>
      day(e.start)>=today && day(e.start)<=nextMonth && poster(e,'thumb') &&
      title(e).length>=8
    ));
    const byReadableTitle = soon.filter(e => title(e).length<=54);
    const interesting = (byReadableTitle.length>=4 ? byReadableTitle : soon).slice()
      .sort((a,b) => {
        const weight={musica:5,cultura:4,familia:3,gastronomia:2,deporte:1,ocio:0,otros:0,naturaleza:1};
        const wa=weight[a.category]||0,wb=weight[b.category]||0;
        const da= Math.max(0, Math.round((new Date(day(a.start)+'T12:00:00Z')-new Date(today+'T12:00:00Z'))/86400000));
        const db= Math.max(0, Math.round((new Date(day(b.start)+'T12:00:00Z')-new Date(today+'T12:00:00Z'))/86400000));
        return (db-da)*0.18+(wb-wa)*(-1) || day(a.start).localeCompare(day(b.start));
      });
    const chosen=[],categories=new Set(),images=new Set();
    for(const e of interesting) {
      if(categories.has(e.category)||images.has(String(e.image_url)))continue;
      chosen.push(e);categories.add(e.category);images.add(String(e.image_url));
      if(chosen.length===4)break;
    }
    for(const e of interesting) {
      if(chosen.length===4)break;
      if(images.has(String(e.image_url)))continue;
      chosen.push(e);images.add(String(e.image_url));
    }
    if(!chosen.length)chosen.push(...sorted(organic().filter(e=>poster(e,'thumb'))).slice(0,4));
    return chosen;
  }
  function renderFeature() {
    const e=state.featured[state.heroIndex];
    if(!e){$('hero').innerHTML=empty('No se han encontrado eventos para destacar.');$('heroDots').innerHTML='';return;}
    const cover=poster(e,'detail');
    $('hero').innerHTML='<div class="feature">'+
      (cover?'<img class="feature-image '+isPosterArt(e)+'" fetchpriority="high" decoding="async" src="'+html(cover)+'" alt="'+html(e.image_alt||title(e))+'">' :
      '<div class="feature-fallback" aria-hidden="true">'+html(categorySymbols[e.category]||'✦')+'</div>')+
      '<div class="feature-content"><span class="feature-pill">✦ PLAN DESTACADO</span>'+
      '<p class="feature-eyebrow">'+html(categoryNames[e.category]||'Agenda')+' · '+html(dateBadge(e))+'</p>'+
      '<h3 class="feature-title">'+html(title(e))+'</h3>'+
      '<div class="feature-meta">⌖ '+html(e.municipality||'Gran Canaria')+(e.venue?' · '+html(e.venue):'')+'</div>'+
      '<button class="feature-cta" type="button" data-open="'+html(e.id)+'">Descubrir plan <span aria-hidden="true">→</span></button></div>'+
      '<div class="feature-nav"><button type="button" data-hero-shift="-1" aria-label="Anterior destacado">‹</button><button type="button" data-hero-shift="1" aria-label="Siguiente destacado">›</button></div></div>';
    $('heroDots').innerHTML=state.featured.map((_,index)=>
      '<button type="button" data-hero-index="'+index+'" class="'+(index===state.heroIndex?'active':'')+'" aria-label="Destacado '+(index+1)+'" aria-pressed="'+(index===state.heroIndex)+'"></button>').join('');
  }
  function shiftHero(delta) {
    if(state.featured.length<2)return;
    state.heroIndex=(state.heroIndex+delta+state.featured.length)%state.featured.length;
    renderFeature();
  }
  function adsTile() {
    const ad=state.ads.find(a=>a.enabled!==false);
    if(!ad) return '';
    const image=safeUrl(ad.image);
    const link=safeUrl(ad.button_url);
    return '<article class="event-tile tile-sponsor">'+
      '<div class="tile-art '+(image?'':'no-poster')+'">'+
      (image?'<img src="'+html(image)+'" alt="'+html(ad.image_alt||ad.advertiser||'Anuncio')+'" loading="lazy" decoding="async">':'<div class="category-pattern">✦</div>')+
      '<span class="tile-date">Publicidad</span></div>'+
      '<div class="tile-details"><span class="tile-category">Contenido patrocinado</span>'+
      '<strong class="tile-title">'+html(ad.headline||ad.advertiser||'Anuncio')+'</strong>'+
      '<span class="tile-subline">⌖ <span>'+html(ad.location||'Canarias')+'</span></span>'+
      (link?'<a class="tile-price" href="'+html(link)+'" rel="noopener noreferrer" target="_blank">'+html(ad.button_text||'Saber más')+' ↗</a>':'')+
      '</div></article>';
  }
  function railSection(heading,kicker,items,tag,withSponsor=false) {
    if(!items.length)return '';
    const list=items.slice(0,14).map(e=>tile(e)).join('');
    return '<section class="rail-section" aria-label="'+html(heading)+'"><div class="section-head"><div><span class="small-kicker">'+html(kicker)+'</span><h2>'+html(heading)+'</h2></div><button type="button" class="section-link" data-explore-period="'+html(tag||'all')+'">Ver todos →</button></div><div class="rail" tabindex="0" aria-label="Desliza para ver '+html(heading)+'">'+list+(withSponsor?adsTile():'')+'</div></section>';
  }

  function renderHome() {
    state.featured=featureChoices();
    if(state.heroIndex>=state.featured.length)state.heroIndex=0;
    renderFeature();
    const all=sorted(organic());
    const upcoming=all.filter(e=>day(e.start)>=today);
    const illustrated=upcoming.filter(e=>poster(e,'thumb'));
    const selection=illustrated.filter(e=>day(e.start)<=isoOffset(today,21));
    const picks=selection.length ? selection : illustrated;
    const todayItems=all.filter(isToday);
    const weekendItems=all.filter(inWeekend);
    const family=all.filter(e=>e.category==='familia');
    const music=all.filter(e=>e.category==='musica');
    const culture=all.filter(e=>e.category==='cultura');
    const free=all.filter(e=>moneyLabel(e)==='Gratis');
    $('homeSections').innerHTML=[
      railSection('Descubre tu próximo plan','TE PUEDE GUSTAR',picks,'all'),
      railSection('Este fin de semana','PLANES PARA DISFRUTAR',weekendItems,'weekend',true),
      railSection('Hoy en Canarias','NO TE QUEDES EN CASA',todayItems,'today'),
      railSection('En familia','PARA GRANDES Y PEQUEÑOS',family,'all'),
      railSection('Conciertos y música','SUBE EL VOLUMEN',music,'all'),
      railSection('Arte y cultura','UNA EXPERIENCIA DIFERENTE',culture,'all'),
      railSection('Planes gratuitos','SAL Y DISFRUTA',free,'free')
    ].join('') || empty('No hay eventos disponibles actualmente.');
  }
  function renderCategories(){
    $('categoryFilters').innerHTML=[['all','Todos'],...Object.entries(categoryNames)].map(([key,label])=>
      '<button type="button" class="category-pill '+(state.category===key?'active':'')+'" data-category="'+html(key)+'" aria-pressed="'+(state.category===key)+'">'+
      (key==='all'?'✦ ':html(categorySymbols[key]+' '))+html(label)+'</button>').join('');
  }
  function exploreItems() {
    const q=normalize(state.query.trim());
    let all=sorted(organic().filter(e=>filterPeriod(e,state.period)));
    if(state.category!=='all')all=all.filter(e=>e.category===state.category);
    if(q)all=all.filter(e=>contains(e,q));
    if(state.period==='near' && state.coords)all.sort((a,b)=>(distance(a)??99999)-(distance(b)??99999));
    return all;
  }
  function renderExplore() {
    renderCategories();
    const items=exploreItems();
    $('resultCounter').textContent=items.length+' planes';
    $('exploreGrid').innerHTML=items.length?items.slice(0,state.visible).map(e=>tile(e)).join(''):
      empty('Prueba con otra fecha, categoría o municipio.');
    $('moreButton').hidden=items.length<=state.visible;
  }
  function renderSaved() {
    const items=favorites();
    $('savedGrid').innerHTML=items.length?items.map(e=>tile(e)).join(''):
      empty('Guarda los eventos que te gusten pulsando ♡. Aquí aparecerán tus favoritos.');
  }
  function selectPeriod(period) {
    state.period=period;
    document.querySelectorAll('[data-period]').forEach(el=>el.classList.toggle('active',el.dataset.period===period));
    state.visible=16;
    setView('explore');
    if(period==='near'&&!state.coords)requestLocation(true);
  }
  function persistFavorites() {
    try {localStorage.setItem('dparranda-v2-saved',JSON.stringify([...state.saved]));} catch { /* storage restricted */ }
  }
  function toggleFavorite(id) {
    const key=String(id);
    if(state.saved.has(key)){state.saved.delete(key);toast('Eliminado de tus planes guardados');}
    else{state.saved.add(key);toast('¡Plan guardado!');}
    persistFavorites();
    if(state.view==='saved')renderSaved();
    if(state.view==='explore')renderExplore();
    if(state.view==='home')renderHome();
    const dialog=$('modal');
    if(!dialog.hidden && dialog.dataset.event===key)showEvent(key,false);
  }
  function eventById(id) {return state.events.find(e=>String(e.id)===String(id));}
  function showEvent(id,updateUrl=true) {
    const e=eventById(id);
    if(!e || e.paid_promotion)return;
    const image=poster(e,'detail'), link=safeUrl(e.organizer_url||e.source_url);
    const saved=state.saved.has(String(e.id));
    const date=day(e.start) ? new Intl.DateTimeFormat('es-ES',{weekday:'long',day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(day(e.start)+'T12:00:00Z')) : 'Consultar fecha';
    const time=String(e.start||'').match(/T(\d\d):(\d\d)/);
    const desc=cap(e.details);
    $('modalContent').innerHTML=
      (image?'<img class="detail-image '+isPosterArt(e)+'" alt="'+html(e.image_alt||title(e))+'" src="'+html(image)+'">':
        '<div class="detail-no-image" aria-hidden="true">'+html(categorySymbols[e.category]||'✦')+'</div>')+
      '<div class="detail-body"><span class="detail-kicker">'+html(categoryNames[e.category]||'Agenda')+' · '+html(moneyLabel(e))+'</span>'+
      '<h2 id="detailTitle">'+html(title(e))+'</h2>'+
      '<div class="detail-facts"><p>▣ <strong>'+html(date)+(time?' · '+time[1]+':'+time[2]:'')+'</strong></p>'+
      '<p>⌖ '+html((e.venue ? e.venue+' · ' : '')+(e.municipality||'Canarias'))+'</p></div>'+
      (desc?'<p class="detail-description">'+html(desc)+'</p>':'')+
      '<div class="detail-actions">'+(link?'<a href="'+html(link)+'" class="primary" target="_blank" rel="noopener noreferrer">Web oficial ↗</a>':'')+
      '<button type="button" data-save="'+html(e.id)+'">'+(saved?'♥ Quitar favorito':'♡ Guardar plan')+'</button>'+
      '<button type="button" data-share="'+html(e.id)+'">↗ Compartir</button></div>'+
      '<p class="detail-credit">Información orientativa. Confirma horarios, accesos y posibles cambios en la fuente oficial. '+html(e.source_name||'')+'</p></div>';
    $('modal').dataset.event=String(id);
    $('modal').hidden=false;
    document.body.style.overflow='hidden';
    if(updateUrl){const u=new URL(location.href);u.searchParams.set('evento',id);history.replaceState(null,'',u);}
    $('modalClose').focus({preventScroll:true});
  }
  function closeEvent() {
    $('modal').hidden=true;document.body.style.overflow='';
    const u=new URL(location.href);u.searchParams.delete('evento');history.replaceState(null,'',u);
  }
  async function shareEvent(id) {
    const e=eventById(id);if(!e)return;
    const url=new URL(location.href);url.pathname='/v2/';url.search='';url.searchParams.set('evento',id);
    if(navigator.share) {
      try{await navigator.share({title:title(e),text:'Mira este plan en DParranda',url:url.href});return;}
      catch(err){if(err?.name==='AbortError')return;}
    }
    try {await navigator.clipboard.writeText(url.href);toast('Enlace copiado');}
    catch {toast('No se pudo copiar el enlace');}
  }
  function requestLocation(fromNear=false) {
    if(!navigator.geolocation) {toast('La geolocalización no está disponible');return;}
    $('locationLabel').textContent='Localizando…';
    navigator.geolocation.getCurrentPosition(position=>{
      state.coords={lat:position.coords.latitude,lng:position.coords.longitude};
      $('locationLabel').textContent='Cerca de ti';
      toast('Mostrando planes por distancia aproximada');
      if(state.view==='explore')renderExplore();
      if(state.view==='home')renderHome();
    },()=>{
      $('locationLabel').textContent='Gran Canaria';
      if(fromNear){state.period='all';document.querySelectorAll('[data-period]').forEach(el=>el.classList.toggle('active',el.dataset.period==='all'));}
      toast('Activa los permisos de ubicación para ver planes cercanos');
      if(state.view==='explore')renderExplore();
    },{enableHighAccuracy:false,timeout:11000,maximumAge:300000});
  }
  function bindEvents() {
    document.addEventListener('click',(event)=>{
      const button=event.target.closest('button,a,[data-open]');
      if(!button)return;
      if(button.dataset.view){setView(button.dataset.view);return;}
      if(button.dataset.period){selectPeriod(button.dataset.period);return;}
      if(button.dataset.category){state.category=button.dataset.category;state.visible=16;renderExplore();return;}
      if(button.dataset.heroShift){shiftHero(Number(button.dataset.heroShift));return;}
      if(button.dataset.heroIndex){state.heroIndex=Number(button.dataset.heroIndex);renderFeature();return;}
      if(button.dataset.save){event.stopPropagation();toggleFavorite(button.dataset.save);return;}
      if(button.dataset.open){showEvent(button.dataset.open);return;}
      if(button.dataset.share){shareEvent(button.dataset.share);return;}
      if(button.dataset.explorePeriod){selectPeriod(button.dataset.explorePeriod);return;}
      if(button.dataset.reset){state.category='all';state.query='';$('searchInput').value='';selectPeriod('all');return;}
    });
    document.addEventListener('keydown',(event)=>{
      if(event.key==='Escape'&&!$('modal').hidden){closeEvent();return;}
      const node=event.target.closest('[data-open]');
      if(node&&(event.key==='Enter'||event.key===' ')){event.preventDefault();showEvent(node.dataset.open);}
    });
    document.addEventListener('error',(event)=>{
      const el=event.target;
      if(el.tagName!=='IMG' || !el.closest('.feature,.tile-art,.detail-dialog'))return;
      const parent=el.parentElement;el.remove();
      if(parent.classList.contains('tile-art')) {
        parent.classList.add('no-poster');
        if(!parent.querySelector('.category-pattern')){
          const fallback=document.createElement('div');fallback.className='category-pattern';
          fallback.textContent='✦';fallback.setAttribute('aria-hidden','true');parent.prepend(fallback);
        }
      }else if(parent.classList.contains('feature')) {
        const fallback=document.createElement('div');fallback.className='feature-fallback';fallback.textContent='✦';parent.prepend(fallback);
      }
    },true);
    $('searchForm').addEventListener('submit',event=>{
      event.preventDefault();state.query=$('searchInput').value.trim();state.visible=16;setView('explore');
    });
    $('searchInput').addEventListener('input',()=>{
      state.query=$('searchInput').value;
      if(state.view==='explore'){state.visible=16;renderExplore();}
    });
    $('locationButton').addEventListener('click',()=>requestLocation());
    $('moreButton').addEventListener('click',()=>{state.visible+=16;renderExplore();});
    $('modalClose').addEventListener('click',closeEvent);
    $('modal').addEventListener('click',event=>{if(event.target===$('modal'))closeEvent();});
    const hero=$('hero');let startX=null;
    hero.addEventListener('touchstart',event=>{startX=event.touches[0]?.clientX??null;},{passive:true});
    hero.addEventListener('touchend',event=>{
      if(startX===null)return;
      const diff=(event.changedTouches[0]?.clientX??startX)-startX;
      if(Math.abs(diff)>45)shiftHero(diff<0?1:-1);
      startX=null;
    },{passive:true});
  }
  async function fetchCatalog() {
    try {
      const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),6000);
      let response;
      try{response=await fetch('/api/catalog',{signal:controller.signal,cache:'no-store'});}
      finally{clearTimeout(timer);}
      if(!response.ok)throw new Error('API '+response.status);
      const data=await response.json();
      if(!Array.isArray(data.events))throw new Error('Formato de API');
      state.source='live';
      return data.events;
    }catch{
      const response=await fetch('/events.json',{cache:'no-store'});
      if(!response.ok)throw new Error('Catálogo no disponible ('+response.status+')');
      const data=await response.json();
      if(!Array.isArray(data.events))throw new Error('Datos no válidos');
      state.source='static';
      return data.events;
    }
  }
  async function init() {
    bindEvents();
    try {
      const [events,ads] = await Promise.all([
        fetchCatalog(),fetch('/ads.json').then(r=>r.ok?r.json():{}).catch(()=>({}))
      ]);
      state.events=events;state.ads=Array.isArray(ads.ads)?ads.ads:[];
      renderHome();renderExplore();renderSaved();
      $('dataSourceNote').textContent=state.source==='live'?
        'Eventos reales del catálogo de DParranda. Confirma siempre los detalles en la fuente oficial.' :
        'Vista experimental con la última copia disponible del catálogo. Algunos cambios recientes pueden no aparecer.';
      const params=new URLSearchParams(location.search);
      if(params.has('evento'))showEvent(params.get('evento'),false);
    }catch(err) {
      $('hero').innerHTML=empty('No se ha podido cargar el catálogo. Puedes volver a la versión actual.');
      $('homeSections').innerHTML='';
      $('dataSourceNote').textContent='No se ha podido acceder a los eventos: '+String(err?.message||'Error');
    }
  }
  init();
})();