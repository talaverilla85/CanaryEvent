(()=>{'use strict';
const form=document.getElementById('leadForm');
const status=document.getElementById('result');
const previewButton=document.getElementById('submit');
const sendButton=document.getElementById('sendProposal');
const demo=document.getElementById('advertiserDemo');
const consent=form.elements.consent,format=form.elements.format;
const creative=form.elements.creative,preview=document.getElementById('creativePreview');
let enabled=false,previewUrl=null;
form.elements.billing_country.value='España';
function canShowEvent(){return format.value==='event'||format.value==='combined'}
function refreshFields(){
 const show=canShowEvent(),fieldset=document.getElementById('eventFields');
 fieldset.hidden=!show;fieldset.disabled=!show;
 for(const id of ['event_title','event_start','event_venue','category'])form.elements[id].required=show;
}
function localDay(d){const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',
 {timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 return [p.year,p.month,p.day].join('-');
}
function refreshDays(){
 const days=Number(form.elements.campaign_days.value),from=form.elements.campaign_start.value;
 if(!from){document.getElementById('campaignSummary').textContent='Indica una fecha de inicio para calcular la duración';return}
 const end=new Date(from+'T12:00:00Z');end.setUTCDate(end.getUTCDate()+days-1);
 document.getElementById('campaignSummary').textContent='La campaña solicitada se mostraría del '+from.split('-').reverse().join('/')+
 ' al '+end.toISOString().slice(0,10).split('-').reverse().join('/')+' ('+days+' días naturales, ambos incluidos).';
}
format.addEventListener('change',refreshFields);
form.elements.campaign_start.addEventListener('change',refreshDays);
form.elements.campaign_days.addEventListener('change',refreshDays);
form.elements.campaign_start.min=localDay(new Date());
refreshFields();refreshDays();
creative.addEventListener('change',()=>{
 if(previewUrl)URL.revokeObjectURL(previewUrl);
 const file=creative.files&&creative.files[0];
 preview.hidden=!file;if(!file)return;
 if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>12000000){
  creative.setCustomValidity('Selecciona una imagen JPG, PNG o WebP de hasta 12 MB');
  preview.hidden=true;return;
 }
 creative.setCustomValidity('');
 previewUrl=URL.createObjectURL(file);
 document.getElementById('creativeImage').src=previewUrl;
 document.getElementById('creativeInfo').textContent=file.name+' · Vista previa horizontal 16:9';
});
async function convertImage(file){
 const url=URL.createObjectURL(file);
 try{
  const image=new Image();image.decoding='async';image.src=url;await image.decode();
  if(image.naturalWidth<200||image.naturalHeight<150)throw Error('La imagen tiene una resolución demasiado pequeña');
  const canvas=document.createElement('canvas');canvas.width=1200;canvas.height=675;
  const cx=canvas.getContext('2d',{alpha:false});
  if(!cx)throw Error('No se ha podido procesar la imagen');
  cx.fillStyle='#eef6f6';cx.fillRect(0,0,1200,675);
  // Same center-cropped 16:9 creative for event card and banner.
  const ratio=Math.max(1200/image.naturalWidth,675/image.naturalHeight);
  const dw=Math.ceil(image.naturalWidth*ratio),dh=Math.ceil(image.naturalHeight*ratio);
  cx.drawImage(image,(1200-dw)/2,(675-dh)/2,dw,dh);
  let blob=null;
  for(const quality of [.85,.72,.55,.4]){
   blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/webp',quality));
   if(blob&&blob.size<=800000)break;
  }
  if(!blob||blob.size>800000)throw Error('No se ha podido optimizar la imagen. Prueba con otra fotografía');
  const encoded=await new Promise((resolve,reject)=>{
   const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('No se puede leer la imagen'));reader.readAsDataURL(blob);
  });
  return {image_data:encoded,image_width:1200,image_height:675,image_name:file.name};
 }finally{URL.revokeObjectURL(url)}
}
async function configuration(){
 try{
  const response=await fetch('/api/advertise',{cache:'no-store'}),data=await response.json();
  enabled=response.ok&&data.enabled===true&&!!data.privacy_url;
  if(enabled){
   const link=document.createElement('a');
   link.href=data.privacy_url;link.textContent='Consulta el aviso de privacidad completo';
   link.rel='noopener noreferrer';link.target='_blank';
   consent.closest('label').querySelector('span').append(' ',link);
  }
 }catch{enabled=false}
 sendButton.hidden=!enabled;
 sendButton.disabled=!enabled;
 document.getElementById('submissionInfo').textContent=enabled?
  'Puedes previsualizar tu anuncio sin enviar datos. Si deseas solicitar su revisión, completa todos los campos y utiliza «Enviar propuesta para revisión».':
  'El botón «Ver cómo quedaría mi anuncio» funciona sin datos personales ni facturación. La recepción real de solicitudes sigue desactivada hasta contar con el aviso de privacidad.';
 if(!enabled)status.textContent='Modo de prueba disponible. Previsualiza tu anuncio sin enviar nada ni introducir datos fiscales.';
}
form.addEventListener('submit',async e=>{
 e.preventDefault();if(!enabled)return;
 if(!form.reportValidity())return;
 const selected=creative.files&&creative.files[0];if(!selected){status.textContent='Añade una imagen promocional';return}
 sendButton.disabled=true;status.classList.remove('error');status.textContent='Preparando la imagen y registrando la solicitud…';
 try{
  const fields=Object.fromEntries(new FormData(form).entries());
  delete fields.creative;fields.consent=consent.checked;
  fields.campaign_days=Number(fields.campaign_days);
  Object.assign(fields,await convertImage(selected));
  const response=await fetch('/api/advertise',{method:'POST',credentials:'same-origin',
   headers:{'Content-Type':'application/json'},body:JSON.stringify(fields)});
  const data=await response.json();
  if(!response.ok)throw Error(data.error||'No se pudo enviar la propuesta');
  status.textContent='Solicitud '+data.request_id+' registrada. Revisaremos los datos antes de ofrecerte una propuesta.';
  form.reset();form.elements.billing_country.value='España';refreshFields();refreshDays();
  preview.hidden=true;if(previewUrl)URL.revokeObjectURL(previewUrl);
 }catch(err){status.classList.add('error');status.textContent=err.message}
 finally{sendButton.disabled=!enabled}
});
function previewAdvertiser(){
 // A self-contained demonstration. Do not read, store or transmit contact,
 // billing, consent, or other personal information.
 const f=form.elements, fmt=f.format.value;
 const isEvent=fmt==='event'||fmt==='combined';
 const title=(isEvent?f.event_title.value:f.campaign_name.value).trim()||
   f.campaign_name.value.trim();
 if(!fmt){
  status.textContent='Para ver la vista previa, selecciona primero «Formato publicitario».';
  status.classList.add('error');f.format.focus();return;
 }
 if(!title){
  status.textContent='Escribe el nombre de la campaña o del evento para crear la vista previa.';
  status.classList.add('error');(isEvent?f.event_title:f.campaign_name).focus();return;
 }
 const kind={event:'Evento patrocinado',banner:'Banner entre eventos',
  combined:'Evento y banner',other:'Propuesta personalizada'};
 const desc=f.banner_text.value.trim()||f.message.value.trim()||
  'Tu promoción se mostrará aquí cuando añadas la descripción.';
 document.getElementById('demoFormat').textContent=kind[fmt]||'Publicidad';
 document.getElementById('demoTitle').textContent=title;
 document.getElementById('demoDescription').textContent=desc;
 document.getElementById('demoLocation').textContent='⌖ '+(
  (isEvent&&f.event_municipality.value.trim())||f.municipality.value.trim()||'Gran Canaria');
 const from=f.campaign_start.value,days=Number(f.campaign_days.value);
 let windowText='Fechas por concretar';
 if(from&&Number.isFinite(days)&&days>0&&days<=60){
  const to=new Date(from+'T12:00:00Z');to.setUTCDate(to.getUTCDate()+days-1);
  windowText=from.split('-').reverse().join('/')+' – '+
    to.toISOString().slice(0,10).split('-').reverse().join('/')+' · '+days+' días';
 }
 document.getElementById('demoDates').textContent='◷ '+windowText;
 const target=f.action_url.value.trim();
 document.getElementById('demoDestination').textContent=target&&/^https:\/\//i.test(target)?
   'Más información: '+target:'Botón: Más información';
 const artwork=document.getElementById('demoArtwork');
 const chosen=creative.files&&creative.files[0];
 const validImage=!!chosen&&['image/jpeg','image/png','image/webp'].includes(chosen.type)&&
   chosen.size<=12000000&&!creative.validationMessage&&!!previewUrl;
 artwork.hidden=!validImage;
 if(validImage)artwork.src=previewUrl;
 else artwork.removeAttribute('src');
 document.getElementById('demoArtworkFallback').hidden=validImage;
 demo.hidden=false;status.classList.remove('error');
 status.textContent='Vista previa creada en este dispositivo. No se ha enviado ninguna solicitud.';
 demo.scrollIntoView({behavior:'smooth',block:'start'});
}
previewButton.addEventListener('click',previewAdvertiser);
document.getElementById('closeAdvertiserDemo').addEventListener('click',()=>{demo.hidden=true;previewButton.focus()});
configuration();
})();