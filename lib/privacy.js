// Public legal identity for DParranda, operated by an individual autónomo.
// These values are intentionally never embedded in the public Git repository.
// They are *public legal disclosures* once configured in Vercel, not secrets.
const CONFIG={
  legal_name:'DPARRANDA_LEGAL_NAME',
  legal_address:'DPARRANDA_LEGAL_ADDRESS',
  legal_nif:'DPARRANDA_LEGAL_NIF',
  privacy_email:'DPARRANDA_PRIVACY_EMAIL'
};
const val=(key,max)=>typeof process.env[key]==='string'?process.env[key].trim().slice(0,max):'';
export function missingPrivacyIdentity(){
 const missing=[];
 const name=val(CONFIG.legal_name,160);
 const address=val(CONFIG.legal_address,250);
 const nif=val(CONFIG.legal_nif,22).toUpperCase().replace(/\s/g,'');
 const email=val(CONFIG.privacy_email,180);
 if(name.length<6||/[<>\x00-\x1f]/.test(name))missing.push(CONFIG.legal_name);
 if(address.length<10||/[<>\x00-\x1f]/.test(address))missing.push(CONFIG.legal_address);
 if(!/^[A-Z0-9-]{8,15}$/.test(nif))missing.push(CONFIG.legal_nif);
 if(!/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(email))missing.push(CONFIG.privacy_email);
 return missing;
}
export function publicPrivacyDetails(){
 if(missingPrivacyIdentity().length)return null;
 return {
  legal_name:val(CONFIG.legal_name,160),
  legal_address:val(CONFIG.legal_address,250),
  legal_nif:val(CONFIG.legal_nif,22).toUpperCase().replace(/\s/g,''),
  privacy_email:val(CONFIG.privacy_email,180)
 };
}
export function privacyUrl(){
 if(!publicPrivacyDetails())return null;
 // Default URL lives with the same first-party simulator and contact form.
 // DPARRANDA_PRIVACY_URL remains an optional override for a future domain.
 const alternative=val('DPARRANDA_PRIVACY_URL',450);
 if(alternative){
  try{
   const u=new URL(alternative);
   if(u.protocol==='https:'&&!u.username&&!u.password&&
    (u.hostname==='canaryevent.vercel.app'||u.hostname==='dparranda.es'||
      u.hostname.endsWith('.dparranda.es')))return u.href;
  }catch{}
 }
 return 'https://canaryevent.vercel.app/privacidad/';
}
