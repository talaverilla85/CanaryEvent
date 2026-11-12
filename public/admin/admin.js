(()=>{'use strict';
const $=id=>document.getElementById(id), apiUrl='/api/admin';
let events=[], ads=[], leads=[], promotions=[], opsDrafts=[], pagination=0, filter='all', search='', section='events', current=null, toastTimer;
const escape=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const text=x=>String(x??'').trim();
function message(m){const p=$('feedback');p.textContent=m;p.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>p.classList.remove('show'),3500)}
function display(id,visible){$(id).hidden=!visible}
async function api(op,body=null,params={}) {
  const q=new URLSearchParams({op,...params}),options={method:body===null?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:{}};
  if(body!==null){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body)}
  const r=await fetch(apiUrl+'?'+q.toString(),options);
  let data={};try{data=await r.json()}catch{}
  if(!r.ok)throw new Error(data.error||'Error de conexión ('+r.status+')');
  return data;
}
function setLoginStatus(login){display('dashboard',login);display('login',!login);display('setup',false);$('logout').classList.toggle('hidden',!login)}
async function initialize(){
  try{
    const session=await api('session');
    if(!session.configured){display('setup',true);display('login',false);return}
    setLoginStatus(!!session.authenticated);
    if(session.authenticated)await loadPanel();
  }catch(e){
    if(/pendiente de activar|no configurad/i.test(e.message)){display('setup',true);display('login',false)}
    else{display('login',true);$('loginError').textContent=e.message;$('loginError').classList.remove('hidden')}
  }
}
$('loginForm').addEventListener('submit',async e=>{
  e.preventDefault();const btn=e.target.querySelector('button');btn.disabled=true;$('loginError').classList.add('hidden');
  try{await api('login',{password:$('password').value});$('password').value='';setLoginStatus(true);await loadPanel()}
  catch(err){$('loginError').textContent=err.message;$('loginError').classList.remove('hidden')}
  finally{btn.disabled=false}
});
$('logout').addEventListener('click',async()=>{try{await api('logout',{})}catch{}closeDialog();setLoginStatus(false);$('password').value='';message('Sesión cerrada')});
async function loadStats(){
 const s=await api('stats');$('statEvents').textContent=s.events;$('statReview').textContent=s.reviews;
 $('statHidden').textContent=s.hidden;$('statAds').textContent=s.active_ads;
}
async function loadAdvertisingIntake(){
 const node=$('adopsIntake');if(!node)return;
 try{
  const state=await api('advertising-intake-config');
  if(state.receiving_proposals){
    node.textContent='Recepción de solicitudes: ACTIVADA. Los anunciantes pueden enviar su creatividad y sus datos para revisión, sin pagar.';
    node.classList.add('ready');
    return;
  }
  const missing=[];
  if(!state.leads_enabled)missing.push('DPARRANDA_LEADS_ENABLED = true');
  if(!state.privacy_configured){
    const fields=Array.isArray(state.missing_legal_fields)?state.missing_legal_fields:[];
    if(fields.length)missing.push(...fields.map(name=>name+' = completar identidad del autónomo'));
    else missing.push('Completar información legal de DParranda');
  }
  if(!state.database_configured)missing.push('DATABASE_URL = conexión de Neon');
  node.replaceChildren();
  const intro=document.createElement('strong');
  intro.textContent='Recepción de solicitudes: DESACTIVADA';
  const detail=document.createElement('p');
  detail.textContent='Falta configurar en Vercel: '+missing.join('; ')+'. Guarda los cambios en Production y vuelve a desplegar.';
  const link=document.createElement('a');link.href='https://vercel.com/noe-s-projects-deb823a5/canaryevent/settings/environment-variables';
  link.target='_blank';link.rel='noopener noreferrer';link.textContent='Abrir configuración de Vercel';
  node.append(intro,detail,link);
  const legal=document.createElement('a');legal.href='/privacidad/';legal.target='_blank';
  legal.rel='noopener noreferrer';legal.textContent=' · Previsualizar privacidad';
  node.append(legal);
 }catch(err){node.textContent='No se ha podido comprobar la recepción: '+(err.message||'error de conexión')}
}
async function loadResendSandbox(){
 const button=$('sendResendTest'),status=$('resendTestInfo');
 if(!button||!status)return;
 button.disabled=true;
 try{
  const info=await api('resend-test-config');
  if(info.ready===true){
   status.textContent='Conexión de pruebas preparada. El correo se enviará únicamente a la dirección registrada en tu cuenta Resend; no a anunciantes.';
   button.disabled=false;
  }else{
   status.textContent='Pendiente: añade RESEND_API_KEY y RESEND_TEST_RECIPIENT en Vercel Production y vuelve a desplegar. No envíes la clave por chat.';
  }
 }catch(err){status.textContent='No se pudo comprobar Resend: '+err.message}
}
$('sendResendTest').addEventListener('click',async()=>{
 const button=$('sendResendTest'),status=$('resendTestInfo');
 if(!confirm('¿Enviar un único correo de prueba a tu propia cuenta de Resend? No se enviará nada a los anunciantes.'))return;
 button.disabled=true;status.textContent='Solicitando correo de prueba a Resend…';
 try{
  const result=await api('resend-send-test',{});
  status.textContent=result.message||'Resend ha aceptado el correo de prueba.';
  message('Prueba aceptada por Resend. Comprueba tu correo.');
 }catch(err){status.textContent=err.message;message('No se ha podido enviar la prueba')}
 finally{button.disabled=false}
});
async function loadPanel(){await Promise.allSettled([loadStats(),loadEvents(true),loadAds(),loadLeads(),loadPromotions(),loadAdvertiserAccounts(),loadAdvertiserDrafts(),loadAdvertisingIntake(),loadResendSandbox()]);if(location.hash==='#publicidad')setSection('ads')}
function setSection(next){
 section=next;display('eventsSection',next==='events');display('adsSection',next==='ads');
 for(const [id,on] of [['tabEvents',next==='events'],['tabAds',next==='ads']]){
  $(id).classList.toggle('active',on);$(id).setAttribute('aria-selected',on?'true':'false')
 }
}
$('tabEvents').onclick=()=>setSection('events');$('tabAds').onclick=()=>setSection('ads');
const dateLabel=e=>{const d=String(e.start||'').slice(0,10);return /^\d{4}-\d\d-\d\d$/.test(d)?d.split('-').reverse().join('/'):d};
async function loadEvents(reset=false) {
 if(reset){pagination=0;events=[]}
 $('eventsList').innerHTML='<div class="empty">Cargando eventos…</div>';
 try{
  const d=await api('events',null,{q:search,only:filter,offset:String(pagination)});
  events=reset?d.events:events.concat(d.events);
  pagination=d.next_offset;
  $('moreEvents').hidden=!d.has_more;
  renderEvents();
 }catch(e){$('eventsList').innerHTML='<div class="empty">'+escape(e.message)+'</div>'}
}
function renderEvents(){
 if(!events.length){$('eventsList').innerHTML='<div class="empty">No hay eventos con estos criterios.</div>';return}
 $('eventsList').innerHTML=events.map(row=>{
  const e=row.payload||{};const id=row.id;
  const labels=[row.possible_duplicate?'<span class="pill warning">Posible duplicado</span>':'',
   row.hidden?'<span class="pill off">Oculto</span>':'',
   row.canonical_event_id?'<span class="pill off">Unificado</span>':'',
   row.review_status==='needs_review'?'<span class="pill warning">Revisión pendiente</span>':''].filter(Boolean).join('');
  return '<article class="event"><div class="event-info"><small>#'+escape(id)+' · '+escape(dateLabel(e))+'</small>'+
    '<strong>'+escape(row.title_override||e.title||'Sin título')+'</strong>'+
    '<p>'+escape(row.venue_override||e.venue||'Recinto por confirmar')+' · '+escape(e.municipality||'')+'</p>'+
    '<div class="meta">'+labels+'</div></div><div class="actions"><button class="ghost mini" data-event="'+escape(id)+'" type="button">Revisar ficha</button>'+
    (row.hidden&&!row.canonical_event_id?'<button class="ghost mini restore-action" data-restore-event="'+escape(id)+'" type="button" aria-label="Restaurar evento '+escape(id)+'">Restaurar</button>':
     row.possible_duplicate&&!row.canonical_event_id?'<button class="ghost mini warn remove-duplicate" data-hide-duplicate="'+escape(id)+'" type="button" aria-label="Quitar duplicado '+escape(id)+' de la web">Quitar duplicado</button>':'')+
    '</div></article>';
 }).join('');
}
$('refreshEvents').onclick=()=>loadEvents(true);
let searchTimer;$('searchEvents').addEventListener('input',e=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{search=e.target.value.trim();loadEvents(true)},350)});
$('eventFilter').onchange=e=>{filter=e.target.value;loadEvents(true)};
$('moreEvents').onclick=()=>loadEvents(false);
async function changeEventVisibility(row,hidden,button){
 if(hidden){
  if(!row.possible_duplicate || row.hidden || row.canonical_event_id)return;
  const e=row.payload||{};
  if(!window.confirm('¿Quitar de la web pública este posible duplicado?\n\n'+
    (e.title||'Evento #'+row.id)+' · '+(e.municipality||'')+
    '\n\nLa ficha quedará oculta, pero podrás restaurarla desde el filtro «Ocultos». No se borrará de la fuente.'))return;
 }else{
  if(!row.hidden || row.canonical_event_id)return;
  if(!window.confirm('¿Restaurar esta ficha en la web pública?\n\nSi sigue duplicada, volverá a aparecer entre los posibles duplicados.'))return;
 }
 button.disabled=true;
 try{
  await api('visibility',{id:row.id,hidden});
  message(hidden?'Duplicado retirado de la web. Puedes restaurarlo.':'Evento restaurado en la web pública.');
  await Promise.allSettled([loadEvents(true),loadStats()]);
 }catch(err){message(err.message);button.disabled=false}
}
$('eventsList').onclick=e=>{
 const removal=e.target.closest('[data-hide-duplicate]');
 const restoration=e.target.closest('[data-restore-event]');
 if(removal||restoration){
  const button=removal||restoration, row=events.find(x=>String(x.id)===button.dataset.hideDuplicate||String(x.id)===button.dataset.restoreEvent);
  if(row)changeEventVisibility(row,!!removal,button);
  return;
 }
 const b=e.target.closest('[data-event]');if(!b)return;
 const row=events.find(x=>String(x.id)===b.dataset.event);if(row)editEvent(row);
};
function closeDialog(){$('dialog').classList.add('hidden');$('dialog').setAttribute('aria-hidden','true');$('sheet').innerHTML='';current=null}
$('dialog').addEventListener('click',e=>{if(e.target.matches('[data-close]'))closeDialog()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeDialog()});
function openDialog(html){
 $('sheet').innerHTML=html;$('dialog').classList.remove('hidden');$('dialog').setAttribute('aria-hidden','false');
 $('sheet').querySelector('input,textarea,select,button')?.focus();
}
function field(name,label,value='',placeholder='',wide=false,kind='text'){
 return '<div class="field '+(wide?'wide':'')+'"><label for="f-'+escape(name)+'">'+escape(label)+'</label>'+
 (kind==='textarea'?'<textarea id="f-'+escape(name)+'" name="'+escape(name)+'" placeholder="'+escape(placeholder)+'">'+escape(value)+'</textarea>':
 '<input id="f-'+escape(name)+'" name="'+escape(name)+'" type="'+escape(kind)+'" value="'+escape(value)+'" placeholder="'+escape(placeholder)+'">')+'</div>';
}
function editEvent(row){
 current=row;const e=row.payload||{};
 const original=escape(e.title||'')+' · '+escape(e.municipality||'')+' · '+escape(e.start||'');
 const link=/^https:\/\//i.test(e.source_url||'')?'<a href="'+escape(e.source_url)+'" target="_blank" rel="noopener noreferrer">Ver fuente oficial ↗</a>':'';
 const content='<div class="sheet-head"><div><span class="eyebrow">Revisión de evento #'+escape(row.id)+'</span><h2 id="dialogTitle">Editar ficha</h2></div><button class="ghost mini" type="button" data-close>✕</button></div>'+
 '<p class="muted modal-intro">'+original+'</p><p class="modal-link">'+link+'</p>'+
 '<form id="eventForm"><div class="form-grid">'+
 field('title_override','Título corregido',row.title_override||'',e.title||'',true)+
 field('venue_override','Recinto corregido',row.venue_override||'',e.venue||'',true)+
 field('details_override','Descripción ampliada',row.details_override||'',e.details||'',true,'textarea')+
 field('price_override','Precio corregido',row.price_override||'',e.price||'')+
 field('category_override','Categoría corregida',row.category_override||'',e.category||'')+
 '<div class="field"><label for="f-free">¿Es gratuito?</label><select id="f-free" name="free_override"><option value="">Conservar fuente</option><option value="1">Sí, gratuito</option><option value="0">No</option></select></div>'+
 '<div class="field"><label for="f-review">Estado de revisión</label><select id="f-review" name="review_status"><option value="unreviewed">Sin revisar</option><option value="needs_review">Revisión pendiente</option><option value="approved">Comprobado</option><option value="rejected">Rechazado</option></select></div>'+
 field('canonical_event_id','ID de la ficha principal (si es duplicado)',row.canonical_event_id||'','Sin fusionar')+
 '</div><label class="checkbox"><input id="f-hidden" name="hidden" type="checkbox" '+(row.hidden?'checked':'')+'>Ocultar esta ficha de la web pública</label>'+
 '<p class="notice">Los campos en blanco conservan el valor original. Si introduces un ID principal, debe pertenecer al mismo día y municipio.</p>'+
 '<div class="sheet-footer"><button type="button" class="ghost" data-close>Cancelar</button><button type="submit" class="primary">Guardar correcciones</button></div></form>';
 openDialog(content);$('f-free').value=row.free_override===null||row.free_override===undefined?'':String(row.free_override);
 $('f-review').value=row.review_status||'unreviewed';
 $('eventForm').onsubmit=async ev=>{
  ev.preventDefault();const btn=ev.submitter||$('eventForm').querySelector('[type=submit]');btn.disabled=true;
  const f=new FormData(ev.currentTarget),obj=Object.fromEntries(f.entries());
  obj.id=row.id;obj.hidden=$('f-hidden').checked;
  try{await api('event',obj);closeDialog();message('Ficha guardada');await Promise.allSettled([loadEvents(true),loadStats()])}
  catch(err){message(err.message);btn.disabled=false}
 };
}
async function loadAds() {
 $('adsList').innerHTML='<div class="empty">Cargando campañas…</div>';
 try{const response=await api('ads');ads=response.ads||[];renderAds();renderAdOperations()}
 catch(e){$('adsList').innerHTML='<div class="empty">'+escape(e.message)+'</div>'}
}
function renderAds(){
 if(!ads.length){$('adsList').innerHTML='<div class="empty">Todavía no hay campañas publicitarias.</div>';return}
 $('adsList').innerHTML=ads.map(a=>{
  const preview=a.enquiry_id?'/api/admin?op=leadimage&id='+Number(a.enquiry_id):a.image;
  const image=/^\/sponsors\/[a-z0-9._/-]+\.(webp|png|jpeg|jpg)$/i.test(preview||'')||/^\/api\/admin\?op=leadimage&id=[0-9]+$/.test(preview)?
    '<img src="'+escape(preview)+'" alt="'+escape(a.image_alt||'Anuncio')+'" loading="lazy">':'Imagen pendiente';
  const dates=a.permanent?'Permanente':(a.starts_at?String(a.starts_at).slice(0,10):'Desde ahora')+' – '+(a.ends_at?String(a.ends_at).slice(0,10):'Sin final')+' · '+daysLeft(a.ends_at);
  return '<article class="ad-card"><div class="ad-media">'+image+'</div><div class="ad-content"><span class="pill '+(a.enabled?'':'off')+'">'+(a.enabled?'Activa':'Pausada')+'</span>'+
   '<h3>'+escape(a.headline)+'</h3><p>'+escape(a.description)+'</p><small class="muted">'+escape(a.advertiser)+' · '+escape(dates)+'</small>'+
   '<div class="ad-footer"><small class="muted">'+(Array.isArray(a.municipalities)&&a.municipalities.length?escape(a.municipalities.join(', ')):'Toda Gran Canaria')+'</small>'+
   '<button class="ghost mini" data-ad="'+escape(a.id)+'" type="button">Editar</button></div></div></article>';
 }).join('');
}
$('adsList').onclick=e=>{const btn=e.target.closest('[data-ad]');if(!btn)return;editAd(ads.find(a=>a.id===btn.dataset.ad))};
$('newAd').onclick=()=>editAd(null);
function editAd(ad){
 if(!ad)ad={enabled:false,kind:'paid',permanent:false,municipalities:[]};
 const dates=v=>typeof v==='string'?v.slice(0,10):'';
 let content='<div class="sheet-head"><div><span class="eyebrow">Publicidad · Solo administración</span><h2 id="dialogTitle">'+(ad.id?'Editar campaña':'Nueva campaña')+'</h2></div><button class="ghost mini" type="button" data-close>✕</button></div>'+
 '<form id="adForm"><div class="form-grid">'+
 field('advertiser','Anunciante',ad.advertiser||'')+
 field('headline','Titular del anuncio',ad.headline||'')+
 field('description','Descripción',ad.description||'','',true,'textarea')+
 field('location','Ubicación mostrada',ad.location||'')+
 field('button_text','Texto del botón',ad.button_text||'Descubrir')+
 field('button_url','Enlace de destino HTTPS',ad.button_url||'','https://...',true,'url')+
 field('image','Imagen (ruta /sponsors/...webp)',ad.image||'','/sponsors/archivo.webp',true)+
 field('image_alt','Descripción accesible de la imagen',ad.image_alt||'','',true)+
 field('starts_at','Inicio',dates(ad.starts_at),'',false,'date')+
 field('ends_at','Finalización',dates(ad.ends_at),'',false,'date')+
 field('municipalities','Municipios (separados por coma; vacío = toda la isla)',(ad.municipalities||[]).join(', '),'Agüimes, Ingenio',true)+
 '<div class="field"><label for="f-kind">Tipo de campaña</label><select name="kind" id="f-kind"><option value="paid">Comercial</option><option value="house">Propia</option></select></div></div>'+
 '<label class="checkbox"><input type="checkbox" id="f-enabled" '+(ad.enabled?'checked':'')+'>Campaña activa</label>'+
 '<label class="checkbox"><input type="checkbox" id="f-permanent" '+(ad.permanent?'checked':'')+'>Campaña permanente</label>'+
 '<p class="notice">La publicidad se mostrará únicamente cuando esté activa y cumpla las fechas indicadas.</p>'+
 '<div class="sheet-footer"><button type="button" class="ghost" data-close>Cancelar</button><button class="primary" type="submit">Guardar campaña</button></div></form>';
 openDialog(content);$('f-kind').value=ad.kind||'paid';
 $('adForm').onsubmit=async ev=>{
  ev.preventDefault();const b=ev.submitter||$('adForm').querySelector('[type=submit]');b.disabled=true;
  const f=Object.fromEntries(new FormData(ev.currentTarget).entries());
  f.id=ad.id||undefined;f.enabled=$('f-enabled').checked;f.permanent=$('f-permanent').checked;
  f.municipalities=String(f.municipalities||'').split(',').map(x=>x.trim()).filter(Boolean);
  f.starts_at=f.starts_at||null;f.ends_at=f.ends_at||null;
  try{await api('ad',f);closeDialog();message('Campaña guardada');await Promise.allSettled([loadAds(),loadStats()])}
  catch(err){message(err.message);b.disabled=false}
 };
}

