// One-off Stripe Payment Links for approved advertising campaigns.
// Every link belongs to one immutable approved draft; never accept client prices.
import {workspaceForDraft} from './advertiser-workspace.js';
import {sendPaymentApprovedEmail} from './advertiser-mail.js';

export const STRIPE_PRICES={local:1900,zona:4900,insular:9900};
export const STRIPE_LABELS={local:'Local',zona:'Zona',insular:'Insular'};
export const expectedAmount=(plan,days)=>
 Object.hasOwn(STRIPE_PRICES,plan)&&[30,60].includes(Number(days))
  ?STRIPE_PRICES[plan]*(Number(days)/30):null;

export function stripePaymentsReady(){
 const mode=process.env.DPARRANDA_STRIPE_MODE||'test';
 const prefix=mode==='test'?'sk_test_':mode==='live'?'sk_live_':null;
 return !!prefix&&process.env.DPARRANDA_STRIPE_PAYMENTS_ENABLED==='true'&&
  String(process.env.STRIPE_SECRET_KEY||'').startsWith(prefix)&&
  /^whsec_/.test(String(process.env.STRIPE_WEBHOOK_SECRET||''));
}
export function stripeMode(){return process.env.DPARRANDA_STRIPE_MODE||'test'}
function canaryDate(){
 const values=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
 return values.year+'-'+values.month+'-'+values.day;
}

async function apiPaymentLink(d){
 const cents=expectedAmount(d.plan,d.days);
 const form=new URLSearchParams({
  'line_items[0][price_data][currency]':'eur',
  'line_items[0][price_data][unit_amount]':String(cents),
  'line_items[0][price_data][product_data][name]':'DParranda · Publicidad '+STRIPE_LABELS[d.plan]+' · '+d.days+' días',
  'line_items[0][price_data][product_data][description]':String(d.title).slice(0,120),
  'line_items[0][quantity]':'1',
  'restrictions[completed_sessions][limit]':'1',
  // Capture invoice details at checkout. Invoice creation remains disabled:
  // a second payable Stripe invoice must NEVER be generated for an already paid link.
  'billing_address_collection':'required',
  'tax_id_collection[enabled]':'true',
  'invoice_creation[enabled]':'false',
  'metadata[dparranda_draft_id]':String(d.id),
  'metadata[dparranda_days]':String(d.days),
  'metadata[dparranda_plan]':d.plan,
  'after_completion[type]':'hosted_confirmation',
  'after_completion[hosted_confirmation][custom_message]':'Gracias. Tu pago se verificará automáticamente. Puedes consultar el estado en tu área privada de DParranda.'
 });
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch('https://api.stripe.com/v1/payment_links',{
   method:'POST',signal:controller.signal,
   headers:{Authorization:'Bearer '+process.env.STRIPE_SECRET_KEY,
    'Content-Type':'application/x-www-form-urlencoded',
    'Idempotency-Key':'dparranda-approved-draft-'+d.id+'-'+cents+'-v1'},
   body:form.toString()
  });
  if(!response.ok){
   console.error('DParranda Stripe link rejected',response.status);
   throw new Error('Stripe no pudo preparar el enlace de pago');
  }
  const link=await response.json();
  if(typeof link.id!=='string'||!link.id.startsWith('plink_')||
     typeof link.url!=='string'||!/^https:\/\/buy\.stripe\.com\//.test(link.url)||
     link.livemode!==(stripeMode()==='live'))
   throw new Error('Stripe devolvió una respuesta de pago inesperada');
  return {id:link.id,url:link.url};
 }finally{clearTimeout(timeout)}
}

export async function ensureApprovedPayment(sql,draftId){
 if(!stripePaymentsReady())return {status:'not_configured'};
 const [d]=await sql`SELECT d.id,d.plan,d.days,d.price_cents,d.status,d.payment_status,
  d.stripe_payment_link_id,d.stripe_payment_url,d.title,d.placement,d.event_start,
  to_char(d.campaign_start,'YYYY-MM-DD') AS campaign_start_iso,a.email
  FROM advertiser_campaign_drafts d JOIN advertiser_accounts a ON a.id=d.advertiser_id
  WHERE d.id=${draftId} AND a.active=TRUE AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=d.id::text)`;
 if(!d)throw new Error('El anunciante no está disponible');
 const cents=expectedAmount(d.plan,d.days);
 if(!cents||Number(d.price_cents)!==cents)throw new Error('El importe aprobado no coincide con la tarifa');
 if(d.payment_status==='paid')return {status:'already_paid'};
 if(d.placement==='evento'){
  const eventDay=String(d.event_start||'').slice(0,10);
  if(!/^20\d{2}-\d{2}-\d{2}$/.test(eventDay)||eventDay<canaryDate()||
      !d.campaign_start_iso||eventDay<d.campaign_start_iso)
   throw new Error('La fecha del evento ya no permite esta contratación. Solicita una corrección antes de cobrar.');
 }
 if(!['approved_for_payment','pending_payment'].includes(d.status))
  throw new Error('El anuncio todavía no está aprobado para el pago');
 let link={id:d.stripe_payment_link_id,url:d.stripe_payment_url};
 if(!link.id||!link.url){
  link=await apiPaymentLink(d);
  const [stored]=await sql`UPDATE advertiser_campaign_drafts SET
    stripe_payment_link_id=${link.id},stripe_payment_url=${link.url},
    status='pending_payment',payment_status='pending',updated_at=now()
    WHERE id=${draftId} AND stripe_payment_link_id IS NULL AND
     status IN ('approved_for_payment','pending_payment') AND payment_status<>'paid'
    RETURNING id`;
  if(!stored){
   const [other]=await sql`SELECT stripe_payment_link_id,stripe_payment_url FROM advertiser_campaign_drafts WHERE id=${draftId}`;
   if(!other?.stripe_payment_link_id||!other?.stripe_payment_url)
    throw new Error('El anuncio cambió mientras se preparaba el enlace');
   link={id:other.stripe_payment_link_id,url:other.stripe_payment_url};
  }
 }else if(d.status==='approved_for_payment'){
  await sql`UPDATE advertiser_campaign_drafts SET status='pending_payment',payment_status='pending',updated_at=now()
   WHERE id=${draftId} AND status='approved_for_payment' AND payment_status<>'paid'`;
 }
 const workspace=await workspaceForDraft(sql,draftId);
 if(!workspace?.account?.active)return {status:'email_unavailable',url:link.url};
 try{
  const email=await sendPaymentApprovedEmail(workspace,link.url,cents,d.plan,d.days,link.id);
  return {status:'ready',email_status:email.status,url:link.url,amount_cents:cents};
 }catch(e){
  console.error('DParranda Stripe approval mail unavailable',e?.name||'Error');
  return {status:'ready',email_status:'failed',url:link.url,amount_cents:cents};
 }
}
