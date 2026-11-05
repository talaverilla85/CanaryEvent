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
 }
 let bannerAdded=false;
 for(let i=0;i<candidates.length;i++){
  GRID.append(eventCard(candidates[i]));
  if(draft.kind==='banner'&&i===4){
   GRID.append(sponsorBanner(draft));bannerAdded=true;
  }
 }
 if(draft.kind==='banner'&&!bannerAdded)GRID.append(sponsorBanner(draft));
 if(!candidates.length){
  GRID.append(el('p','status','No hay otros eventos disponibles ahora mismo para mostrar en la simulación.'));
 }
 STATUS.hidden=true;
 const names={local:'Local',zona:'Zona',insular:'Insular'};
 $('simPlan').textContent=(names[draft.plan]||'Campaña')+' · '+draft.days+' días · '+(draft.plan==='insular'?'Gran Canaria':(draft.municipalities||[]).join(', '));
 $('simTotal').textContent=(Number(draft.total)||0)+' €';
 $('simSummary').hidden=false;
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
}
})();