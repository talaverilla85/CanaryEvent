// Administrator edits paid creative without touching Stripe, price, plan or booking dates.
import {safeText} from './admin-auth.js';

function validHttps(url){
 try{const u=new URL(url);return u.protocol==='https:'&&!u.username&&!u.password}
 catch{return false}
}
function plain(value,max,name,{required=true}={}){
 if(typeof value!=='string'||value.length>max)throw new Error(name+' supera el tamaño permitido');
 const s=safeText(value,max);
 if(required&&!s)throw new Error('Indica '+name.toLowerCase());
 return s;
}
export async function editPaidCreative(sql,body,parseImage){
 const id=Number(body?.id);
 if(!Number.isSafeInteger(id)||id<1)throw new Error('Anuncio no válido');
 const [draft]=await sql`SELECT d.id,d.placement,d.status,d.payment_status,
  d.published_event_id,d.published_ad_id,d.stripe_checkout_session_id
  FROM advertiser_campaign_drafts d WHERE d.id=${id}`;
 if(!draft||draft.payment_status!=='paid'||!draft.stripe_checkout_session_id||
    !['active','approved','paid_review'].includes(draft.status))
  throw new Error('Solo puedes modificar anuncios con pago confirmado y no finalizados');
 const title=plain(body.title,160,'Título');
 const description=plain(body.description,650,'Descripción');
 if(description.length<12)throw new Error('La descripción debe tener al menos 12 caracteres');
 const destination=plain(body.destination,800,'Enlace de destino');
 if(!validHttps(destination))throw new Error('El enlace de destino debe ser HTTPS');
 const imageAlt=plain(body.image_alt||title,160,'Descripción de la imagen');
 let eventStart=null,eventTown=null,eventVenue=null;
 if(draft.placement==='evento'){
  eventStart=plain(body.event_start,16,'Fecha y hora del evento');
  if(!/^20\d\d-(0[1-9]|1[0-2])-([0-2]\d|3[01])T([01]\d|2[0-3]):[0-5]\d$/.test(eventStart)||
     Number.isNaN(Date.parse(eventStart+':00Z'))||
     new Date(eventStart+':00Z').toISOString().slice(0,10)!==eventStart.slice(0,10))
   throw new Error('Fecha y hora del evento inválidas');
  eventTown=plain(body.event_town,90,'Municipio del evento');
  eventVenue=plain(body.event_venue,200,'Lugar del evento');
 }
 if(draft.published_event_id){
  const [pub]=await sql`SELECT id FROM sponsored_events
   WHERE id=${draft.published_event_id} AND advertiser_draft_id=${id}`;
  if(!pub)throw new Error('La publicación vinculada no se ha encontrado');
 }
 if(draft.published_ad_id){
  const [pub]=await sql`SELECT id FROM ad_campaigns
   WHERE id=${draft.published_ad_id} AND kind='paid'`;
  if(!pub)throw new Error('La publicidad vinculada no se ha encontrado');
 }
 const asset=body.image_data?parseImage(body.image_data):null;
 if(asset&&(Number(body.image_width)!==1200||Number(body.image_height)!==675))
  throw new Error('La imagen debe prepararse a 1200 × 675 píxeles');
 const [updated]=await sql`UPDATE advertiser_campaign_drafts SET
  title=${title},description=${description},destination=${destination},image_alt=${imageAlt},
  event_start=${eventStart},event_town=${eventTown},event_venue=${eventVenue},updated_at=now()
  WHERE id=${id} AND payment_status='paid'
    AND status IN ('paid_review','approved','active') RETURNING id`;
 if(!updated)throw new Error('El estado de la campaña ha cambiado');
 if(asset){
  await sql`INSERT INTO advertiser_campaign_draft_images
    (draft_id,mime_type,width,height,image_data,updated_at)
    VALUES(${id},${asset.mime},1200,675,decode(${asset.base64},'base64'),now())
    ON CONFLICT(draft_id) DO UPDATE SET mime_type=excluded.mime_type,
     width=excluded.width,height=excluded.height,image_data=excluded.image_data,
     updated_at=now()`;
 }
 if(draft.published_event_id){
  const [pub]=await sql`UPDATE sponsored_events SET title=${title},
   details=${description},source_url=${destination},image_alt=${imageAlt},
   start=${eventStart},municipality=${eventTown},venue=${eventVenue},updated_at=now()
   WHERE id=${draft.published_event_id} AND advertiser_draft_id=${id} RETURNING id`;
  if(!pub)throw new Error('No se pudo actualizar el evento público');
 }
 if(draft.published_ad_id){
  const [pub]=await sql`UPDATE ad_campaigns SET headline=${title},
   description=${description},button_url=${destination},image_alt=${imageAlt},updated_at=now()
   WHERE id=${draft.published_ad_id} AND kind='paid' RETURNING id`;
  if(!pub)throw new Error('No se pudo actualizar el anuncio público');
 }
 return {id,updated:true,payment_unchanged:true,booking_unchanged:true,
   new_image:!!asset,message:'Cambios guardados. Pago, plan, fecha y duración contratados sin modificar.'};
}
