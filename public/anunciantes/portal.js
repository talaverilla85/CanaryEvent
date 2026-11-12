(()=>{'use strict';
const $=id=>document.getElementById(id);
const TOWNS=['Agaete','Agüimes','Artenara','Arucas','Firgas','Gáldar','Ingenio','La Aldea de San Nicolás','Las Palmas de Gran Canaria','Mogán','Moya','San Bartolomé de Tirajana','Santa Brígida','Santa Lucía de Tirajana','Santa María de Guía de Gran Canaria','Tejeda','Telde','Teror','Valleseco','Valsequillo de Gran Canaria','Vega de San Mateo'];
const PRICES={local:19,zona:49,insular:99};
const LABELS={local:'Local',zona:'Zona',insular:'Insular'};
const STATUS={draft:'Borrador',submitted:'Pendiente de revisión',approved_for_payment:'Aprobado · pendiente de pago',pending_payment:'Pendiente de pago',paid_review:'Pago verificado',changes_requested:'Cambios solicitados',
 approved:'Aprobado · pendiente de publicación',active:'Publicado',finished:'Finalizado',rejected:'No aprobado',cancelled:'Cancelado'};
let account=null,campaigns=[],editing=null,plan='local',selected=[],previewUrl=null;
const close=x=>{$(x).hidden=true};
const show=x=>{$(x).hidden=false};
async function api(op,data=null){
 const opts={method:data===null?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:{}};
 if(data!==null){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(data)}
 const response=await fetch('/api/advertiser?op='+encodeURIComponent(op),opts);
 let body={};try{body=await response.json()}catch{}
 if(!response.ok)throw Error(body.error||'Error de conexión');
 return body;
}
function dateText(value){
 const d=String(value||'').slice(0,10);
 return /^\d{4}-\d\d-\d\d$/.test(d)?d.slice(8)+'/'+d.slice(5,7)+'/'+d.slice(0,4):'Por confirmar';
}
function localDay(){
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'})
  .formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 return p.year+'-'+p.month+'-'+p.day;
}
function daysLeft(date){
 const today=localDay(),end=String(date||'').slice(0,10);
 if(!/^\d{4}-\d\d-\d\d$/.test(end))return null;
 return Math.max(0,Math.ceil((Date.parse(end+'T00:00:00Z')-Date.parse(today+'T00:00:00Z'))/86400000)+1);
}
function text(tag,str,className){
 const node=document.createElement(tag);
 node.textContent=String(str||'');
 if(className)node.className=className;
 return node;
}
function feedback(message){$('editorFeedback').textContent=message;show('editorFeedback')}
function summary(){
 const days=Number($('duration').value)||30,total=PRICES[plan]*(days/30);
 $('summaryPlan').textContent=LABELS[plan]+' · '+days+' días';
 $('summaryTotal').textContent=total+' €';
 for(const el of document.querySelectorAll('[data-plan]'))el.classList.toggle('active',el.dataset.plan===plan);
 regions();
}
function regions(){
 $('regionRow').hidden=plan==='insular';
 const grid=$('towns');grid.replaceChildren();
 const max=plan==='local'?1:4;
 for(const town of TOWNS){
  const label=document.createElement('label'),input=document.createElement('input');
  input.type='checkbox';input.value=town;input.checked=selected.includes(town);
  input.disabled=!input.checked&&selected.length>=max;
  input.addEventListener('change',()=>{
   selected=input.checked?[...selected,town]:selected.filter(t=>t!==town);
   regions();
  });
  label.append(input,document.createTextNode(town));grid.append(label);
 }
 $('townHint').textContent=plan==='local'?(selected.length?'Municipio elegido: '+selected[0]:'Elige un municipio'):
  selected.length+' de hasta 4 municipios seleccionados';
}
function resetFile(){
 if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null}
 $('artwork').value='';$('imagePreviewImg').removeAttribute('src');close('imagePreview');
}
function setEditor(d){
 editing=d||null;
 $('draftForm').reset();resetFile();close('editorFeedback');
 plan=d?.plan||'local';selected=Array.isArray(d?.municipalities)?[...d.municipalities]:[];
 $('duration').value=String(d?.days||30);
 $('campaignStart').min=localDay();
 $('campaignStart').value=String(d?.campaign_start||'').slice(0,10);
 $('placement').value=d?.placement||'banner';
 $('advertiser').value=d?.advertiser||account?.company||'';
 $('title').value=d?.title||'';$('description').value=d?.description||'';
 $('destination').value=d?.destination||'';
 $('eventStart').value=d?.event_start||'';
 $('eventTown').value=d?.event_town||TOWNS[0];
 $('eventVenue').value=d?.event_venue||'';
 $('imageAlt').value=d?.image_alt||'';
 $('eventFields').hidden=$('placement').value!=='evento';
 if(d?.has_image){
  $('imagePreviewImg').src='/api/advertiser?op=artwork&id='+Number(d.id);
  show('imagePreview');
 }
 $('editorTitle').textContent=d?'Editar borrador #'+d.id:'Preparar nuevo anuncio';
 summary();show('editor');$('editor').scrollIntoView({behavior:'smooth',block:'start'});
}
function paintCampaigns(){
 const node=$('campaigns');node.replaceChildren();
 close('campaignLoading');
 if(!campaigns.length){node.append(text('p','Todavía no has preparado ninguna campaña. Pulsa «Crear anuncio» para comenzar.','muted'));return}
 for(const d of campaigns){
  const card=text('article','','campaign'),head=text('div','','campaign-row');
  const left=text('div',''),heading=text('h3',d.title);
  left.append(heading,text('div',(LABELS[d.plan]||d.plan)+' · '+d.days+' días · '+(d.price_cents/100)+' €','campaign-meta'));
  head.append(left);
  const badge=text('span',STATUS[d.status]||d.status,'tag'+(d.status==='active'?' active':d.status==='paid_review'?' pending':''));
  head.append(badge);card.append(head);
  const meta=text('p',d.placement==='evento'?'Evento patrocinado':'Banner publicitario','campaign-meta');card.append(meta);
  if(d.status==='active'&&d.actual_ends_at){
   const leftDays=daysLeft(d.actual_ends_at);
   card.append(text('strong',(leftDays??0)+' días restantes','small'));
   if(d.actual_starts_at){
    const start=String(d.actual_starts_at).slice(0,10),end=String(d.actual_ends_at).slice(0,10);
    const elapsed=Math.max(0,(Date.parse(localDay()+'T00:00:00Z')-Date.parse(start+'T00:00:00Z'))/86400000);
    const duration=Math.max(1,(Date.parse(end+'T00:00:00Z')-Date.parse(start+'T00:00:00Z'))/86400000+1);
    const track=text('div','','progress'),bar=text('span');bar.style.width=Math.min(100,Math.max(0,elapsed/duration*100))+'%';track.append(bar);card.append(track);
   }
   card.append(text('p','Publicada: '+dateText(d.actual_starts_at)+' · Finaliza: '+dateText(d.actual_ends_at),'campaign-meta'));
  }else card.append(text('p','La campaña todavía no está publicándose. El plazo de difusión no ha comenzado.','campaign-meta'));
  if(d.status==='pending_payment'&&d.payment_status==='pending'&&/^https:\/\/buy\.stripe\.com\//.test(d.payment_url||'')){
   const button=text('a','Realizar pago seguro · '+(d.price_cents/100)+' €','primary');
   button.href=d.payment_url;button.target='_blank';button.rel='noopener noreferrer';
   card.append(button);
   card.append(text('p','El plazo de la campaña no comienza hasta que el pago esté confirmado y el anuncio se publique.','campaign-meta'));
  }
  if(d.status==='paid_review'&&d.payment_status==='paid')
   card.append(text('p','Pago confirmado. La campaña queda pendiente de publicación.','campaign-meta'));
  if(d.review_note)card.append(text('p','Observaciones del administrador: '+d.review_note,'campaign-meta'));
  if(d.has_image){
   const preview=text('div','','preview'),image=document.createElement('img');
   image.src='/api/advertiser?op=artwork&id='+Number(d.id);image.alt='Creatividad de '+d.title;
   image.loading='lazy';preview.append(image);card.append(preview);
  }
  card.append(text('p','Estadísticas de visitas y clics: próximamente.','campaign-meta'));
  if(['draft','changes_requested'].includes(d.status)){
   const buttons=text('div','','actions'),edit=text('button','Editar borrador','secondary');
   edit.type='button';edit.addEventListener('click',()=>setEditor(d));buttons.append(edit);
   if(d.has_image&&d.campaign_start){
    const submit=text('button','Enviar para revisión','primary');
    submit.type='button';submit.onclick=async()=>{
     if(!confirm('¿Enviar esta versión del anuncio para revisión? Todavía no se realiza ningún pago.'))return;
     submit.disabled=true;
     try{await api('submit',{id:d.id});await loadCampaigns()}
     catch(err){alert(err.message)}
     finally{submit.disabled=false}
    };
    buttons.append(submit);
   }
   card.append(buttons);
  }
  node.append(card);
 }
}
async function loadCampaigns(){
 show('campaignLoading');const data=await api('campaigns');campaigns=data.campaigns||[];paintCampaigns();
}
function showError(message){close('loading');show('noAccess');$('loginMessage').textContent=message}
async function boot(){
 try{
  const config=await api('config');
  if(!config.enabled){showError('Estamos preparando el acceso privado a las campañas. El enlace todavía no está activado.');return}
  if(typeof config.privacy_url==='string')$('privacyLink').href=config.privacy_url;
  const token=new URLSearchParams(location.hash.replace(/^#/,'')).get('acceso');
  if(token){
   await api('exchange',{token});
   history.replaceState(null,'',location.pathname);
  }
  const session=await api('session');
  if(!session.authenticated){showError('Abre el enlace único que recibiste de DParranda. No puedes acceder sin invitación.');return}
  account=session.account;
  $('greeting').textContent='Publicidad de '+(account.company||'tu empresa');
  show('dashboard');show('logout');close('loading');
  await loadCampaigns();
 }catch(err){showError(err.message||'No se ha podido comprobar el acceso')}
}
$('logout').onclick=async()=>{try{await api('logout',{})}catch{}location.replace('/anunciantes/')};
$('newDraft').onclick=()=>setEditor(null);
$('cancelEditor').onclick=()=>close('editor');
$('duration').onchange=summary;
$('placement').onchange=()=>{$('eventFields').hidden=$('placement').value!=='evento'};
document.querySelectorAll('[data-plan]').forEach(btn=>btn.onclick=()=>{
 plan=btn.dataset.plan;
 selected=selected.slice(0,plan==='local'?1:plan==='zona'?4:0);
 summary();
});
for(const town of TOWNS){const option=document.createElement('option');option.value=town;option.textContent=town;$('eventTown').append(option)}
$('artwork').onchange=()=>{
 resetPreview();
 const file=$('artwork').files?.[0];
 if(!file)return;
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>12000000){feedback('Utiliza una imagen JPG, PNG o WebP de hasta 12 MB.');$('artwork').value='';return}
 previewUrl=URL.createObjectURL(file);$('imagePreviewImg').src=previewUrl;show('imagePreview');
};
function resetPreview(){if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=null}}
async function compress(file){
 const url=URL.createObjectURL(file);
 try{
  const image=new Image();image.src=url;await image.decode();
  if(image.naturalWidth<200||image.naturalHeight<150)throw Error('La imagen es demasiado pequeña');
  const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=675;
  const ctx=canvas.getContext('2d',{alpha:false});
  if(!ctx)throw Error('No se puede preparar la imagen');
  const ratio=Math.max(1200/image.naturalWidth,675/image.naturalHeight),w=image.naturalWidth*ratio,h=image.naturalHeight*ratio;
  ctx.fillStyle='#f1f8f7';ctx.fillRect(0,0,1200,675);
  ctx.drawImage(image,(1200-w)/2,(675-h)/2,w,h);
  let blob=null;
  for(const quality of [.82,.7,.55,.42]){
   blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/webp',quality));
   if(blob&&blob.size<=800000)break;
  }
  if(!blob||blob.size>800000)throw Error('No se pudo reducir la imagen');
  return await new Promise((resolve,reject)=>{
   const reader=new FileReader();reader.onload=()=>resolve(reader.result);
   reader.onerror=()=>reject(Error('No se pudo leer la imagen'));
   reader.readAsDataURL(blob);
  });
 }finally{URL.revokeObjectURL(url)}
}
$('draftForm').onsubmit=async event=>{
 event.preventDefault();
 const form=event.currentTarget;
 if(!form.reportValidity())return;
 if(plan!=='insular'&&!selected.length){feedback('Selecciona al menos un municipio.');return}
 const kind=$('placement').value;
 if(kind==='evento'&&(!$('eventStart').value||!$('eventTown').value||!$('eventVenue').value.trim())){
  feedback('Completa la fecha, el municipio y el lugar del evento.');return;
 }
 const button=$('saveDraft');button.disabled=true;feedback('Guardando tu borrador…');
 try{
  const file=$('artwork').files?.[0];
  const payload={
   consent:$('portalConsent').checked,
   id:editing?.id,plan,days:Number($('duration').value),
   placement:kind,municipalities:plan==='insular'?[]:selected,
   campaign_start:$('campaignStart').value,
   advertiser:$('advertiser').value,title:$('title').value,
   description:$('description').value,destination:$('destination').value,
   event_start:$('eventStart').value,event_town:$('eventTown').value,
   event_venue:$('eventVenue').value,image_alt:$('imageAlt').value,
   image_data:file?await compress(file):null
  };
  const result=await api('save',payload);
  feedback('Borrador #'+result.id+' guardado. No se ha cobrado ni publicado nada.');
  await loadCampaigns();
 }catch(err){feedback(err.message||'No se pudo guardar el borrador')}
 finally{button.disabled=false}
};
window.addEventListener('pagehide',resetPreview);
boot();
})();
