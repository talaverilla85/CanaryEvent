(()=>{'use strict';
const $=id=>document.getElementById(id);
async function load(){
 try{
  const response=await fetch('/api/privacy',{credentials:'omit',cache:'no-store'});
  if(!response.ok)throw Error('Error al consultar la información legal');
  const info=await response.json();
  if(info?.ready!==true){$('unavailable').hidden=false;return}
  const values=[info.legal_name,info.legal_address,info.legal_nif,info.privacy_email];
  if(values.some(v=>typeof v!=='string'||!v.trim())){$('unavailable').hidden=false;return}
  $('legalName').textContent=info.legal_name;
  $('legalAddress').textContent=info.legal_address;
  $('legalNif').textContent=info.legal_nif;
  for(const id of ['legalEmail','rightsEmail']){
   $(id).textContent=info.privacy_email;
   $(id).href='mailto:'+info.privacy_email;
  }
  $('policy').hidden=false;
 }catch{$('unavailable').hidden=false}
 finally{$('loading').hidden=true}
}
load();
})();