function daysLeft(value){
 if(!value)return 'Sin fecha de fin';
 const key=String(value).slice(0,10);
 const todayParts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 const today=[todayParts.year,todayParts.month,todayParts.day].join('-');
 const days=Math.round((Date.parse(key+'T00:00:00Z')-Date.parse(today+'T00:00:00Z'))/86400000)+1;
 return days<1?'Campaña finalizada':days===1?'Último día':days+' días restantes';
}
async function loadLeads(){
 const list=$('leadsList');if(!list)return;
 list.innerHTML='<div class="empty">Cargando solicitudes…</div>';
 try{const data=await api('leads');leads=data.leads||[];renderLeads();renderAdOperations();const pending=leads.filter(l=>l.status==='new'&&String(l.dates_text||'').startsWith('INTERES_INICIAL|')).length;$('tabAds').textContent='Publicidad'+(pending?' · '+pending+' interesados':'')}
 catch(e){list.innerHTML='<div class="empty">'+escape(e.message)+'</div>'}
}
function renderLeads(){
 if(!leads.length){$('leadsList').innerHTML='<div class="empty">No hay solicitudes comerciales registradas.</div>';return}
 $('leadsList').innerHTML=leads.map(l=>{
 const id=Number(l.id),interest=String(l.dates_text||'').startsWith('INTERES_INICIAL|'),eligible=!interest&&!!(l.event_title&&l.event_start&&l.event_venue&&l.event_municipality);
 return '<article class="event lead-item"><div class="event-info"><small>Solicitud #'+id+' · '+escape(String(l.created_at).slice(0,10))+
  ' · '+escape(l.status)+(interest?' · INTERESADO':'')+'</small><strong>'+escape(l.company)+' · '+escape(l.campaign_name)+'</strong>'+
  '<p>'+escape(l.format)+' · '+escape(l.municipality)+' · '+escape(l.email)+' · '+escape(l.telephone)+'</p>'+
  '<div class="meta"><span class="pill">'+escape(l.campaign_days)+' días</span><span class="pill off">'+escape(l.campaign_start||'Sin fecha')+'</span></div>'+
  '<details class="lead-detail"><summary>'+(interest?'Ver contacto y tarifa elegida':'Ver propuesta, imagen y datos fiscales')+'</summary>'+
  '<p><strong>Contacto:</strong> '+escape(l.contact_name)+' · '+escape(l.email)+' · '+escape(l.telephone)+'</p>'+
  (interest?'':'<p><strong>Facturar a:</strong> '+escape(l.legal_name)+' · '+escape(l.tax_id)+'</p>')+
  (interest?'':'<p>'+escape(l.billing_address)+' · '+escape(l.billing_postal)+' '+escape(l.billing_city)+' · '+escape(l.billing_region)+' · '+escape(l.billing_country)+'</p>')+
  (interest?'':'<p><strong>Email de facturas:</strong> '+escape(l.billing_email)+'</p>')+
  '<p><strong>Evento:</strong> '+escape(l.event_title||'No aplica')+' · '+escape(l.event_start||'')+' · '+escape(l.event_municipality||'')+' · '+escape(l.event_venue||'')+'</p>'+
  '<p><strong>Descripción:</strong> '+escape(l.message)+'</p>'+
  '<p><a href="'+escape(l.action_url||'#')+'" target="_blank" rel="noopener noreferrer">Web o entradas ↗</a></p>'+
  (interest?'':'<img class="lead-image" loading="lazy" src="/api/admin?op=leadimage&id='+id+'" alt="'+escape(l.creative_alt||'Imagen de propuesta')+'">')+
  '</details></div><div class="actions lead-actions">'+
  (eligible?'<button type="button" class="ghost mini" data-lead="'+id+'" data-mode="event">Crear evento</button>':'')+
  (interest?'':'<button type="button" class="ghost mini" data-lead="'+id+'" data-mode="banner">Crear banner</button>')+
  '<button type="button" class="ghost mini" data-lead="'+id+'" data-mode="invite">Crear acceso privado</button>'+ 
  (l.status==='new'?'<button type="button" class="ghost mini" data-lead="'+id+'" data-mode="contact">Marcar contactado</button>':'')+
  '</div></article>';
 }).join('');
}
$('leadsList').onclick=async e=>{
 const btn=e.target.closest('[data-lead]');if(!btn)return;
 const id=Number(btn.dataset.lead),mode=btn.dataset.mode;btn.disabled=true;
 try{
  if(mode==='invite'){
   await createAdvertiserInvite(id);
  }else{
   if(mode==='contact')await api('lead-status',{id,status:'contacted'});
   else await api('promote',{id,placement:mode});
   message(mode==='contact'?'Solicitud marcada como contactada':'Borrador creado. Revísalo antes de publicar.');
   await Promise.allSettled([loadLeads(),loadPromotions(),loadAds(),loadStats()]);
  }
 }catch(err){message(err.message)}finally{btn.disabled=false}
};
async function loadPromotions(){
 const list=$('promotionsList');if(!list)return;
 list.innerHTML='<div class="empty">Cargando eventos promocionados…</div>';
 try{const data=await api('promotions');promotions=data.promotions||[];renderPromotions();renderAdOperations()}
 catch(e){list.innerHTML='<div class="empty">'+escape(e.message)+'</div>'}
}
function renderPromotions(){
 if(!promotions.length){$('promotionsList').innerHTML='<div class="empty">No hay eventos patrocinados. Puedes crear uno desde una solicitud.</div>';return}
 $('promotionsList').innerHTML=promotions.map(p=>{
  const active=p.enabled&&p.review_status==='approved';
  return '<article class="event"><div class="event-info"><small>Promoción #'+escape(p.id)+' · '+escape(p.start)+'</small>'+
   '<strong>'+escape(p.title)+'</strong><p>'+escape(p.advertiser)+' · '+escape(p.municipality)+' · '+escape(p.venue)+'</p>'+
   '<div class="meta"><span class="pill '+(active?'':'off')+'">'+(active?'Publicada':'Borrador / pausada')+'</span>'+
   '<span class="pill warning">'+escape(daysLeft(p.campaign_ends_at))+'</span></div></div>'+
   '<div class="actions"><button class="ghost mini" data-promotion="'+escape(p.id)+'" data-enable="'+(active?'false':'true')+'">'+(active?'Pausar':'Aprobar y publicar')+'</button></div></article>';
 }).join('');
}
$('promotionsList').onclick=async e=>{
 const b=e.target.closest('[data-promotion]');if(!b)return;
 const approved=b.dataset.enable==='true';
 if(approved&&!confirm('¿Has revisado el evento, sus fechas y el acuerdo comercial? Se publicará como patrocinado.'))return;
 b.disabled=true;
 try{await api('promotion-status',{id:Number(b.dataset.promotion),approved,enabled:approved});
 message(approved?'Evento patrocinado publicado':'Evento patrocinado pausado');
 await Promise.allSettled([loadPromotions(),loadStats()]);
 }catch(err){message(err.message)}finally{b.disabled=false}
};

