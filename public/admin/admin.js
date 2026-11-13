(()=>{'use strict';
const $=id=>document.getElementById(id), apiUrl='/api/admin';
let events=[], ads=[], leads=[], promotions=[], opsDrafts=[], advertisingArchives=[], invoiceReviews=[], pagination=0, filter='all', search='', section='events', current=null, toastTimer;
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
 button.disabled=false;
 button.dataset.ready='false';
 button.textContent='Comprobar configuración';
 try{
  const info=await api('resend-test-config');
  if(info.ready===true){
   status.textContent='Resend listo para pruebas. El correo se enviará únicamente a la dirección registrada en tu cuenta Resend, no a anunciantes.';
   button.dataset.ready='true';
   button.textContent='Enviar correo de prueba';
  }else{
   const missing=[];
   if(info.api_key_status==='missing')missing.push('falta RESEND_API_KEY');
   else if(info.api_key_status==='invalid_format')missing.push('RESEND_API_KEY no tiene el formato de una clave Resend');
   if(info.test_recipient_status==='missing')missing.push('falta RESEND_TEST_RECIPIENT');
   else if(info.test_recipient_status==='invalid_format')missing.push('RESEND_TEST_RECIPIENT no es un correo válido');
   const problem=missing.join('; ')||'la configuración aún no está disponible';
   status.textContent='Resend pendiente: '+problem+'. Comprueba que ambas variables estén en Production y haz Redeploy tras guardarlas. No compartas la API key.';
  }
 }catch(err){
  status.textContent='No se pudo comprobar Resend: '+err.message+'. Comprueba que tienes una sesión de administrador activa.';
 }
}
$('sendResendTest').addEventListener('click',async()=>{
 const button=$('sendResendTest'),status=$('resendTestInfo');
 if(button.dataset.ready!=='true'){
  await loadResendSandbox();
  if(button.dataset.ready==='true')message('Resend preparado. Ya puedes pulsar Enviar correo de prueba.');
  else message('Revisa el motivo indicado en el recuadro de Resend.');
  return;
 }
 if(!confirm('¿Enviar un único correo de prueba a tu propia cuenta de Resend? No se enviará nada a los anunciantes.'))return;
 button.disabled=true;status.textContent='Solicitando correo de prueba a Resend…';
 try{
  const result=await api('resend-send-test',{});
  status.textContent=result.message||'Resend ha aceptado el correo de prueba.';
  message('Prueba aceptada por Resend. Comprueba tu correo.');
 }catch(err){status.textContent=err.message;message('No se ha podido enviar la prueba')}
 finally{button.disabled=false}
});
async function loadPanel(){await Promise.allSettled([loadStats(),loadEvents(true),loadAds(),loadLeads(),loadPromotions(),loadAdvertiserAccounts(),loadAdvertiserDrafts(),loadAdvertisingIntake(),loadResendSandbox(),loadAdvertisingArchives(),loadInvoiceReviews()]);if(location.hash==='#publicidad')setSection('ads')}
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
function isArchived(source,id){return advertisingArchives.some(a=>a.source===source&&a.record_id===String(id))}
async function loadInvoiceReviews(){
 const node=$('invoiceReviewsList');if(!node)return;
 try{
  const result=await api('invoice-reviews');invoiceReviews=result.invoices||[];
  renderInvoiceReviews();
 }catch(err){node.innerHTML='<p class="muted">No se pudo consultar facturación: '+escape(err.message)+'</p>'}
}
function renderInvoiceReviews(){
 const node=$('invoiceReviewsList');if(!node)return;
 if(!invoiceReviews.length){node.innerHTML='<p class="muted">Todavía no hay pagos confirmados pendientes de facturación.</p>';return}
 node.innerHTML=invoiceReviews.map(r=>{
  const id=Number(r.draft_id),pending=r.review_status!=='checked';
  const amount=(Number(r.total_cents||0)/100).toLocaleString('es-ES',{style:'currency',currency:'EUR'});
  return '<article class="invoice-review-item">'+
   '<div><strong>'+escape(r.company_name||r.title||'Anunciante')+'</strong><p>'+escape(r.title||'Campaña')+' · '+escape(amount)+
   ' · Pago Stripe verificado</p><p>'+ (pending?'Pendiente de revisar los datos':'Datos revisados · falta habilitar emisión fiscal')+'</p></div>'+
   '<div class="actions"><a class="invoice-preview-link" target="_blank" rel="noopener noreferrer" href="/api/admin?op=invoice-review-preview&id='+id+
   '">Ver borrador</a><button type="button" class="ghost mini" data-invoice-edit="'+id+'">Revisar datos</button></div>'+
   '</article>';
 }).join('');
}
function openInvoiceReview(row){
 const props=[
  ['company_name','Razón social o nombre fiscal'],
  ['customer_tax_id','NIF / CIF'],
  ['billing_address','Dirección fiscal'],
  ['billing_postal','Código postal'],
  ['billing_city','Localidad'],
  ['billing_region','Provincia / región'],
  ['billing_country','País'],
  ['billing_email','Correo de facturación'],
  ['internal_note','Nota interna para la revisión']
 ];
 const fields=props.map(([name,label])=>
  '<label class="'+(['company_name','billing_address','billing_email','internal_note'].includes(name)?'full':'')+'">'+
  escape(label)+(name==='internal_note'?
  '<textarea name="'+name+'" maxlength="700" rows="2">'+escape(row[name]||'')+'</textarea>':
  '<input name="'+name+'" maxlength="'+(name==='company_name'?180:name==='billing_address'?220:name==='billing_email'?180:110)+'" value="'+escape(row[name]||'')+'">')+'</label>').join('');
 openDialog('<div class="sheet-head"><div><span class="eyebrow">FACTURACIÓN · DOCUMENTO NO EMITIDO</span>'+
  '<h2 id="dialogTitle">Revisar datos fiscales</h2></div><button type="button" class="ghost mini" data-close>✕</button></div>'+
  '<p class="notice">El pago de '+escape((Number(row.total_cents)/100).toLocaleString('es-ES',{style:'currency',currency:'EUR'}))+
  ' está confirmado. Todavía NO hay factura ni envío automático. Comprueba todos los datos fiscales antes de marcar como revisada.</p>'+
  '<p><a target="_blank" rel="noopener noreferrer" href="/api/admin?op=invoice-review-preview&id='+Number(row.draft_id)+'">Abrir vista previa del documento</a></p>'+
  '<form id="invoiceReviewForm" data-invoice-id="'+Number(row.draft_id)+'"><div class="invoice-review-form">'+fields+'</div>'+
  '<div class="sheet-footer"><button type="submit" class="ghost" value="save">Guardar borrador</button>'+
  '<button type="submit" class="primary" value="check">Marcar datos revisados</button>'+
  '<button type="button" class="ghost" data-close>Cerrar</button></div></form>');
}
$('invoiceReviewsList').addEventListener('click',event=>{
 const button=event.target.closest('[data-invoice-edit]');if(!button)return;
 const row=invoiceReviews.find(r=>Number(r.draft_id)===Number(button.dataset.invoiceEdit));
 if(row)openInvoiceReview(row);
});
$('refreshInvoiceReviews').addEventListener('click',loadInvoiceReviews);
$('sheet').addEventListener('submit',async event=>{
 if(event.target.id!=='invoiceReviewForm')return;
 event.preventDefault();
 const form=event.target,id=Number(form.dataset.invoiceId);
 const action=event.submitter?.value==='check'?'check':'save';
 const data=Object.fromEntries(new FormData(form).entries());
 form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=true);
 try{
  const result=await api('invoice-review-update',{id,action,...data});
  await loadInvoiceReviews();closeDialog();message(result.message||'Datos guardados');
 }catch(err){
  message(err.message);form.querySelectorAll('button[type=submit]').forEach(b=>b.disabled=false);
 }
});
async function loadAdvertisingArchives(){
 try{const data=await api('advertising-archives');advertisingArchives=data.archives||[];
  renderAdOperations();renderAds();renderLeads();}
 catch(err){message('No se pudo cargar la papelera: '+err.message)}
}
async function loadAds() {
 $('adsList').innerHTML='<div class="empty">Cargando campañas…</div>';
 try{const response=await api('ads');ads=response.ads||[];renderAds();renderAdOperations()}
 catch(e){$('adsList').innerHTML='<div class="empty">'+escape(e.message)+'</div>'}
}
function renderAds(){
 const visibleAds=ads.filter(a=>!isArchived(a.kind==='house'?'house':'published',a.id));
 if(!visibleAds.length){$('adsList').innerHTML='<div class="empty">Todavía no hay campañas publicitarias.</div>';return}
 $('adsList').innerHTML=visibleAds.map(a=>{
  const preview=a.has_uploaded_image?'/api/admin?op=adimage&id='+encodeURIComponent(a.id):
    a.enquiry_id?'/api/admin?op=leadimage&id='+Number(a.enquiry_id):a.image;
  const image=/^\/sponsors\/[a-z0-9._/-]+\.(webp|png|jpeg|jpg)$/i.test(preview||'')||/^\/api\/admin\?op=(leadimage&id=[0-9]+|adimage&id=[a-zA-Z0-9_-]+)$/.test(preview)?
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
$('createOwnAd').onclick=()=>editAd(null);
function editAd(ad){
 if(ad&&ad.kind!=='house'){message('Esta opción es para gestionar publicidad propia sin coste.');return}
 if(!ad)ad={enabled:false,kind:'house',permanent:false,municipalities:[],advertiser:'AriMar'};
 const dates=v=>typeof v==='string'?v.slice(0,10):'';
 const today=opsToday(),defaultEnd=new Date(Date.parse(today+'T12:00:00Z')+29*86400000).toISOString().slice(0,10);
 const startDefault=dates(ad.starts_at)||today,endDefault=dates(ad.ends_at)||defaultEnd;
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
 field('starts_at','Inicio',startDefault,'',false,'date')+
 field('ends_at','Finalización',endDefault,'',false,'date')+
 field('municipalities','Municipios (separados por coma; vacío = toda la isla)',(ad.municipalities||[]).join(', '),'Agüimes, Ingenio',true)+
 '<input type="hidden" name="kind" id="f-kind" value="house"></div>'+
 '<label class="checkbox"><input type="checkbox" id="f-enabled" '+(ad.enabled?'checked':'')+'>Campaña activa</label>'+
 '<div class="field"><label for="f-newImage">Cartel publicitario (JPG, PNG o WebP, opcional)</label><input id="f-newImage" type="file" accept="image/jpeg,image/png,image/webp"><small class="muted">Se prepara a 1200 × 675. Si no subes ninguno, se conserva la imagen que ya tengas.</small></div>'+
 '<p class="notice">Publicidad propia gratuita · Sin Stripe. Cada campaña se puede activar, pausar y modificar por separado. Duración de 1 a 60 días; al editar un anuncio antiguo permanente, se aplicarán las fechas que elijas.</p>'+
 '<div class="sheet-footer"><button type="button" class="ghost" data-close>Cancelar</button><button class="primary" type="submit">Guardar campaña</button></div></form>';
 openDialog(content);
 $('adForm').onsubmit=async ev=>{
  ev.preventDefault();const b=ev.submitter||$('adForm').querySelector('[type=submit]');b.disabled=true;
  const f=Object.fromEntries(new FormData(ev.currentTarget).entries());
  f.id=ad.id||undefined;f.enabled=$('f-enabled').checked;f.permanent=false;f.kind='house';
  f.municipalities=String(f.municipalities||'').split(',').map(x=>x.trim()).filter(Boolean);
  f.starts_at=f.starts_at||null;f.ends_at=f.ends_at||null;
  try{
   const file=$('f-newImage').files?.[0];
   if(file){
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>15_000_000)
     throw new Error('Selecciona una imagen JPG, PNG o WebP de menos de 15 MB');
    const bitmap=await createImageBitmap(file);
    const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=675;
    const ctx=canvas.getContext('2d');
    if(!ctx)throw new Error('No se pudo preparar la imagen');
    const scale=Math.max(1200/bitmap.width,675/bitmap.height);
    ctx.drawImage(bitmap,(1200-bitmap.width*scale)/2,(675-bitmap.height*scale)/2,
      bitmap.width*scale,bitmap.height*scale);bitmap.close?.();
    let encoded='';
    for(const q of [.84,.7,.54,.4]){
     encoded=canvas.toDataURL('image/webp',q);
     if(encoded.startsWith('data:image/webp;base64,')&&encoded.length*3/4<=800000)break;
    }
    if(!encoded.startsWith('data:image/webp;base64,')||encoded.length*3/4>800000)
     throw new Error('La imagen no se ha podido optimizar a menos de 800 KB');
    f.image_data=encoded;f.image_width=1200;f.image_height=675;f.image='';
   }
   await api('ad',f);closeDialog();message('Campaña propia guardada, sin coste');
   await Promise.allSettled([loadAds(),loadStats()]);
  }catch(err){message(err.message);b.disabled=false}
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
 try{const data=await api('leads');leads=data.leads||[];renderLeads();renderAdOperations();const pending=leads.filter(l=>!isArchived('lead',l.id)&&l.status==='new'&&String(l.dates_text||'').startsWith('INTERES_INICIAL|')).length;$('tabAds').textContent='Publicidad'+(pending?' · '+pending+' interesados':'')}
 catch(e){list.innerHTML='<div class="empty">'+escape(e.message)+'</div>'}
}
function renderLeads(){
 const visibleLeads=leads.filter(l=>!isArchived('lead',l.id)&&!isArchived('draft',opsDrafts.find(d=>Number(d.source_lead_id)===Number(l.id))?.id));
 if(!visibleLeads.length){$('leadsList').innerHTML='<div class="empty">No hay solicitudes comerciales registradas.</div>';return}
 $('leadsList').innerHTML=visibleLeads.map(l=>{
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
  const visibleDrafts=drafts.filter(d=>!isArchived('draft',d.id));
  if(!visibleDrafts.length){root.innerHTML='<div class="empty">Ningún anunciante ha creado campañas todavía.</div>';return}
  root.innerHTML=visibleDrafts.map(d=>{
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
 approved:'Aprobado',scheduled:'Programado',active:'Activo',paused:'Pausado',finished:'Caducado',
 rejected:'Rechazado',cancelled:'Cancelado'
};
const opsPlanNames={local:'Local',zona:'Zona',insular:'Insular'};
let opsSearch='',opsFilter='all',opsAllRows=[];
function opsArchiveAction(row){
 if(row.archived)return '<button class="ghost mini adops-restore-btn" type="button" data-ops-restore="'+escape(row.key)+'">Restaurar</button>';
 if(row.source==='house'&&row.id==='arimar-fundador')return '';
 return '<button class="ghost mini adops-archive-btn" type="button" data-ops-archive="'+escape(row.key)+'">'+
  (row.payment==='paid'?'Archivar':'Quitar del panel')+'</button>';
}
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
   event_start:e.event_start,event_town:e.event_municipality,event_venue:e.event_venue,
   actual_starts_at:null,actual_ends_at:null,
   editable:['submitted','changes_requested'].includes(status)
  });
 }
 for(const d of opsDrafts){
  const id=Number(d.id),end=opsDate(d.actual_ends_at);
  const start=opsDate(d.actual_starts_at);
  const status=d.status==='active'&&end&&end<today?'finished':
   d.status==='active'&&d.published_enabled===false?'paused':
   d.status==='active'&&start&&start>today?'scheduled':d.status;
  result.push({
   key:'draft-'+id,source:'draft',id,company:d.account_company||d.advertiser||'',
   title:d.title||'Sin título',submitted_at:d.created_at||d.updated_at,
   status,payment:d.payment_status||'unavailable',days:Number(d.days)||null,
   plan:d.plan||'',kind:d.placement==='evento'?'Evento patrocinado':'Banner',
   area:Array.isArray(d.municipalities)&&d.municipalities.length?d.municipalities.join(', '):'Toda Gran Canaria',
   price:Number.isFinite(Number(d.price_cents))?Number(d.price_cents)/100:null,
   has_image:!!d.has_image,
   image_url:d.has_image?'/api/admin?op=advertiser-draft-image&id='+id:'',
    description:d.description||'',image_alt:d.image_alt||'',review_note:d.review_note||'',
   contact:d.account_contact||'',email:d.account_email||'',telephone:'',destination:d.destination||'',
   start:d.campaign_start,event_start:d.event_start,event_town:d.event_town,event_venue:d.event_venue,
   actual_starts_at:d.actual_starts_at,actual_ends_at:d.actual_ends_at,
   editable:['submitted','changes_requested'].includes(status)
  });
 }
 for(const a of ads){
  if(a.kind==='house'){
   const started=opsDate(a.starts_at),ended=opsDate(a.ends_at);
   const status=ended&&ended<today?'finished':!a.enabled?'paused':started&&started>today?'scheduled':'active';
   const duration=started&&ended?Math.round(
    (Date.parse(ended+'T00:00:00Z')-Date.parse(started+'T00:00:00Z'))/86400000)+1:null;
   const staticImage=typeof a.image==='string'&&/^\/sponsors\/[a-z0-9._/-]+\.(webp|jpg|jpeg|png)$/i.test(a.image)?a.image:'';
   result.push({
    key:'house-'+String(a.id),source:'house',id:String(a.id),
    company:a.advertiser||'AriMar',title:a.headline||'Campaña propia',submitted_at:a.updated_at,
    status,payment:'free',days:duration,permanent:!!a.permanent,
    plan:'',kind:'Publicidad propia',area:Array.isArray(a.municipalities)&&a.municipalities.length?
     a.municipalities.join(', '):'Toda Gran Canaria',
    price:0,has_image:!!a.has_uploaded_image||!!staticImage,
    image_url:a.has_uploaded_image?'/api/admin?op=adimage&id='+encodeURIComponent(a.id):staticImage,
    description:a.description||'',review_note:'',contact:'',email:'',telephone:'',
    destination:a.button_url||'',start:started,event_start:null,event_venue:null,
    actual_starts_at:started,actual_ends_at:ended,editable:false
   });
   continue;
  }
  if(a.kind!=='paid')continue;
  if(opsDrafts.some(d=>d.published_ad_id===a.id))continue; // Shown via linked paid draft.
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
 for(const row of result)row.archived=isArchived(row.source,row.id);
 return result.sort((a,b)=>String(b.submitted_at||'').localeCompare(String(a.submitted_at||'')));
}
function opsFilteredRows(){
 return opsAllRows.filter(r=>{
  const search=opsSearch;
  if(opsFilter==='archived'){if(!r.archived)return false}
  else if(r.archived)return false;
  if(search&&!([r.company,r.title,r.area,r.id].join(' ').toLowerCase().includes(search)))return false;
  return opsFilter==='archived'||opsFilter==='all'||(opsFilter==='paid'?r.payment==='paid':r.status===opsFilter);
 });
}
function renderAdOperations(){
 const container=$('adOpsRows');if(!container)return;
 opsAllRows=normalizedOpsRows();
 const countOf=status=>opsAllRows.filter(r=>!r.archived&&r.status===status).length;
 $('adOpsInterested').textContent=String(countOf('interest'));
 $('adOpsPending').textContent=String(countOf('submitted')+countOf('paid_review'));
 $('adOpsActive').textContent=String(countOf('active'));
 $('adOpsFinished').textContent=String(countOf('finished'));
 const rows=opsFilteredRows();
 $('adOpsCount').textContent=rows.length+' visibles · '+opsAllRows.filter(r=>!r.archived).length+' en gestión · '+opsAllRows.filter(r=>r.archived).length+' archivadas';
 if(!rows.length){
  container.innerHTML='<tr><td colspan="9">No hay campañas que coincidan con este filtro.</td></tr>';
  return;
 }
 container.innerHTML=rows.map(r=>{
  const status=r.archived?'Archivado':opsStateNames[r.status]||r.status;
  const payment=r.payment==='paid'?'Pagado':r.payment==='pending'?'Pendiente':
    r.payment==='free'?'Sin coste':r.payment==='refunded'?'Reembolsado':'No verificado';
  const days=r.permanent?'Anterior permanente':Number.isInteger(r.days)&&r.days>0?r.days+' días':'—';
  const amount=r.price===null?'—':Number(r.price).toLocaleString('es-ES',{minimumFractionDigits:0,maximumFractionDigits:2})+' €';
  const img=r.has_image&&r.image_url?'<img class="adops-thumb" loading="lazy" src="'+escape(r.image_url)+'" alt="Anuncio de '+escape(r.company)+'">':'';
  const area=r.plan?opsPlanNames[r.plan]+' · '+r.area:r.area;
  return '<tr><td><strong>'+escape(r.company)+'</strong><small>'+escape(r.title)+'</small></td>'+
   '<td>'+escape(opsDate(r.submitted_at)||'—')+'<small>#'+escape(String(r.id))+'</small></td>'+
   '<td><span class="adops-status st-'+(r.archived?'archived':escape(r.status))+'">'+escape(status)+'</span></td>'+
   '<td><span class="adops-payment p-'+escape(r.payment)+'">'+escape(payment)+'</span></td>'+
   '<td>'+escape(days)+(r.status==='active'&&r.actual_ends_at?
    '<small>'+escape(daysLeft(r.actual_ends_at))+'</small>':'')+'</td>'+
   '<td>'+escape(r.kind)+'<small>'+escape(area||'Sin cobertura')+'</small></td>'+
   '<td><strong>'+escape(amount)+'</strong></td>'+
   '<td><div class="adops-visual">'+img+
     '<button type="button" data-ops-preview="'+escape(r.key)+'">Ver anuncio</button></div></td>'+
   '<td><div class="adops-actions">'+
    (r.archived?opsArchiveAction(r):
    '<button type="button" class="ghost mini" data-ops-preview="'+escape(r.key)+'">'+
      (r.editable?'Revisar':'Detalles')+'</button>'+
    (r.source==='draft'&&r.payment==='paid'&&['active','scheduled','paused','approved','paid_review'].includes(r.status)?
      '<button type="button" class="ghost mini" data-ops-paid-edit="'+Number(r.id)+'">Editar anuncio</button>'+
      (['active','scheduled','paused'].includes(r.status)?
       '<button type="button" class="ghost mini" data-ops-paid-toggle="'+Number(r.id)+'" data-paid-enable="'+(r.status==='paused'?'true':'false')+'">'+
       (r.status==='paused'?'Activar':'Desactivar')+'</button>':''):'')+
    (r.source==='house'?'<button type="button" class="ghost mini" data-ops-house-edit="'+escape(r.id)+'">Editar</button>'+
    (r.status==='active'||r.status==='scheduled'?
      '<button type="button" class="ghost mini" data-ops-house-toggle="'+escape(r.id)+'" data-house-enable="false">Pausar</button>':
      '<button type="button" class="ghost mini" data-ops-house-toggle="'+escape(r.id)+'" data-house-enable="true">Activar</button>'):'')+
    (r.source==='lead'&&r.status==='changes_requested'?
     '<button type="button" class="ghost mini" data-ops-invite="'+Number(r.id)+'">Dar acceso</button>':'')+
    opsArchiveAction(r))+'</div></td></tr>';
 }).join('');
}
function opsOpenPreview(row){
 const url=/^https:\/\//i.test(row.destination)?row.destination:'';
 const image=row.has_image&&row.image_url?
  '<div class="adops-preview-card"><img src="'+escape(row.image_url)+'" alt="Vista de la creatividad presentada"></div>':
  '<p class="notice">Esta solicitud no tiene imagen registrada.</p>';
 const area=(row.plan?opsPlanNames[row.plan]+' · ':'')+row.area;
 const money=row.price===null?'Sin importe calculado':row.price+' €';
 const mockEvent=row.kind==='Evento patrocinado';
 const previewImage=row.has_image&&row.image_url?'<img src="'+escape(row.image_url)+'" alt="Cartel de '+escape(row.title)+'">':'';
 const previewCard='<div class="adops-live-outer"><p class="muted small">Vista previa de la tarjeta en D’Parranda. No implica publicación ni inicia la campaña.</p>'+
  '<article class="adops-live-card"><div class="adops-live-photo">'+previewImage+
  '<span class="adops-live-tag">'+(mockEvent?'Patrocinado · Ocio':'Publicidad')+'</span></div>'+
  '<div class="adops-live-content"><span class="adops-live-date">'+escape(mockEvent?String(row.event_start||'').slice(0,16).replace('T',' · '):'Publicidad')+'</span>'+
  '<h3>'+escape(row.title)+'</h3><p>'+escape(mockEvent?(row.event_venue||'')+' · '+(row.event_town||'Gran Canaria'):row.area)+'</p></div></article></div>';
 const details='<div class="sheet-head"><div><span class="eyebrow">Publicidad · Solicitud #'+escape(String(row.id))+'</span>'+
  '<h2 id="dialogTitle">'+escape(row.company)+'</h2></div><button type="button" class="ghost mini" data-close>✕</button></div>'+
  '<p><strong>'+escape(row.title)+'</strong></p>'+
  '<div class="meta"><span class="adops-status st-'+escape(row.status)+'">'+
  escape(row.archived?'Archivado':opsStateNames[row.status]||row.status)+'</span> '+
  '<span class="adops-payment p-'+escape(row.payment)+'">'+
  escape(row.payment==='paid'?'Pago confirmado':row.payment==='pending'?'Pago pendiente':row.payment==='free'?'Sin coste · campaña propia':'Pago sin verificar')+'</span></div>'+
  previewCard+image+
  '<div class="adops-preview-card"><p><strong>Descripción:</strong> '+escape(row.description)+'</p>'+
  '<p><strong>Formato:</strong> '+escape(row.kind)+' · <strong>Zona:</strong> '+escape(area)+'</p>'+
  '<p><strong>Duración:</strong> '+escape(row.permanent?'Anterior permanente':row.days?row.days+' días':'—')+' · <strong>Tarifa:</strong> '+escape(money)+'</p>'+
  '<p><strong>Inicio solicitado:</strong> '+escape(opsDate(row.start)||'Sin fecha')+'</p>'+
  (row.event_start?'<p><strong>Evento:</strong> '+escape(row.event_start)+' · '+escape(row.event_venue)+'</p>':'')+
  (row.email?'<p><strong>Contacto:</strong> '+escape(row.contact)+' · '+escape(row.email)+
    (row.telephone?' · '+escape(row.telephone):'')+'</p>':'')+
  (url?'<p><a href="'+escape(url)+'" target="_blank" rel="noopener noreferrer">Consultar página del anunciante</a></p>':'')+
  '</div>'+
  (row.review_note?'<p class="notice"><strong>Observaciones anteriores:</strong> '+escape(row.review_note)+'</p>':'')+
  '<div class="sheet-footer">'+
  (row.archived?opsArchiveAction(row):
  (row.editable&&row.has_image?'<button type="button" class="primary" data-ops-review="approved_for_payment" data-ops-key="'+escape(row.key)+'">Aprobar contenido</button>':'')+
  (row.editable?'<button type="button" class="ghost" data-ops-review="changes_requested" data-ops-key="'+escape(row.key)+'">Pedir cambios</button>'+
  '<button type="button" class="ghost" data-ops-review="rejected" data-ops-key="'+escape(row.key)+'">Rechazar</button>':'')+
  (row.source==='draft'&&row.payment==='paid'&&['active','scheduled','paused','approved','paid_review'].includes(row.status)?
     '<button type="button" class="primary" data-ops-paid-edit="'+Number(row.id)+'">Editar anuncio pagado</button>'+
     (['active','scheduled','paused'].includes(row.status)?
      '<button type="button" class="ghost" data-ops-paid-toggle="'+Number(row.id)+'" data-paid-enable="'+(row.status==='paused'?'true':'false')+'">'+
      (row.status==='paused'?'Activar anuncio':'Desactivar anuncio')+'</button>':''):'')+
   (row.source==='house'?'<button type="button" class="primary" data-ops-house-edit="'+escape(row.id)+'">Editar campaña propia</button>'+
    (row.status==='active'||row.status==='scheduled'?
      '<button type="button" class="ghost" data-ops-house-toggle="'+escape(row.id)+'" data-house-enable="false">Pausar</button>':
      '<button type="button" class="ghost" data-ops-house-toggle="'+escape(row.id)+'" data-house-enable="true">Activar</button>'):'')+
   (row.source==='draft'&&row.status==='paid_review'&&row.payment==='paid'?
    '<button type="button" class="primary" data-ops-schedule="'+Number(row.id)+'">Programar publicación</button>':'')+
   (row.source==='draft'&&['approved_for_payment','pending_payment'].includes(row.status)&&row.payment!=='paid'?
   '<button type="button" class="primary" data-ops-payment="'+Number(row.id)+'">Enviar / reenviar pago</button>':'')+
  (row.source==='lead'?'<button type="button" class="ghost" data-ops-invite="'+Number(row.id)+'">Generar acceso privado</button>':'')+
  opsArchiveAction(row))+'<button type="button" class="ghost" data-close>Cerrar</button></div>'+
  '<p class="muted small">'+(row.payment==='paid'&&row.status==='paid_review'?
  'Pago confirmado. Programar publicación respeta la fecha de inicio; si es futura, el anuncio no se mostrará al público hasta entonces.':
  'Al aprobar se generará el enlace Stripe y se intentará enviar por correo. El anuncio no se publica sin pago verificado.')+'</p>';
 openDialog(details);
}
$('adOpsSearch').addEventListener('input',event=>{
 opsSearch=String(event.target.value||'').trim().toLowerCase();renderAdOperations();
});
$('adOpsFilter').addEventListener('change',event=>{
 opsFilter=event.target.value;renderAdOperations();
});
$('refreshAdOperations').onclick=async()=>{
 await loadAdvertisingArchives();
 await Promise.allSettled([loadLeads(),loadAdvertiserDrafts(),loadAds(),loadPromotions()]);
 message('Tabla de publicidad actualizada');
};
async function optimizePaidCreativeFile(file){
 if(!file)return null;
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>15000000)
  throw new Error('Selecciona JPG, PNG o WebP de hasta 15 MB');
 const bitmap=await createImageBitmap(file);
 const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=675;
 const ctx=canvas.getContext('2d');
 if(!ctx){bitmap.close?.();throw new Error('No se pudo preparar la imagen')}
 const scale=Math.max(1200/bitmap.width,675/bitmap.height);
 ctx.drawImage(bitmap,(1200-bitmap.width*scale)/2,(675-bitmap.height*scale)/2,
  bitmap.width*scale,bitmap.height*scale);bitmap.close?.();
 let data='';
 for(const q of [.84,.7,.54,.4]){
  data=canvas.toDataURL('image/webp',q);
  if(data.startsWith('data:image/webp;base64,')&&data.length*3/4<=800000)break;
 }
 if(!data.startsWith('data:image/webp;base64,')||data.length*3/4>800000)
  throw new Error('El cartel no se pudo comprimir a menos de 800 KB');
 return {image_data:data,image_width:1200,image_height:675};
}
function openPaidCreativeEditor(row){
 if(row.source!=='draft'||row.payment!=='paid'||
   !['active','scheduled','paused','approved','paid_review'].includes(row.status))return;
 const isEvent=row.kind==='Evento patrocinado';
 const content='<div class="sheet-head"><div><span class="eyebrow">Publicidad contratada · Pago confirmado</span>'+
  '<h2 id="dialogTitle">Editar anuncio #'+row.id+'</h2></div>'+
  '<button type="button" class="ghost mini" data-close>✕</button></div>'+
  '<p class="notice">Puedes modificar cartel, título, descripción y enlace. Se conservan el pago de '+
  escape(String(row.price))+' €, la cobertura, el inicio y la duración de '+escape(String(row.days))+' días.</p>'+
  '<form id="paidCreativeForm"><div class="form-grid">'+
  field('title','Título',row.title||'','',true)+
  field('description','Descripción',row.description||'','',true,'textarea')+
  field('destination','Enlace HTTPS',row.destination||'','https://...',true,'url')+
  field('image_alt','Descripción accesible del cartel',row.image_alt||row.title||'','',true)+
  (isEvent?field('event_start','Fecha y hora del evento',row.event_start||'','',true,'datetime-local')+
   field('event_town','Municipio del evento',row.event_town||'','',true)+
   field('event_venue','Lugar del evento',row.event_venue||'','',true):'')+
  '</div><div class="field"><label for="paidCreativeImage">Nuevo cartel (opcional)</label>'+
  '<input id="paidCreativeImage" type="file" accept="image/jpeg,image/png,image/webp">'+
  '<small class="muted">Se prepara a 1200 × 675 en WebP. Sin archivo nuevo, se conserva el actual.</small></div>'+
  '<p class="muted small">No se genera otro pago ni se cambian las fechas publicitarias.</p>'+
  '<div class="sheet-footer"><button type="button" class="ghost" data-close>Cancelar</button>'+
  '<button type="submit" class="primary">Guardar cambios</button></div></form>';
 openDialog(content);
 const form=$('paidCreativeForm');
 form.onsubmit=async e=>{
  e.preventDefault();
  const button=e.submitter||form.querySelector('button[type=submit]');button.disabled=true;
  try{
   const body=Object.fromEntries(new FormData(form).entries());body.id=row.id;
   const asset=await optimizePaidCreativeFile($('paidCreativeImage').files?.[0]);
   if(asset)Object.assign(body,asset);
   await api('edit-paid-creative',body);
   closeDialog();
   await Promise.allSettled([loadAdvertiserDrafts(),loadPromotions(),loadAds()]);
   message('Anuncio actualizado sin modificar el pago ni los días contratados.');
  }catch(err){message(err.message);button.disabled=false}
 };
}
async function handlePaidCampaignAction(button){
 const id=Number(button.dataset.opsPaidToggle);
 const row=opsAllRows.find(r=>r.source==='draft'&&r.id===id&&r.payment==='paid');
 if(!row||!['active','scheduled','paused'].includes(row.status)){
  message('Solo se puede activar o desactivar un anuncio pagado y programado');return;
 }
 const enabled=button.dataset.paidEnable==='true';
 if(!confirm((enabled?'¿Activar':'¿Desactivar')+' el anuncio «'+row.title+'»?'+
   '\\n\\nNo se modifican las fechas ni el pago. Los días desactivados siguen dentro del periodo contratado.'))return;
 button.disabled=true;
 try{
  const result=await api('paid-ad-status',{id,enabled});
  closeDialog();
  await Promise.allSettled([loadAdvertiserDrafts(),loadPromotions(),loadAds()]);
  message(result.message||'Estado de publicación actualizado');
 }catch(e){message(e.message);button.disabled=false}
}
async function handleOwnCampaignAction(button){
 const id=button.dataset.opsHouseEdit||button.dataset.opsHouseToggle;
 const ad=ads.find(a=>a.kind==='house'&&a.id===id);
 if(!ad){message('No encontramos la campaña. Actualiza la lista.');return}
 if(button.dataset.opsHouseEdit){editAd(ad);return}
 const enabled=button.dataset.houseEnable==='true';
 if(!confirm((enabled?'¿Activar':'¿Pausar')+' la campaña «'+ad.headline+'»?'))return;
 button.disabled=true;
 try{
  await api('house-ad-status',{id,enabled});
  closeDialog();
  await Promise.allSettled([loadAds(),loadStats()]);
  message(enabled?'Campaña propia habilitada':'Campaña propia pausada');
 }catch(err){message(err.message);button.disabled=false}
}
async function handleAdvertisingArchiveAction(button){
 const key=button.dataset.opsArchive||button.dataset.opsRestore;
 const row=opsAllRows.find(r=>r.key===key);
 if(!row)return;
 const archiving=!!button.dataset.opsArchive, word=archiving?'ARCHIVAR':'RESTAURAR';
 const detail=row.payment==='paid'?
  'El pago y sus justificantes permanecerán guardados. ':
  'Podrás recuperar el registro desde Archivados. ';
 const caution=archiving?'Al retirarlo dejará de mostrarse públicamente. ':'Al recuperarlo no se reactivará automáticamente su publicación. ';
 const typed=prompt((archiving?'Quitar del panel':'Restaurar')+' «'+row.title+'»?\n\n'+detail+caution+
  '\n\nEscribe '+word+' para confirmar:');
 if(typed===null)return;
 if(typed.trim()!==word){message('Operación cancelada: escribe exactamente '+word);return}
 button.disabled=true;
 try{
  const result=await api('advertising-archive',{source:row.source,id:row.id,
   action:archiving?'archive':'restore',confirmation:word});
  await loadAdvertisingArchives();
  await Promise.allSettled([loadLeads(),loadAdvertiserDrafts(),loadAds(),loadPromotions(),loadStats()]);
  closeDialog();message(result.message||'Gestión de archivo realizada');
 }catch(err){message(err.message);button.disabled=false}
}
$('adOpsRows').addEventListener('click',event=>{
 const button=event.target.closest('[data-ops-preview],[data-ops-invite],[data-ops-house-edit],[data-ops-house-toggle],[data-ops-paid-edit],[data-ops-paid-toggle],[data-ops-archive],[data-ops-restore]');if(!button)return;
 if(button.dataset.opsArchive||button.dataset.opsRestore){handleAdvertisingArchiveAction(button);return}
 if(button.dataset.opsPaidEdit){const row=opsAllRows.find(r=>r.source==='draft'&&r.id===Number(button.dataset.opsPaidEdit));if(row)openPaidCreativeEditor(row);return}
 if(button.dataset.opsPaidToggle){handlePaidCampaignAction(button);return}
 if(button.dataset.opsHouseEdit||button.dataset.opsHouseToggle){handleOwnCampaignAction(button);return;}
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
  r.payment==='paid'?'Pagado':r.payment==='pending'?'Pendiente':r.payment==='free'?'Sin coste':'Sin confirmar',
  r.days||'',r.kind,(r.plan?opsPlanNames[r.plan]+' · ':'')+r.area,r.price??''
 ])];
 const csv='\ufeff'+lines.map(row=>row.map(cell).join(';')).join('\r\n');
 const object=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const a=document.createElement('a');a.href=object;a.download='dparranda-publicidad.csv';a.click();
 setTimeout(()=>URL.revokeObjectURL(object),500);
};
$('sheet').addEventListener('click',async event=>{
 const button=event.target.closest('[data-ops-review],[data-ops-invite],[data-ops-payment],[data-ops-schedule],[data-ops-house-edit],[data-ops-house-toggle],[data-ops-paid-edit],[data-ops-paid-toggle],[data-ops-archive],[data-ops-restore]');if(!button)return;
 if(button.dataset.opsArchive||button.dataset.opsRestore){await handleAdvertisingArchiveAction(button);return}
 if(button.dataset.opsPaidEdit){const row=opsAllRows.find(r=>r.source==='draft'&&r.id===Number(button.dataset.opsPaidEdit));if(row)openPaidCreativeEditor(row);return}
 if(button.dataset.opsPaidToggle){await handlePaidCampaignAction(button);return}
 if(button.dataset.opsHouseEdit||button.dataset.opsHouseToggle){await handleOwnCampaignAction(button);return;}
 if(button.dataset.opsSchedule){
  const row=opsAllRows.find(r=>r.source==='draft'&&r.id===Number(button.dataset.opsSchedule));
  if(!row||row.payment!=='paid'||row.status!=='paid_review')return;
  const start=opsDate(row.start),dates=start?' desde '+start:' según las fechas contratadas';
  if(!confirm('¿Programar el anuncio'+dates+'? Solo será visible en las fechas contratadas. No se modifica la fecha solicitada.'))return;
  button.disabled=true;
  try{
   const result=await api('schedule-paid-draft',{id:row.id});
   closeDialog();
   await Promise.allSettled([loadLeads(),loadAdvertiserDrafts(),loadPromotions(),loadAds()]);
   message('Anuncio programado del '+result.start+' al '+result.end+'. La vista pública respeta esas fechas.');
  }catch(err){message(err.message);button.disabled=false}
  return;
 }
 if(button.dataset.opsPayment){
  button.disabled=true;
  try{
   const result=await api('send-approved-payment',{id:Number(button.dataset.opsPayment)});
   await Promise.allSettled([loadLeads(),loadAdvertiserDrafts()]);
   closeDialog();message(result.message||'Enlace de pago preparado');
  }catch(err){message(err.message);button.disabled=false}
  return;
 }
 if(button.dataset.opsInvite){
  const id=Number(button.dataset.opsInvite);
  try{await createAdvertiserInvite(id);await Promise.allSettled([loadLeads(),loadAdvertiserDrafts()])}
  catch(err){message(err.message)}
  return;
 }
 const row=opsAllRows.find(x=>x.key===button.dataset.opsKey);
 if(!row)return;
 const state=button.dataset.opsReview;
 if(state==='approved_for_payment'&&!confirm('¿Has revisado imagen, texto, fechas y condiciones? Se intentará generar y enviar el enlace Stripe correspondiente. Ningún anuncio se publica sin confirmar el pago.'))return;
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