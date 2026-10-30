(()=>{'use strict';
const form=document.getElementById('leadForm');
const status=document.getElementById('result');
const button=document.getElementById('submit');
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
 button.disabled=!enabled;
 if(!enabled)status.textContent='La recepción de solicitudes todavía está en preparación: falta activar el aviso de privacidad y el envío seguro. Puedes revisar todos los datos que solicitaremos, pero no enviarlos aún.';
}
form.addEventListener('submit',async e=>{
 e.preventDefault();if(!enabled)return;
 if(!form.reportValidity())return;
 const selected=creative.files&&creative.files[0];if(!selected){status.textContent='Añade una imagen promocional';return}
 button.disabled=true;status.classList.remove('error');status.textContent='Preparando la imagen y registrando la solicitud…';
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
 finally{button.disabled=!enabled}
});
configuration();
})();