const advertStatus={
 draft:'Borrador',pending_payment:'Pendiente de pago',paid_review:'Pago confirmado · en revisión',
 changes_requested:'Cambios solicitados',approved:'Aprobado',active:'Publicado',
 finished:'Finalizado',rejected:'Rechazado',cancelled:'Cancelado'
};
function showAdvertiserLink(url){
 // Show only once. We never store plaintext invitation tokens or send email.
 if(!/^https:\/\/[^\/]+\/anunciantes\/#acceso=[0-9a-f]{64}$/.test(url||'')){
  message('La invitación no tiene un formato válido');return;
 }
 const html='<div class="sheet-head"><div><span class="eyebrow">Área de anunciantes</span><h2 id="dialogTitle">Enlace personal generado</h2></div>'+
 '<button class="ghost mini" type="button" data-close>✕</button></div>'+
 '<p>Este enlace da acceso privado a la empresa. Cópialo ahora y envíalo tú por correo. No lo publiques en redes ni lo compartas con terceros.</p>'+
 '<div class="field"><label for="privateInvite">Enlace de acceso</label><textarea id="privateInvite" readonly rows="4">'+escape(url)+'</textarea></div>'+
 '<div class="actions"><button id="copyAdvertiserInvite" type="button" class="primary">Copiar enlace</button>'+
 '<button type="button" class="ghost" data-close>Cerrar</button></div>'+
 '<p class="notice">Si regeneras este enlace, los anteriores dejarán de funcionar y se cerrarán las sesiones previas.</p>';
 openDialog(html);
 $('copyAdvertiserInvite').onclick=async()=>{
  const value=$('privateInvite').value;
  try{await navigator.clipboard.writeText(value);message('Enlace copiado. Puedes enviarlo por correo.')}
  catch{$('privateInvite').focus();$('privateInvite').select();message('Selecciona el enlace y cópialo manualmente')}
 };
}
async function createAdvertiserInvite(leadId,rotate=false){
 try{
  const result=await api('advertiser-invite',{lead_id:leadId,rotate});
  showAdvertiserLink(result.invitation_url);
  await loadAdvertiserAccounts();
 }catch(err){
  if(!rotate&&/ya tiene acceso/i.test(err.message)&&
     confirm('Este anunciante ya tiene acceso. ¿Regenerar el enlace e invalidar el anterior?')){
   return createAdvertiserInvite(leadId,true);
  }
  throw err;
 }
}
async function loadAdvertiserAccounts(){
 const root=$('advertiserAccountsList');if(!root)return;
 root.innerHTML='<div class="empty">Cargando accesos…</div>';
 try{
  const result=await api('advertiser-accounts'),accounts=result.accounts||[];
  if(!accounts.length){root.innerHTML='<div class="empty">Todavía no hay invitaciones. Utiliza «Crear acceso privado» desde una solicitud de empresa.</div>';return}
  root.innerHTML=accounts.map(a=>
   '<article class="event"><div class="event-info"><strong>'+escape(a.company)+'</strong>'+
   '<p>'+escape(a.email)+' · '+escape(a.contact_name||'')+'</p>'+
   '<div class="meta"><span class="pill '+(a.active?'':'off')+'">'+(a.active?'Acceso habilitado':'Acceso revocado')+'</span>'+
   '<span class="pill">'+escape(a.campaigns)+' anuncios</span></div></div>'+
   '<div class="actions"><button class="ghost mini" type="button" data-ad-account="'+Number(a.id)+'" data-mode="access" data-active="'+String(!a.active)+'">'+(a.active?'Revocar acceso':'Restaurar acceso')+'</button>'+
   (a.lead_id?'<button class="ghost mini" type="button" data-ad-account="'+Number(a.id)+'" data-mode="rotate" data-lead-id="'+Number(a.lead_id)+'">Nuevo enlace</button>':'')+
   '</div></article>').join('');
 }catch(err){root.innerHTML='<div class="empty">'+escape(err.message)+'</div>'}
}
$('advertiserAccountsList').onclick=async event=>{
 const btn=event.target.closest('[data-ad-account]');if(!btn)return;
 const mode=btn.dataset.mode;btn.disabled=true;
 try{
  if(mode==='rotate'){
   if(confirm('¿Generar un enlace nuevo? El anterior dejará de funcionar.')){
    await createAdvertiserInvite(Number(btn.dataset.leadId),true);
   }
  }else if(mode==='access'){
   const active=btn.dataset.active==='true';
   if(confirm(active?'¿Restaurar el acceso privado de este anunciante?':'¿Revocar su acceso y cerrar sus sesiones?')){
    await api('advertiser-access',{id:Number(btn.dataset.adAccount),active});
    await loadAdvertiserAccounts();
   }
  }
 }catch(err){message(err.message)}finally{btn.disabled=false}
};
async function loadAdvertiserDrafts(){
 const root=$('advertiserDraftsList');if(!root)return;
 root.innerHTML='<div class="empty">Cargando campañas privadas…</div>';
 try{
  const result=await api('advertiser-drafts'),drafts=result.drafts||[];opsDrafts=drafts;renderAdOperations();
  if(!drafts.length){root.innerHTML='<div class="empty">Ningún anunciante ha creado campañas todavía.</div>';return}
  root.innerHTML=drafts.map(d=>{
   const status=advertStatus[d.status]||d.status;
   return '<article class="event"><div class="event-info">'+
    '<small>Anuncio #'+Number(d.id)+' · '+escape(d.account_company)+' · '+escape(status)+'</small>'+
    '<strong>'+escape(d.title)+'</strong>'+
    '<p>'+escape(d.placement)+' · '+escape(d.plan)+' · '+escape(d.days)+' días · '+escape(Number(d.price_cents)/100)+' €</p>'+
    '<div class="meta"><span class="pill off">'+escape(d.payment_status==='paid'?'Pagado':'Sin pago confirmado')+'</span></div>'+
    '<details class="lead-detail"><summary>Ver creatividad y detalles del borrador</summary>'+
    '<p>'+escape(d.description)+'</p>'+
    '<p>Zona: '+escape(Array.isArray(d.municipalities)&&d.municipalities.length?d.municipalities.join(', '):'Toda Gran Canaria')+'</p>'+
    '<p>Inicio solicitado: '+escape(String(d.campaign_start||'Por confirmar').slice(0,10))+'</p>'+
    '<p>Evento: '+escape(d.event_start||'No aplica')+' · '+escape(d.event_town||'')+' · '+escape(d.event_venue||'')+'</p>'+
    (d.has_image?'<img class="lead-image" loading="lazy" src="/api/admin?op=advertiser-draft-image&id='+Number(d.id)+'" alt="'+escape(d.image_alt||'Cartel publicitario')+'">':'<p>Imagen pendiente de subir</p>')+
    '</details></div><div class="actions">'+
    (d.status==='paid_review'&&d.payment_status==='paid'?'<button type="button" class="ghost mini" data-ad-draft="'+Number(d.id)+'" data-review="approved">Aprobar revisión</button>':'')+
    (['draft','paid_review','changes_requested'].includes(d.status)?'<button type="button" class="ghost mini" data-ad-draft="'+Number(d.id)+'" data-review="changes_requested">Pedir cambios</button>':'')+
    (['draft','paid_review','changes_requested'].includes(d.status)?'<button type="button" class="ghost mini warn" data-ad-draft="'+Number(d.id)+'" data-review="rejected">Rechazar</button>':'')+
    '</div></article>';
  }).join('');
 }catch(err){root.innerHTML='<div class="empty">'+escape(err.message)+'</div>'}
}
$('advertiserDraftsList').onclick=async event=>{
 const btn=event.target.closest('[data-ad-draft]');if(!btn)return;
 const status=btn.dataset.review;
 const reason=prompt(status==='approved'?'Observaciones de la revisión (opcional)':'Indica qué debe corregir el anunciante:');
 if(reason===null)return;
 if(status!=='approved'&&!reason.trim()){message('Indica el motivo antes de solicitar cambios o rechazar');return}
 btn.disabled=true;
 try{
  await api('advertiser-review',{id:Number(btn.dataset.adDraft),status,note:reason.trim()});
  await loadAdvertiserDrafts();
  message('Revisión registrada. No se ha publicado ningún anuncio.');
 }catch(err){message(err.message)}finally{btn.disabled=false}
};

