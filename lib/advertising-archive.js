// Archiving deliberately does NOT delete paid information or any customer payments.
// All operations are invoked behind authenticated admin + same-origin checks.
import {stripeMode} from './stripe-advertising.js';

function validKey(source,id){
 if(!['lead','draft','house','published'].includes(source))throw new Error('Tipo de publicidad no válido');
 if(['lead','draft'].includes(source)){
  const n=Number(id);
  if(!Number.isSafeInteger(n)||n<=0)return null;
  return String(n);
 }
 if(typeof id!=='string'||!/^[A-Za-z0-9_-]{2,90}$/.test(id))return null;
 return id;
}
async function updateStripeLink(id,active){
 if(!id)return;
 if(!/^plink_[A-Za-z0-9]+$/.test(id))throw new Error('Referencia Stripe inválida');
 const key=String(process.env.STRIPE_SECRET_KEY||''),mode=stripeMode();
 if(!['test','live'].includes(mode)||!key.startsWith(mode==='test'?'sk_test_':'sk_live_'))
  throw new Error('Stripe no está configurado. No se puede retirar una solicitud con enlace de pago activo.');
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch('https://api.stripe.com/v1/payment_links/'+encodeURIComponent(id),{
   method:'POST',signal:controller.signal,
   headers:{Authorization:'Bearer '+key,'Content-Type':'application/x-www-form-urlencoded'},
   body:new URLSearchParams({active:String(active)}).toString()
  });
  if(!response.ok)throw new Error('Stripe no ha podido '+(active?'reactivar':'desactivar')+' el enlace. No se ha modificado la campaña.');
  const result=await response.json();
  if(result.id!==id||result.active!==active||result.livemode!==(mode==='live'))
   throw new Error('Stripe devolvió un estado inesperado; no se ha archivado la campaña');
 }finally{clearTimeout(timeout)}
}
export async function listAdvertisingArchives(sql){
 const rows=await sql`SELECT source,record_id,archived_at FROM advertising_archives ORDER BY archived_at DESC LIMIT 500`;
 return {archives:rows};
}
export async function changeAdvertisingArchive(sql,body){
 const source=body?.source,recordId=validKey(source,body?.id);
 if(!recordId)throw new Error('Anuncio no válido');
 if(body?.action!=='archive'&&body?.action!=='restore')
  throw new Error('Acción de archivo no válida');
 const archiving=body.action==='archive';
 if(body.confirmation!==(archiving?'ARCHIVAR':'RESTAURAR'))
  throw new Error('Debes confirmar la operación de archivo');
 if(source==='house'||source==='published'){
  if(recordId==='arimar-fundador')
   throw new Error('La publicidad principal de AriMar está protegida. Puedes pausarla desde el panel.');
  const [ad]=await sql`SELECT id,kind FROM ad_campaigns WHERE id=${recordId}`;
  if(!ad||ad.kind!==(source==='house'?'house':'paid'))
   throw new Error('No se ha encontrado la campaña');
  if(source==='published'){
   const [linked]=await sql`SELECT id FROM advertiser_campaign_drafts WHERE published_ad_id=${recordId}`;
   if(linked)throw new Error('Archiva este anuncio desde su solicitud pagada.');
  }
  if(archiving){
   await sql`INSERT INTO advertising_archives(source,record_id) VALUES(${source},${recordId})
     ON CONFLICT(source,record_id) DO NOTHING`;
   await sql`UPDATE ad_campaigns SET enabled=FALSE,updated_at=now() WHERE id=${recordId}`;
  }else{
   // Restoring does not automatically expose an archived ad to the public.
   await sql`DELETE FROM advertising_archives WHERE source=${source} AND record_id=${recordId}`;
  }
 }else if(source==='lead'){
  const id=Number(recordId);
  const [lead]=await sql`SELECT id FROM advertising_enquiries WHERE id=${id}`;
  if(!lead)throw new Error('Solicitud no encontrada');
  const [linked]=await sql`SELECT id FROM advertiser_campaign_drafts WHERE source_lead_id=${id}`;
  if(linked)throw new Error('Esta solicitud tiene una campaña asociada: archiva la campaña.');
  if(archiving){
   await sql`INSERT INTO advertising_archives(source,record_id) VALUES('lead',${recordId})
     ON CONFLICT(source,record_id) DO NOTHING`;
   await sql`UPDATE sponsored_events SET enabled=FALSE,updated_at=now() WHERE enquiry_id=${id}`;
  }else{
   await sql`DELETE FROM advertising_archives WHERE source='lead' AND record_id=${recordId}`;
  }
 }else{
  const id=Number(recordId);
  const [draft]=await sql`SELECT id,source_lead_id,payment_status,stripe_payment_link_id,
   published_event_id,published_ad_id, status FROM advertiser_campaign_drafts WHERE id=${id}`;
  if(!draft)throw new Error('Campaña no encontrada');
  const [existing]=await sql`SELECT record_id FROM advertising_archives WHERE source='draft' AND record_id=${recordId}`;
  if(archiving&&!existing&&draft.stripe_payment_link_id){
   // Never leave a payable URL behind for a withdrawn campaign.
   await updateStripeLink(draft.stripe_payment_link_id,false);
  }else if(!archiving&&existing&&draft.stripe_payment_link_id&&draft.payment_status!=='paid'){
   // An unpaid restored campaign can keep using its original signed payment link.
   await updateStripeLink(draft.stripe_payment_link_id,true);
  }
  if(archiving){
   await sql`INSERT INTO advertising_archives(source,record_id) VALUES('draft',${recordId})
     ON CONFLICT(source,record_id) DO NOTHING`;
   if(draft.published_event_id)
    await sql`UPDATE sponsored_events SET enabled=FALSE,updated_at=now() WHERE id=${draft.published_event_id} AND advertiser_draft_id=${id}`;
   if(draft.published_ad_id)
    await sql`UPDATE ad_campaigns SET enabled=FALSE,updated_at=now() WHERE id=${draft.published_ad_id} AND kind='paid'`;
  }else{
   await sql`DELETE FROM advertising_archives WHERE source='draft' AND record_id=${recordId}`;
   // Do not reactivate published content automatically. Admin must explicitly activate it.
  }
 }
 return {ok:true,source,id:recordId,archived:archiving,
  message:archiving?'Se ha retirado del panel. Puedes recuperarlo en «Archivados».':
   'Registro recuperado. La publicación no se reactiva automáticamente.'};
}
