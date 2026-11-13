(()=>{'use strict';
const $=id=>document.getElementById(id);
const KEY='dp_ad_simulator_v1';
const STATUS=$('simStatus'),GRID=$('simFeed');
const daysSince=2*60*60*1000;
const categories={
 musica:'Música',familia:'Familia',gastronomia:'Gastronomía',
 cultura:'Cultura',deporte:'Deporte',naturaleza:'Naturaleza',
 ocio:'Ocio',otros:'Planes'
};
function el(tag,cl,text){
 const node=document.createElement(tag);
 if(cl)node.className=cl;
 if(text!==undefined)node.textContent=String(text);
 return node;
}
function addText(parent,tag,cl,value){
 const n=el(tag,cl,value);parent.append(n);return n;
}
function dateLabel(value){
 const s=String(value||'');
 const m=/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(s);
 if(!m)return 'Fecha por confirmar';
 return m[3]+'/'+m[2]+'/'+m[1]+(m[4]?' · '+m[4]+':'+m[5]:'');
}
function canDisplayImage(value,official){
 if(typeof value!=='string')return false;
 if(!official)return /^data:image\/webp;base64,[A-Za-z0-9+/=]+$/.test(value)&&value.length<1600000;
 if(/^\/api\/media\?id=[0-9]+$/.test(value))return true;
 if(/^\/sponsors\/[a-z0-9._/-]+\.(webp|jpg|jpeg|png)$/i.test(value))return true;
 try{
  const u=new URL(value,location.origin);
  return u.protocol==='https:'&&u.origin!==''&&u.href.length<1100;
 }catch{return false}
}
function eventCard(event, sponsored=false){
 const card=el('article','event-card');
 const photo=el('div','photo');
 const title=String(event.title||'Plan por descubrir');
 const url=event.image_url||'';
 const ok=canDisplayImage(url,!sponsored);
 if(ok){
  const img=el('img');
  img.src=url;img.loading='lazy';img.alt='Imagen del evento: '+title;
  img.referrerPolicy='strict-origin-when-cross-origin';
  img.addEventListener('error',()=>{img.remove();photo.prepend(el('span','fallback',title))},{once:true});
  photo.append(img);
 }else photo.append(el('span','fallback',title));
 const category=categories[event.category]||'Actividad';
 photo.append(el('span','photo-tag'+(sponsored?' sponsored':''),sponsored?'Patrocinado':category));
 const info=el('div','event-info');
 info.append(el('span','event-date-chip',dateLabel(event.start)));
 info.append(el('h3','event-title',title));
 const meta=el('div','event-meta');
 meta.append(el('span','', '⌖'));
 const where=el('div');
 addText(where,'strong','',event.venue||'Lugar por confirmar');
 addText(where,'small','',event.municipality||'Gran Canaria');
 meta.append(where);info.append(meta);
 const bottom=el('div','event-bottom');
 const price=event.free===1||event.free===true?'Gratis':String(event.price||'');
 bottom.append(el('span','event-price',price));
 bottom.append(el('span','',sponsored?'Evento patrocinado':'Ver detalles en la agenda'));
 info.append(bottom);
 card.append(photo,info);
 return card;
}
function sponsorBanner(draft){
 const slot=el('section','sponsor-slot');
 slot.setAttribute('aria-label','Espacio patrocinado en la simulación');
 const cap=el('div','sponsor-caption');
 cap.append(el('span','','✳ ESPACIO PATROCINADO'),el('span','','PUBLICIDAD'));
 slot.append(cap);
 const card=el('aside','sponsor-card');
 const media=el('div','sponsor-media');
 if(canDisplayImage(draft.image,false)){
  const img=el('img');img.src=draft.image;img.alt='Imagen de '+draft.advertiser;
  media.append(img);
 }else media.append(el('span','','Imagen del anunciante'));
 const body=el('div','sponsor-content');
 body.append(el('span','sponsor-label',draft.advertiser+' · COMERCIO LOCAL'));
 body.append(el('h3','sponsor-heading',draft.title));
 body.append(el('p','sponsor-copy',draft.description));
 const footer=el('div','sponsor-bottom');
 const area=draft.plan==='insular'?'Gran Canaria':(draft.municipalities||[]).join(', ');
 footer.append(el('span','sponsor-location','⌖ '+area),el('span','sponsor-button','Descubrir ↗'));
 body.append(footer);
 card.append(media,body);slot.append(card);
 return slot;
}
function contractCallout(draft){
 const wrapper=el('section','inline-contract');
 wrapper.setAttribute('aria-label','Solicitar contratación del anuncio mostrado');
 const row=el('div','inline-contract-row');
 const info=el('div','inline-contract-info');
 info.append(el('strong','','¿Te gusta este anuncio?'));
 const plan={local:'Local',zona:'Zona',insular:'Insular'}[draft.plan]||'Publicidad';
 const price=Number(draft.total)||0;
 info.append(el('span','',plan+' · '+draft.days+' días · '+price+' € · Revisión antes del pago'));
 const button=el('button','inline-contract-button','Solicitar contratación');
 button.type='button';button.setAttribute('aria-controls','interestSection');button.setAttribute('aria-expanded','false');
 button.onclick=()=>{
  const section=$('interestSection');
  section.hidden=!section.hidden;
  button.setAttribute('aria-expanded',String(!section.hidden));
  button.textContent=section.hidden?'Solicitar contratación':'Ocultar solicitud';
  if(!section.hidden)section.scrollIntoView({behavior:'smooth',block:'nearest'});
 };
 const actions=el('div','inline-contract-actions');
 const testButton=el('button','inline-contract-test','Enviar prueba al panel');
 testButton.type='button';testButton.hidden=true;
 const testFeedback=el('p','inline-contract-feedback','');testFeedback.setAttribute('role','status');testFeedback.setAttribute('aria-live','polite');
 actions.append(button,testButton);row.append(info,actions);wrapper.append(row,testFeedback);
 // Admin test calls the authenticated admin API; no actual merchant data or payment.
 fetch('/api/admin?op=advertising-intake-config',{credentials:'same-origin',cache:'no-store'})
  .then(async response=>response.ok?response.json():null)
  .then(config=>{if(config?.admin_test_enabled===true)testButton.hidden=false})
  .catch(()=>{});
 testButton.onclick=async()=>{
  if(!confirm('¿Guardar esta simulación como una solicitud de PRUEBA en tu panel de administración? No se cobra ni publica nada.'))return;
  if(!canDisplayImage(draft.image,false)){
   testFeedback.textContent='Para enviar una prueba con imagen debes adjuntar primero una creatividad desde «Volver a editar».';
   return;
  }
  testButton.disabled=true;testFeedback.textContent='Enviando anuncio e imagen al panel…';
  try{
   const response=await fetch('/api/admin?op=advertising-test-proposal',{
    method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({campaign:{
     plan:draft.plan,days:draft.days,kind:draft.kind,
     advertiser:draft.advertiser,title:draft.title,
     description:draft.description,destination:draft.destination,
     start:draft.start,municipalities:draft.municipalities,
     eventDate:draft.eventDate,eventVenue:draft.eventVenue,eventTown:draft.eventTown,
     image_data:draft.image
    }})
   });
   const result=await response.json();
   if(!response.ok||!result.received)throw Error(result.error||'No se pudo enviar la prueba');
   testFeedback.replaceChildren();
   const strong=el('strong','','Tu prueba se ha guardado correctamente. ');
   const link=el('a','inline-test-link','Verla en administración');
   link.href='/admin/#publicidad';link.target='_blank';link.rel='noopener noreferrer';
   testFeedback.append(strong,link);
   testButton.textContent='Prueba enviada';testButton.disabled=true;
  }catch(err){testFeedback.textContent=err.message||'Error al enviar la prueba';testButton.disabled=false}
 };
 wrapper.append($('interestSection')); // The public form belongs to this ad.
 return wrapper;
}
function localToday(){
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{
  timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'
 }).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 return p.year+'-'+p.month+'-'+p.day;
}
async function loadEvents(){
 // Read-only public catalog; no draft, image, or personal data ever goes to the API.
 for(const path of ['/api/catalog','/events.json']){
  try{
   const res=await fetch(path,{cache:'no-store'});
   if(!res.ok)continue;
   const data=await res.json(),events=Array.isArray(data)?data:data.events;
   if(Array.isArray(events))return events;
  }catch{}
 }
 return [];
}
function render(draft,events){
 const today=localToday();
 const active=events.filter(e=>e&&typeof e.title==='string'&&
  typeof e.start==='string'&&String(e.end||e.start).slice(0,10)>=today);
 active.sort((a,b)=>String(a.start).localeCompare(String(b.start)));
 const target=draft.plan==='insular'?[]:draft.municipalities;
 let candidates=draft.plan==='insular'?active:active.filter(e=>target.includes(e.municipality));
 let otherArea=false;
 if(candidates.length<5 && active.length>candidates.length){
  // Keep this a real feed even when the chosen municipality has few upcoming events.
  // Explicitly distinguish additional island-wide examples.
  candidates=candidates.concat(active.filter(e=>!candidates.includes(e)));
  otherArea=true;
 }
 candidates=candidates.slice(0,12);
 $('searchDescription').textContent=draft.plan==='insular'?'Gran Canaria · Todos los planes':
  (target.join(', ')||'Gran Canaria')+' · Todos los planes';
 $('feedCount').textContent='Simulación de la agenda';
 if(otherArea){
  $('simNote').hidden=false;
  $('simNote').textContent='Se muestran también eventos de otras zonas para ilustrar el aspecto del anuncio.';
 }
 GRID.replaceChildren();
 if(draft.kind==='evento'){
  GRID.append(eventCard({
   title:draft.title,start:draft.eventDate,venue:draft.eventVenue,
   municipality:draft.eventTown,category:'ocio',
   image_url:draft.image,free:false,price:''
  },true));
  GRID.append(contractCallout(draft));
 }
 let bannerAdded=false;
 for(let i=0;i<candidates.length;i++){
  GRID.append(eventCard(candidates[i]));
  if(draft.kind==='banner'&&i===4){
   GRID.append(sponsorBanner(draft));GRID.append(contractCallout(draft));bannerAdded=true;
  }
 }
 if(draft.kind==='banner'&&!bannerAdded){GRID.append(sponsorBanner(draft));GRID.append(contractCallout(draft));}
 if(!candidates.length){
  GRID.append(el('p','status','No hay otros eventos disponibles ahora mismo para mostrar en la simulación.'));
 }
 STATUS.hidden=true;
 const names={local:'Local',zona:'Zona',insular:'Insular'};
 $('simPlan').textContent=(names[draft.plan]||'Campaña')+' · '+draft.days+' días · '+(draft.plan==='insular'?'Gran Canaria':(draft.municipalities||[]).join(', '));
 $('simTotal').textContent=(Number(draft.total)||0)+' €';
 $('simSummary').hidden=false;
}
function initInterestForm(draft){
 const section=$('interestSection'),form=$('interestForm');
 const availability=$('interestAvailability'),feedback=$('interestFeedback');
 section.hidden=true;
 fetch('/api/advertise-interest',{cache:'no-store'}).then(async response=>{
  if(!response.ok)throw Error('Configuración no disponible');
  return response.json();
 }).then(config=>{
  if(config.enabled!==true||typeof config.privacy_url!=='string'||!config.privacy_url.startsWith('https://')){
   availability.textContent='La recepción de solicitudes aún no está activada. Puedes ver tu anuncio, pero no enviarlo hasta que se configure el formulario de contratación.';
   return;
  }
  $('interestPrivacy').href=config.privacy_url;
  if(config.proposal_enabled===true){
   $('proposalSubmit').hidden=false;
   $('proposalNotice').hidden=false;
  }
  availability.hidden=true;
  form.hidden=false;
 }).catch(()=>{
  availability.textContent='No se ha podido comprobar el envío de solicitudes. Inténtalo de nuevo después de recargar la página.';
 });
 $('eventCampaignRule').hidden=draft.kind!=='evento';
 form.addEventListener('submit',async event=>{
  event.preventDefault();
  if(!form.reportValidity())return;
  const proposal=true; // This simulator submits the selected ad for editorial review, never payment.
  if(proposal&&(!draft.image||!/^data:image\/webp;base64,/.test(draft.image))){
   feedback.textContent='Para solicitar la publicación, primero añade una imagen al anuncio desde «Volver al formulario».';
   return;
  }
  const button=$('proposalSubmit');
  button.disabled=true;
  feedback.textContent='Enviando solicitud de contratación para revisión…';
  const values=new FormData(form);
  // The complete creative is sent only when the user expressly chooses a
  // proposal for review; an interest-only enquiry never transfers its image.
  const payload={
   company:String(values.get('company')||''),
   contact:String(values.get('contact')||''),
   email:String(values.get('email')||''),
   telephone:String(values.get('telephone')||''),
   website:String(values.get('website')||''),
   consent:values.get('consent')==='on',
   proposal,
   campaign:{
    kind:draft.kind,plan:draft.plan,days:draft.days,
    municipalities:draft.municipalities,start:draft.start,
    advertiser:draft.advertiser,title:draft.title,description:draft.description,
    destination:draft.destination,image_data:proposal?draft.image:null,
    eventDate:draft.eventDate,eventVenue:draft.eventVenue,eventTown:draft.eventTown
   }
  };
  try{
   const response=await fetch('/api/advertise-interest',{
    method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)
   });
   const result=await response.json();
   if(!response.ok||result.received!==true)throw Error(result.error||'No se ha podido registrar');
   form.hidden=true;
   availability.hidden=false;
   availability.classList.add('interest-success');
   availability.replaceChildren();
   availability.append(el('strong','','¡Hemos recibido tu anuncio!'));
   const notice=result.welcome_email==='sent'
    ?' Te hemos enviado un correo de bienvenida con el acceso privado a tu anuncio. Revisa también la carpeta de spam.'
    :result.private_area_ready
      ?' Hemos preparado tu área privada. Si todavía no recibes el correo, contactaremos contigo para darte acceso.'
      :' Hemos guardado tu solicitud; te informaremos de los siguientes pasos.';
   availability.append(el('span','',notice+' Revisaremos tu creatividad antes de cualquier pago. No se ha cobrado ni publicado nada.'));
  }catch(err){
   feedback.textContent=err instanceof Error?err.message:'No se ha podido registrar tu interés.';
  }finally{button.disabled=false}
 });
}
let draft=null;
try{
 const raw=sessionStorage.getItem(KEY);
 draft=raw?JSON.parse(raw):null;
 if(!draft||draft.version!==1||!Number.isFinite(draft.createdAt)||
    Math.abs(Date.now()-draft.createdAt)>daysSince||
    !['banner','evento'].includes(draft.kind)||
    !['local','zona','insular'].includes(draft.plan)||
    ![30,60].includes(draft.days)||
    typeof draft.title!=='string'||draft.title.length>160||
    typeof draft.advertiser!=='string'||draft.advertiser.length>120||
    typeof draft.description!=='string'||draft.description.length>350||
    !Array.isArray(draft.municipalities)||draft.municipalities.length>4){
  draft=null;sessionStorage.removeItem(KEY);
 }
}catch{draft=null}
if(!draft){
 STATUS.replaceChildren(
  el('p','','La vista previa ya no está disponible. Vuelve a preparar tu anuncio.'),
  el('a','return','Volver al formulario')
 );
 STATUS.querySelector('a').href='/anunciate/#crear';
}else{
 loadEvents().then(events=>render(draft,events))
 .catch(()=>render(draft,[]));
 initInterestForm(draft);
}
})();