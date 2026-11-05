(()=>{'use strict';
const $=id=>document.getElementById(id);
const PRICES={local:19,zona:49,insular:99};
const LABELS={local:'Local · 1 municipio',zona:'Zona · hasta 4 municipios',insular:'Insular · toda Gran Canaria'};
const TOWNS=['Agaete','Agüimes','Artenara','Arucas','Firgas','Gáldar','Ingenio',
 'La Aldea de San Nicolás','Las Palmas de Gran Canaria','Mogán','Moya',
 'San Bartolomé de Tirajana','Santa Brígida','Santa Lucía de Tirajana',
 'Santa María de Guía de Gran Canaria','Tejeda','Telde','Teror','Valleseco',
 'Valsequillo de Gran Canaria','Vega de San Mateo'];
let plan='local',days=30,chosen=[],imageUrl=null;
for(const town of TOWNS){const o=document.createElement('option');o.value=town;o.textContent=town;$('eventTown').append(o)}
$('formatType').addEventListener('change',()=>{$('eventDetails').hidden=$('formatType').value!=='evento';resetPreview()});
function showPanel(which){
 const info=which==='info';
 $('infoPanel').hidden=!info;$('createPanel').hidden=info;
 $('chooseInfo').classList.toggle('active',info);
 $('chooseCreate').classList.toggle('active',!info);
 $('chooseInfo').setAttribute('aria-expanded',String(info));
 $('chooseCreate').setAttribute('aria-expanded',String(!info));
 const panel=$(info?'infoPanel':'createPanel');
 history.replaceState(null,'',info?'#informacion':'#crear');
 panel.scrollIntoView({behavior:'smooth',block:'start'});
}
$('chooseInfo').addEventListener('click',()=>showPanel('info'));
$('chooseCreate').addEventListener('click',()=>showPanel('create'));
$('infoToCreate').addEventListener('click',()=>showPanel('create'));
function canSelectTown(municipality){
 if(plan==='insular')return false;
 if(chosen.includes(municipality))return true;
 return chosen.length<(plan==='local'?1:4);
}
function renderTowns(){
 $('regionSection').hidden=plan==='insular';
 const container=$('regionPicker');
 container.replaceChildren();
 for(const town of TOWNS){
  const label=document.createElement('label');
  const check=document.createElement('input');
  check.type='checkbox';check.value=town;check.checked=chosen.includes(town);
  check.disabled=!canSelectTown(town);
  check.addEventListener('change',()=>{
   if(check.checked)chosen.push(town);
   else chosen=chosen.filter(t=>t!==town);
   renderTowns();resetPreview();
  });
  label.append(check,document.createTextNode(town));container.append(label);
 }
 $('regionSummary').textContent=plan==='local'?(chosen.length?'Municipio seleccionado: '+chosen[0]:'Selecciona 1 municipio'):
  (chosen.length+' de 4 municipios seleccionados');
}
function utcEnd(start,count){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(start))return '';
 const d=new Date(start+'T12:00:00Z');
 if(Number.isNaN(d.valueOf())||d.toISOString().slice(0,10)!==start)return '';
 d.setUTCDate(d.getUTCDate()+count-1);
 return d.toISOString().slice(0,10);
}
function showDate(d){
 if(!d)return 'Sin elegir';
 const [y,m,day]=d.split('-');return day+'/'+m+'/'+y;
}
function localDay(){
 const entries=new Intl.DateTimeFormat('en-GB',{
  timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'
 }).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]);
 const p=Object.fromEntries(entries);return p.year+'-'+p.month+'-'+p.day;
}
function updateSummary(){
 const total=PRICES[plan]*(days/30);
 $('selectedPlan').textContent=LABELS[plan]+' · '+days+' días';
 $('campaignTotal').textContent=total+' €';
 const date=$('campaignStart').value;
 $('campaignEnd').value=date?showDate(utcEnd(date,days)):'Selecciona el inicio';
 document.querySelectorAll('[data-plan]').forEach(b=>{
  const active=b.dataset.plan===plan;b.classList.toggle('active',active);
  b.setAttribute('aria-pressed',String(active));
 });
 document.querySelectorAll('[data-days]').forEach(b=>{
  const active=Number(b.dataset.days)===days;b.classList.toggle('active',active);
  b.setAttribute('aria-pressed',String(active));
 });
 renderTowns();
}
function resetPreview(){$('formFeedback').textContent=''}
document.querySelectorAll('[data-plan]').forEach(b=>b.addEventListener('click',()=>{
 const next=b.dataset.plan;if(!Object.hasOwn(PRICES,next))return;
 plan=next;if(plan==='local')chosen=chosen.slice(0,1);
 if(plan==='zona')chosen=chosen.slice(0,4);
 updateSummary();resetPreview();
}));
document.querySelectorAll('[data-days]').forEach(b=>b.addEventListener('click',()=>{
 const n=Number(b.dataset.days);if(![30,60].includes(n))return;
 days=n;updateSummary();resetPreview();
}));
$('campaignStart').min=localDay();
$('campaignStart').addEventListener('change',()=>{updateSummary();resetPreview()});
let unsupportedImage=false;
$('advertImage').addEventListener('change',()=>{
 if(imageUrl){URL.revokeObjectURL(imageUrl);imageUrl=null}
 const file=$('advertImage').files?.[0];
 unsupportedImage=Boolean(file&&(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>12_000_000));
 if(unsupportedImage){
  $('advertImage').setCustomValidity('Utiliza una imagen JPG, PNG o WebP de hasta 12 MB');
  $('imagePreview').hidden=true;
  $('formFeedback').textContent='La imagen debe ser JPG, PNG o WebP y pesar menos de 12 MB.';
 }else{
  $('advertImage').setCustomValidity('');
  if(file){
   imageUrl=URL.createObjectURL(file);
   $('previewImg').src=imageUrl;$('imagePreview').hidden=false;
  }else{$('previewImg').removeAttribute('src');$('imagePreview').hidden=true}
 }
 resetPreview();
});
// Keep the draft only in this browser tab. Nothing is sent to the server.
// Compress artwork before using sessionStorage so mobile browsers can open the
// simulator even when an original camera image is much larger.
async function draftImage(file){
 if(!file)return null;
 const objectUrl=URL.createObjectURL(file);
 try{
  const img=new Image();
  img.src=objectUrl;
  await img.decode();
  if(img.naturalWidth<200||img.naturalHeight<150)throw Error('La imagen es demasiado pequeña.');
  const canvas=document.createElement('canvas');canvas.width=1000;canvas.height=563;
  const ctx=canvas.getContext('2d',{alpha:false});
  if(!ctx)throw Error('No se puede preparar la imagen.');
  ctx.fillStyle='#e9f4f0';ctx.fillRect(0,0,1000,563);
  // Match the public event and banner artwork crop.
  const ratio=Math.max(1000/img.naturalWidth,563/img.naturalHeight);
  const w=img.naturalWidth*ratio,h=img.naturalHeight*ratio;
  ctx.drawImage(img,(1000-w)/2,(563-h)/2,w,h);
  let blob=null;
  for(const quality of [0.79,0.65,0.5,0.38]){
   blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/webp',quality));
   if(blob&&blob.size<620000)break;
  }
  if(!blob||blob.size>620000)throw Error('No se ha podido optimizar la imagen.');
  return await new Promise((resolve,reject)=>{
   const reader=new FileReader();reader.onload=()=>resolve(reader.result);
   reader.onerror=()=>reject(Error('No se pudo leer la imagen.'));
   reader.readAsDataURL(blob);
  });
 }finally{URL.revokeObjectURL(objectUrl)}
}
$('showPreview').addEventListener('click',async()=>{
 const name=$('advertiser').value.trim(),title=$('headline').value.trim(),
  description=$('description').value.trim(),target=$('destination').value.trim(),
  start=$('campaignStart').value,isEvent=$('formatType').value==='evento';
 const eventVenue=$('eventVenue').value.trim(),eventDate=$('eventDate').value,eventTown=$('eventTown').value;
 const problems=[];
 if(plan!=='insular'&&chosen.length===0)problems.push('elige al menos un municipio');
 if(!start||!utcEnd(start,days))problems.push('indica la fecha de inicio');
 else if(start<localDay())problems.push('la fecha de inicio no puede estar en el pasado');
 if(!name)problems.push('escribe el nombre de la empresa o evento');
 if(!title)problems.push('escribe el título del anuncio');
 if(!description)problems.push('añade una descripción corta');
 if(!target||!/^https:\/\/[^/\s?#]+/i.test(target))problems.push('indica una web que empiece por https://');
 if(isEvent){
  if(!eventVenue)problems.push('indica el lugar del evento');
  if(!eventDate)problems.push('indica la fecha y hora del evento');
  if(!eventTown)problems.push('selecciona el municipio del evento');
 }
 if(unsupportedImage)problems.push('corrige el archivo de imagen');
 if(problems.length){
  $('formFeedback').textContent='Para continuar: '+problems.join('; ')+'.';
  $('formFeedback').scrollIntoView({behavior:'smooth',block:'center'});
  return;
 }
 const button=$('showPreview');button.disabled=true;button.textContent='Preparando simulador…';
 try{
  const file=$('advertImage').files?.[0]||null;
  const image=await draftImage(file);
  const payload={
   version:1,createdAt:Date.now(),kind:isEvent?'evento':'banner',
   advertiser:name,title,description,destination:target,
   plan,days,municipalities:plan==='insular'?[]:[...chosen],
   start,end:utcEnd(start,days),total:PRICES[plan]*(days/30),
   eventVenue:isEvent?eventVenue:'',eventDate:isEvent?eventDate:'',
   eventTown:isEvent?eventTown:'',image:image||null
  };
  sessionStorage.setItem('dp_ad_simulator_v1',JSON.stringify(payload));
  window.location.assign('/anunciate/simulador/');
 }catch(e){
  $('formFeedback').textContent=e instanceof Error?e.message:'No se puede abrir el simulador.';
 }finally{button.disabled=false;button.textContent='Ver en DParranda'}
});

$('resetDraft').addEventListener('click',()=>{
 ['advertiser','headline','description','destination','campaignStart','eventVenue','eventDate'].forEach(id=>$(id).value='');
 $('formatType').value='banner';$('eventDetails').hidden=true;
 $('advertImage').value='';
 if(imageUrl){URL.revokeObjectURL(imageUrl);imageUrl=null}
 $('imagePreview').hidden=true;$('previewImg').removeAttribute('src');
 unsupportedImage=false;$('advertImage').setCustomValidity('');
 plan='local';days=30;chosen=[];
 updateSummary();resetPreview();$('formFeedback').textContent='Formulario borrado.';
});
window.addEventListener('pagehide',()=>{if(imageUrl)URL.revokeObjectURL(imageUrl)});
updateSummary();
if(location.hash==='#crear'||location.hash==='#crear-anuncio')showPanel('create');
if(location.hash==='#informacion')showPanel('info');
})();