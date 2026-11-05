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
function resetPreview(){$('previewSection').hidden=true;$('checkoutInfo').textContent=''}
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
$('showPreview').addEventListener('click',()=>{
 const name=$('advertiser').value.trim(),title=$('headline').value.trim(),
  description=$('description').value.trim(),target=$('destination').value.trim(),start=$('campaignStart').value;
 const problems=[];
 if(plan!=='insular'&&chosen.length===0)problems.push('elige al menos un municipio');
 if(!start||!utcEnd(start,days))problems.push('indica la fecha de inicio');
 else if(start<localDay())problems.push('la fecha de inicio no puede estar en el pasado');
 if(!name)problems.push('escribe el nombre de la empresa o evento');
 if(!title)problems.push('escribe el título del anuncio');
 if(!description)problems.push('añade una descripción corta');
 if(!target||!/^https:\/\/[^/\s?#]+/i.test(target))problems.push('indica una web que empiece por https://');
 if(unsupportedImage)problems.push('corrige el archivo de imagen');
 if(problems.length){
  $('formFeedback').textContent='Para ver el resumen: '+problems.join('; ')+'.';
  $('previewSection').hidden=true;
  $('formFeedback').scrollIntoView({behavior:'smooth',block:'center'});
  return;
 }
 const total=PRICES[plan]*(days/30);
 $('reviewTitle').textContent=title;
 $('reviewDescription').textContent=description;
 $('reviewBrand').textContent=name;
 $('reviewArea').textContent='Cobertura: '+(plan==='insular'?'toda Gran Canaria':chosen.join(', '));
 $('reviewTime').textContent='Del '+showDate(start)+' al '+showDate(utcEnd(start,days));
 $('reviewUrl').textContent='Destino: '+target;
 $('reviewImage').hidden=!imageUrl;
 $('noImage').hidden=!!imageUrl;
 if(imageUrl)$('reviewImage').src=imageUrl;
 else $('reviewImage').removeAttribute('src');
 $('checkoutSummary').textContent=LABELS[plan]+' · '+days+' días · '+total+' €';
 $('previewSection').hidden=false;
 $('checkoutInfo').textContent='';
 $('formFeedback').textContent='Vista previa generada en tu dispositivo. Sin registro, envío de datos ni cobro.';
 $('previewSection').scrollIntoView({behavior:'smooth',block:'start'});
});
$('checkoutButton').addEventListener('click',()=>{
 $('checkoutInfo').textContent='Todavía no está disponible el pago. Falta conectar Stripe, la comprobación de cupos y el aviso legal. No se ha creado ni cobrado ninguna campaña.';
});
$('resetDraft').addEventListener('click',()=>{
 ['advertiser','headline','description','destination','campaignStart'].forEach(id=>$(id).value='');
 $('advertImage').value='';
 if(imageUrl){URL.revokeObjectURL(imageUrl);imageUrl=null}
 $('imagePreview').hidden=true;$('previewImg').removeAttribute('src');
 unsupportedImage=false;$('advertImage').setCustomValidity('');
 plan='local';days=30;chosen=[];
 updateSummary();resetPreview();$('formFeedback').textContent='Borrador reiniciado. No se ha guardado ni enviado nada.';
});
window.addEventListener('pagehide',()=>{if(imageUrl)URL.revokeObjectURL(imageUrl)});
updateSummary();
if(location.hash==='#crear'||location.hash==='#crear-anuncio')showPanel('create');
if(location.hash==='#informacion')showPanel('info');
})();