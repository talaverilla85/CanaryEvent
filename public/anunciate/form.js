(()=>{'use strict';
const form=document.querySelector('#leadForm'),result=document.querySelector('#result'),button=document.querySelector('#submit'),consent=form.elements.consent;
let available=false;
async function status(){
 try{
  const response=await fetch('/api/advertise',{cache:'no-store'});
  const data=await response.json();
  available=response.ok&&data.enabled===true;
  if(available&&data.privacy_url){
   const a=document.createElement('a');a.href=data.privacy_url;a.textContent='Consulta la información completa de privacidad';a.target='_blank';a.rel='noopener noreferrer';
   consent.parentNode.querySelector('span').append(' ',a);
  }
 }catch{available=false}
 button.disabled=!available;
 if(!available){result.textContent='El formulario de solicitudes todavía está en preparación. Estamos configurando su recepción y la información legal antes de habilitar el envío.';}
}
form.addEventListener('submit',async e=>{
 e.preventDefault();if(!available)return;
 button.disabled=true;result.classList.remove('error');result.textContent='Enviando solicitud…';
 const f=Object.fromEntries(new FormData(form).entries());f.consent=consent.checked;
 try{
  const r=await fetch('/api/advertise',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(f)});
  const data=await r.json();if(!r.ok)throw Error(data.error||'No se pudo enviar');
  form.reset();result.textContent='Solicitud recibida. Revisaremos la propuesta antes de contactar contigo.';
 }catch(err){result.textContent=err.message;result.classList.add('error')}
 finally{button.disabled=false}
});
status();
})();