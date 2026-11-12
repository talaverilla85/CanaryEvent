// Admin-only scheduling of already paid, editorially approved advertiser campaigns.
// Public APIs check the scheduled dates; no cron, redirect or fake payment can publish.
import {expectedAmount} from './stripe-advertising.js';
import {validLocalDate} from './admin-auth.js';

export function canaryToday(){
 const parts=new Intl.DateTimeFormat('en-GB',{
  timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'
 }).formatToParts(new Date());
 const p=Object.fromEntries(parts.filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
 return p.year+'-'+p.month+'-'+p.day;
}
function validUrl(s){
 try{const u=new URL(s);return u.protocol==='https:'&&!u.username&&!u.password}
 catch{return false}
}
function campaignDates(d){
 if(!validLocalDate(d.campaign_start_iso)||!d.campaign_start_iso)
  throw new Error('La fecha de campaña no es válida');
 const start=d.campaign_start_iso;
 const begins=start<canaryToday()?canaryToday():start;
 const days=Number(d.days),end=new Date(Date.parse(begins+'T12:00:00Z')+(days-1)*86400000).toISOString().slice(0,10);
 return {begins,end,days};
}
export async function schedulePaidDraft(sql,id){
 if(!Number.isSafeInteger(id)||id<1)throw new Error('Anuncio no válido');
 const [d]=await sql`SELECT d.*,to_char(d.campaign_start,'YYYY-MM-DD') AS campaign_start_iso,a.active AS account_active
  FROM advertiser_campaign_drafts d JOIN advertiser_accounts a ON a.id=d.advertiser_id
  WHERE d.id=${id}`;
 if(!d||!d.account_active)throw new Error('Anunciante no encontrado');
 if(d.payment_status!=='paid'||!d.paid_at||!d.stripe_checkout_session_id)
  throw new Error('El pago no está confirmado por Stripe');
 if(!['paid_review','approved','active'].includes(d.status))
  throw new Error('La campaña no está lista para su publicación');
 if(expectedAmount(d.plan,d.days)!==Number(d.price_cents)||
  !['banner','evento'].includes(d.placement)||!validUrl(d.destination))
  throw new Error('Los datos de contratación no coinciden con lo aprobado');
 const {begins,end,days}=campaignDates(d);
 if(d.status==='active'&&d.published_ad_id||d.status==='active'&&d.published_event_id)
  return {id,scheduled:true,already_scheduled:true,start:begins,end};
 if(d.placement==='evento'){
  if(!/^20\d\d-\d\d-\d\dT\d\d:\d\d$/.test(d.event_start||'')||
    !d.event_town||!d.event_venue)throw new Error('Faltan los datos del evento patrocinado');
  const [hasImg]=await sql`SELECT draft_id FROM advertiser_campaign_draft_images WHERE draft_id=${id}`;
  if(!hasImg)throw new Error('El anuncio aprobado no tiene imagen');
  const [inserted]=await sql`INSERT INTO sponsored_events
   (advertiser_draft_id,enquiry_id,enabled,review_status,advertiser,title,start,
    municipality,venue,category,details,price,source_url,image_alt,campaign_starts_at,campaign_ends_at)
   VALUES(${id},${d.source_lead_id||null},FALSE,'draft',${d.advertiser},${d.title},
    ${d.event_start},${d.event_town},${d.event_venue},'ocio',
    ${d.description},'',${d.destination},${d.image_alt||d.title},${begins},${end})
   ON CONFLICT(advertiser_draft_id) DO NOTHING RETURNING id`;
  const [stored]=inserted?[inserted]:await sql`SELECT id FROM sponsored_events WHERE advertiser_draft_id=${id}`;
  if(!stored)throw new Error('No se pudo preparar el evento');
  await sql`UPDATE advertiser_campaign_drafts SET
   status='approved',actual_starts_at=${begins},actual_ends_at=${end},published_event_id=${stored.id},updated_at=now()
   WHERE id=${id} AND payment_status='paid' AND status IN ('paid_review','approved')`;
  await sql`UPDATE sponsored_events SET enabled=TRUE,review_status='approved',updated_at=now()
   WHERE id=${stored.id} AND advertiser_draft_id=${id}`;
  await sql`UPDATE advertiser_campaign_drafts SET status='active',updated_at=now()
   WHERE id=${id} AND status='approved' AND payment_status='paid' AND published_event_id=${stored.id}`;
  return {id,scheduled:true,placement:'evento',start:begins,end,public_id:Number(stored.id)};
 }
 const [hasImg]=await sql`SELECT draft_id FROM advertiser_campaign_draft_images WHERE draft_id=${id}`;
 if(!hasImg)throw new Error('El anuncio aprobado no tiene imagen');
 const adId='dp-ad-'+id;
 await sql`INSERT INTO ad_campaigns
  (id,enquiry_id,enabled,advertiser,kind,permanent,starts_at,ends_at,municipalities,headline,
   description,location,button_text,button_url,image,image_alt,disclosure)
  VALUES(${adId},${d.source_lead_id||null},FALSE,${d.advertiser},'paid',FALSE,${begins},${end},
   ${JSON.stringify(d.municipalities||[])}::jsonb,${d.title},${d.description},
   ${(d.municipalities||[]).join(', ')||'Gran Canaria'},'Más información',${d.destination},'',
   ${d.image_alt||d.title},'Publicidad')
  ON CONFLICT(id) DO NOTHING`;
 await sql`UPDATE advertiser_campaign_drafts SET status='approved',
  actual_starts_at=${begins},actual_ends_at=${end},published_ad_id=${adId},updated_at=now()
  WHERE id=${id} AND payment_status='paid' AND status IN ('paid_review','approved')`;
 await sql`UPDATE ad_campaigns SET enabled=TRUE,updated_at=now() WHERE id=${adId}`;
 await sql`UPDATE advertiser_campaign_drafts SET status='active',updated_at=now()
  WHERE id=${id} AND status='approved' AND payment_status='paid' AND published_ad_id=${adId}`;
 return {id,scheduled:true,placement:'banner',start:begins,end,public_id:adId};
}