/* Advertising control desk: one view over interest, reviewed submissions,
 * advertiser revisions and existing published campaigns. No payment is inferred.
 */
const opsStateNames={
 interest:'Interesado',draft:'Borrador',submitted:'Pendiente de revisión',
 changes_requested:'Cambios solicitados',approved_for_payment:'Aprobado · pago pendiente',
 pending_payment:'Esperando pago',paid_review:'Pago verificado · revisión',
 approved:'Aprobado',active:'Activo',finished:'Caducado',
 rejected:'Rechazado',cancelled:'Cancelado'
};
const opsPlanNames={local:'Local',zona:'Zona',insular:'Insular'};
let opsSearch='',opsFilter='all',opsAllRows=[];
const opsDate=v=>String(v||'').slice(0,10);
const opsToday=()=>{
 const obj=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{
  timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'
 }).formatToParts(new Date()).filter(v=>v.type!=='literal').map(v=>[v.type,v.value]));
 return obj.year+'-'+obj.month+'-'+obj.day;
};
function normalizedOpsRows(){
 const today=opsToday(),result=[];
 for(const e of leads){
  if(e.has_linked_draft)continue; // Show the newer submitted version, not its original.
  const attrs=String(e.dates_text||'').split('|');
  const isAdminTest=attrs[0]==='PRUEBA_ADMIN';
  const plan=['local','zona','insular'].includes(attrs[1])?attrs[1]:'';
  const status=['submitted','changes_requested','approved_for_payment','rejected'].includes(e.review_status)
   ?e.review_status:'interest';
  const cost=Number(attrs[2]);
  const hasCost=plan&&Number.isFinite(cost)&&cost>=0;
  result.push({
   key:'lead-'+Number(e.id),source:'lead',id:Number(e.id),
   company:(isAdminTest?'[PRUEBA] ':'')+(e.company||''),title:e.campaign_name||'Consulta comercial',
   submitted_at:e.created_at,status,payment:e.payment_status||'unavailable',
   days:Number(e.campaign_days)||null,plan,kind:e.format==='event'?'Evento patrocinado':'Banner',
   area:e.municipality||'',price:hasCost?cost:null,
   has_image:!!e.has_image,image_url:e.has_image?'/api/admin?op=leadimage&id='+Number(e.id):'',
   description:e.banner_text||e.message||'',review_note:e.review_note||'',
   contact:e.contact_name||'',email:e.email||'',telephone:e.telephone||'',
   destination:e.action_url||'',start:e.campaign_start,
   event_start:e.event_start,event_venue:e.event_venue,
   actual_starts_at:null,actual_ends_at:null,
   editable:['submitted','changes_requested'].includes(status)
  });
 }
 for(const d of opsDrafts){
  const id=Number(d.id),end=opsDate(d.actual_ends_at);
  const status=d.status==='active'&&end&&end<today?'finished':d.status;
  result.push({
   key:'draft-'+id,source:'draft',id,company:d.account_company||d.advertiser||'',
   title:d.title||'Sin título',submitted_at:d.created_at||d.updated_at,
   status,payment:d.payment_status||'unavailable',days:Number(d.days)||null,
   plan:d.plan||'',kind:d.placement==='evento'?'Evento patrocinado':'Banner',
   area:Array.isArray(d.municipalities)&&d.municipalities.length?d.municipalities.join(', '):'Toda Gran Canaria',
   price:Number.isFinite(Number(d.price_cents))?Number(d.price_cents)/100:null,
   has_image:!!d.has_image,
   image_url:d.has_image?'/api/admin?op=advertiser-draft-image&id='+id:'',
   description:d.description||'',review_note:d.review_note||'',
   contact:'',email:'',telephone:'',destination:d.destination||'',
   start:d.campaign_start,event_start:d.event_start,event_venue:d.event_venue,
   actual_starts_at:d.actual_starts_at,actual_ends_at:d.actual_ends_at,
   editable:['submitted','changes_requested'].includes(status)
  });
 }
 for(const a of ads){
  if(a.kind!=='paid')continue;
  const started=opsDate(a.starts_at),ended=opsDate(a.ends_at);
  const status=ended&&ended<today?'finished':a.enabled&&(!started||started<=today)?'active':'draft';
  result.push({
   key:'published-'+String(a.id),source:'published',id:String(a.id),
   company:a.advertiser||'',title:a.headline||'Campaña publicitaria',submitted_at:a.updated_at,
   status,payment:'unavailable',days:started&&ended?
   Math.round((Date.parse(ended+'T00:00:00Z')-Date.parse(started+'T00:00:00Z'))/86400000)+1:null,
   plan:'',kind:'Banner',area:Array.isArray(a.municipalities)&&a.municipalities.length?a.municipalities.join(', '):'Toda Gran Canaria',
   price:null,has_image:!!a.has_uploaded_image,image_url:a.has_uploaded_image?
    '/api/admin?op=adimage&id='+encodeURIComponent(a.id):'',
   description:a.description||'',review_note:'',contact:'',email:'',telephone:'',
   destination:a.button_url||'',start:started,event_start:null,event_venue:null,
   actual_starts_at:started,actual_ends_at:ended,editable:false
  });
 }
 return result.sort((a,b)=>String(b.submitted_at||'').localeCompare(String(a.submitted_at||'')));
}
function opsFilteredRows(){
 return opsAllRows.filter(r=>{
  const search=opsSearch;
  if(search&&!([r.company,r.title,r.area,r.id].join(' ').toLowerCase().includes(search)))return false;
  return opsFilter==='all'||(opsFilter==='paid'?r.payment==='paid':r.status===opsFilter);
 });
}
function renderAdOperations(){
 const container=$('adOpsRows');if(!container)return;
 opsAllRows=normalizedOpsRows();
 const countOf=status=>opsAllRows.filter(r=>r.status===status).length;
 $('adOpsInterested').textContent=String(countOf('interest'));
 $('adOpsPending').textContent=String(countOf('submitted')+countOf('paid_review'));
 $('adOpsActive').textContent=String(countOf('active'));
 $('adOpsFinished').textContent=String(countOf('finished'));
 const rows=opsFilteredRows();
 $('adOpsCount').textContent=rows.length+' campañas visibles · '+opsAllRows.length+' registradas';
 if(!rows.length){
  container.innerHTML='<tr><td colspan="9">No hay campañas que coincidan con este filtro.</td></tr>';
  return;
 }
 container.innerHTML=rows.map(r=>{
  const status=opsStateNames[r.status]||r.status;
  const payment=r.payment==='paid'?'Pagado':r.payment==='pending'?'Pendiente':
    r.payment==='refunded'?'Reembolsado':'No verificado';
  const days=Number.isInteger(r.days)&&r.days>0?r.days+' días':'—';
  const amount=r.price===null?'—':Number(r.price).toLocaleString('es-ES',{minimumFractionDigits:0,maximumFractionDigits:2})+' €';
  const img=r.has_image&&r.image_url?'<img class="adops-thumb" loading="lazy" src="'+escape(r.image_url)+'" alt="Anuncio de '+escape(r.company)+'">':'';
  const area=r.plan?opsPlanNames[r.plan]+' · '+r.area:r.area;
  return '<tr><td><strong>'+escape(r.company)+'</strong><small>'+escape(r.title)+'</small></td>'+
   '<td>'+escape(opsDate(r.submitted_at)||'—')+'<small>#'+escape(String(r.id))+'</small></td>'+
   '<td><span class="adops-status st-'+escape(r.status)+'">'+escape(status)+'</span></td>'+
   '<td><span class="adops-payment p-'+escape(r.payment)+'">'+escape(payment)+'</span></td>'+
   '<td>'+escape(days)+(r.status==='active'&&r.actual_ends_at?
    '<small>'+escape(daysLeft(r.actual_ends_at))+'</small>':'')+'</td>'+
   '<td>'+escape(r.kind)+'<small>'+escape(area||'Sin cobertura')+'</small></td>'+
   '<td><strong>'+escape(amount)+'</strong></td>'+
   '<td><div class="adops-visual">'+img+
     '<button type="button" data-ops-preview="'+escape(r.key)+'">Ver anuncio</button></div></td>'+
   '<td><div class="adops-actions">'+
    '<button type="button" class="ghost mini" data-ops-preview="'+escape(r.key)+'">'+
      (r.editable?'Revisar':'Detalles')+'</button>'+
    (r.source==='lead'&&r.status==='changes_requested'?
     '<button type="button" class="ghost mini" data-ops-invite="'+Number(r.id)+'">Dar acceso</button>':'')+
    '</div></td></tr>';
 }).join('');
}
function opsOpenPreview(row){
 const url=/^https:\/\//i.test(row.destination)?row.destination:'';
 const image=row.has_image&&row.image_url?
  '<div class="adops-preview-card"><img src="'+escape(row.image_url)+'" alt="Vista de la creatividad presentada"></div>':
  '<p class="notice">Esta solicitud no tiene imagen registrada.</p>';
 const area=(row.plan?opsPlanNames[row.plan]+' · ':'')+row.area;
 const money=row.price===null?'Sin importe calculado':row.price+' €';
 const details='<div class="sheet-head"><div><span class="eyebrow">Publicidad · Solicitud #'+escape(String(row.id))+'</span>'+
  '<h2 id="dialogTitle">'+escape(row.company)+'</h2></div><button type="button" class="ghost mini" data-close>✕</button></div>'+
  '<p><strong>'+escape(row.title)+'</strong></p>'+
  '<div class="meta"><span class="adops-status st-'+escape(row.status)+'">'+
  escape(opsStateNames[row.status]||row.status)+'</span> '+
  '<span class="adops-payment p-'+escape(row.payment)+'">'+
  escape(row.payment==='paid'?'Pago confirmado':row.payment==='pending'?'Pago pendiente':'Pago sin verificar')+'</span></div>'+
  image+
  '<div class="adops-preview-card"><p><strong>Descripción:</strong> '+escape(row.description)+'</p>'+
  '<p><strong>Formato:</strong> '+escape(row.kind)+' · <strong>Zona:</strong> '+escape(area)+'</p>'+
  '<p><strong>Duración:</strong> '+escape(row.days||'—')+' días · <strong>Tarifa:</strong> '+escape(money)+'</p>'+
  '<p><strong>Inicio solicitado:</strong> '+escape(opsDate(row.start)||'Sin fecha')+'</p>'+
  (row.event_start?'<p><strong>Evento:</strong> '+escape(row.event_start)+' · '+escape(row.event_venue)+'</p>':'')+
  (row.email?'<p><strong>Contacto:</strong> '+escape(row.contact)+' · '+escape(row.email)+
    (row.telephone?' · '+escape(row.telephone):'')+'</p>':'')+
  (url?'<p><a href="'+escape(url)+'" target="_blank" rel="noopener noreferrer">Consultar página del anunciante</a></p>':'')+
  '</div>'+
  (row.review_note?'<p class="notice"><strong>Observaciones anteriores:</strong> '+escape(row.review_note)+'</p>':'')+
  '<div class="sheet-footer">'+
  (row.editable&&row.has_image?'<button type="button" class="primary" data-ops-review="approved_for_payment" data-ops-key="'+escape(row.key)+'">Aprobar contenido</button>':'')+
  (row.editable?'<button type="button" class="ghost" data-ops-review="changes_requested" data-ops-key="'+escape(row.key)+'">Pedir cambios</button>'+
  '<button type="button" class="ghost" data-ops-review="rejected" data-ops-key="'+escape(row.key)+'">Rechazar</button>':'')+
  (row.source==='lead'?'<button type="button" class="ghost" data-ops-invite="'+Number(row.id)+'">Generar acceso privado</button>':'')+
  '<button type="button" class="ghost" data-close>Cerrar</button></div>'+
  '<p class="muted small">Aprobar contenido no genera un cobro ni publica nada. El enlace de pago se habilitará únicamente cuando la pasarela esté configurada.</p>';
 openDialog(details);
}
$('adOpsSearch').addEventListener('input',event=>{
 opsSearch=String(event.target.value||'').trim().toLowerCase();renderAdOperations();
});
$('adOpsFilter').addEventListener('change',event=>{
 opsFilter=event.target.value;renderAdOperations();
});
$('refreshAdOperations').onclick=async()=>{
 await Promise.allSettled([loadLeads(),loadAdvertiserDrafts(),loadAds(),loadPromotions()]);
 message('Tabla de publicidad actualizada');
};
$('adOpsRows').addEventListener('click',event=>{
 const button=event.target.closest('[data-ops-preview],[data-ops-invite]');if(!button)return;
 if(button.dataset.opsInvite){
  createAdvertiserInvite(Number(button.dataset.opsInvite)).then(async()=>{
    await Promise.allSettled([loadLeads(),loadAdvertiserDrafts()]);
  }).catch(err=>message(err.message));
  return;
 }
 const row=opsAllRows.find(r=>r.key===button.dataset.opsPreview);
 if(row)opsOpenPreview(row);
});
$('adOpsExport').onclick=()=>{
 const columns=['Empresa','Anuncio','Fecha solicitud','Estado','Pago','Dias','Formato','Cobertura','Importe'];
 const cell=value=>{
  let textValue=String(value??'').replace(/[\r\n\t]+/g,' ');
  if(/^[\s]*[=+\-@]/.test(textValue))textValue="'"+textValue;
  return '"'+textValue.replace(/"/g,'""')+'"';
 };
 const lines=[columns,...opsFilteredRows().map(r=>[
  r.company,r.title,opsDate(r.submitted_at),opsStateNames[r.status]||r.status,
  r.payment==='paid'?'Pagado':r.payment==='pending'?'Pendiente':'Sin confirmar',
  r.days||'',r.kind,(r.plan?opsPlanNames[r.plan]+' · ':'')+r.area,r.price??''
 ])];
 const csv='\ufeff'+lines.map(row=>row.map(cell).join(';')).join('\r\n');
 const object=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=object;a.download='dparranda-publicidad.csv';a.click();
 setTimeout(()=>URL.revokeObjectURL(object),500);
};
$('sheet').addEventListener('click',async event=>{
 const button=event.target.closest('[data-ops-review],[data-ops-invite]');if(!button)return;
 if(button.dataset.opsInvite){
  const id=Number(button.dataset.opsInvite);
  try{await createAdvertiserInvite(id);await Promise.allSettled([loadLeads(),loadAdvertiserDrafts()])}
  catch(err){message(err.message)}
  return;
 }
 const row=opsAllRows.find(x=>x.key===button.dataset.opsKey);
 if(!row)return;
 const state=button.dataset.opsReview;
 if(state==='approved_for_payment'&&!confirm('¿Has revisado la imagen, texto, fechas y condiciones? Solo se aprobará el contenido. El pago continuará deshabilitado.'))return;
 let note='';
 if(state!=='approved_for_payment'){
  const answer=prompt(state==='changes_requested'?'¿Qué debe corregir el anunciante?':'Motivo del rechazo:');
  if(answer===null)return;
  note=answer.trim();
  if(!note){message('Debes indicar el motivo');return}
 }
 button.disabled=true;
 try{
  const result=await api(row.source==='lead'?'enquiry-review':'advertiser-review',
   {id:row.id,status:state,note});
  closeDialog();
  await Promise.allSettled([loadLeads(),loadAdvertiserDrafts()]);
  message(result.message||'Revisión guardada. Ningún pago ni publicación automática.');
 }catch(err){message(err.message);button.disabled=false}
});
initialize();
})();