(()=>{
'use strict';
const $=id=>document.getElementById(id);
const error=$('error');
const toHex=buffer=>Array.from(new Uint8Array(buffer),x=>x.toString(16).padStart(2,'0')).join('');
const bytes=n=>{const b=new Uint8Array(n);crypto.getRandomValues(b);return b};
$('generator').addEventListener('submit',async e=>{
 e.preventDefault();error.classList.add('hidden');
 const a=$('pass').value,b=$('confirmPass').value,button=$('generate');
 if(a!==b){error.textContent='Las contraseñas no coinciden.';error.classList.remove('hidden');return}
 if(a.length<16){error.textContent='Utiliza al menos 16 caracteres.';error.classList.remove('hidden');return}
 button.disabled=true;button.textContent='Generando huella segura…';
 try{
  if(!crypto?.subtle)throw new Error('Este navegador no permite generación criptográfica segura');
  const salt=bytes(16);
  const enc=new TextEncoder();
  const key=await crypto.subtle.importKey('raw',enc.encode(a),'PBKDF2',false,['deriveBits']);
  const derived=await crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:600000,hash:'SHA-256'},key,256);
  $('valA').value='pbkdf2-sha256:600000:'+toHex(salt)+':'+toHex(derived);
  $('valB').value=toHex(bytes(48));
  $('pass').value='';$('confirmPass').value='';
  $('stepOne').classList.add('hidden');$('stepTwo').classList.remove('hidden');
  window.scrollTo({top:0,behavior:'smooth'});
 }catch(err){error.textContent='No se ha podido generar la huella en este navegador. '+err.message;error.classList.remove('hidden')}
 finally{button.disabled=false;button.textContent='Generar credenciales seguras'}
});
document.querySelectorAll('.copy').forEach(button=>button.addEventListener('click',async()=>{
 const input=$(button.dataset.copy);
 try{await navigator.clipboard.writeText(input.value);button.textContent='Copiado ✓'}
 catch{input.focus();input.select();button.textContent='Seleccionado: pulsa Copiar'}
}));
$('clear').addEventListener('click',()=>{$('valA').value='';$('valB').value='';$('stepTwo').classList.add('hidden');$('stepOne').classList.remove('hidden');window.scrollTo(0,0)});
})();