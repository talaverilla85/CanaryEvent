// Reversible preparation; irreversible money/fiscal work only after admin confirmation.
// No customer can call these functions through the public website.
import {safeText} from './admin-auth.js';
import {stripeMode, stripePaymentsReady} from './stripe-advertising.js';
import {invoiceIssuanceReadiness} from './advertising-invoice-issuance.js';
import {providerConfiguration,getLegalInvoice,createCorrectionInvoice,
 createOrFindContact,createReplacementInvoice,sendLegalInvoice} from './facturadirecta-invoices.js';
import {loadInvoiceIssuer} from './advertising-invoice-issuer.js';

const legalEmail=v=>/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(String(v||''));
const kindNames={billing_details:'Corrección de datos fiscales',refund_full:'Devolución completa',
 refund_partial:'Devolución parcial'};
const numericId=v=>{
 const n=Number(v);
 if(!Number.isSafeInteger(n)||n<1)throw Error('Operación no válida');
 return n;
};
function newDetails(input){
 const fields=['company_name','customer_tax_id','billing_email','billing_address',
  'billing_postal','billing_city','billing_region','billing_country'];
 return Object.fromEntries(fields.map(k=>[k,safeText(input?.[k],k==='billing_address'?220:180)]));
}
function requireFiscalDetails(d){
 if(!d.company_name||!d.customer_tax_id||!legalEmail(d.billing_email)||
  !d.billing_address||!d.billing_postal||!d.billing_city||!d.billing_region||
  !['ES','España','ESPAÑA','Spain'].includes(String(d.billing_country||'')))
  throw Error('Completa todos los datos fiscales del nuevo destinatario antes de rectificar');
}
// Stripe requests use persisted checkout session ID to retrieve the real PaymentIntent.
// No Stripe refund is allowed using an ID typed by the browser.
async function stripeRequest(method,path,body,idempotency){
 const mode=stripeMode(),key=String(process.env.STRIPE_SECRET_KEY||'');
 if(mode!=='live'||!stripePaymentsReady()||!key.startsWith('sk_live_'))
  throw Error('Las devoluciones están bloqueadas hasta activar y verificar Stripe real');
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
 try{
  const result=await fetch('https://api.stripe.com/v1'+path,{
   method,signal:controller.signal,
   headers:{Authorization:'Bearer '+key,
    'Content-Type':'application/x-www-form-urlencoded',
    ...(idempotency?{'Idempotency-Key':idempotency}:{})},
   ...(body?{body:new URLSearchParams(body).toString()}:{})
  });
  const payload=await result.json().catch(()=>({}));
  if(!result.ok)throw Error('Stripe no pudo completar la operación (HTTP '+result.status+')');
  return payload;
 }finally{clearTimeout(timeout)}
}
async function checkoutPaymentIntent(review){
 const sessionId=String(review.stripe_checkout_session_id||'');
 if(!/^cs_live_[A-Za-z0-9]+$/.test(sessionId))throw Error('Falta la referencia verificada del pago real');
 const s=await stripeRequest('GET','/checkout/sessions/'+encodeURIComponent(sessionId));
 if(s.id!==sessionId||s.livemode!==true||s.payment_status!=='paid'||
  s.currency!=='eur'||Number(s.amount_total)!==Number(review.total_cents))
  throw Error('Los datos del cobro no coinciden con Stripe. Revisa la operación antes de reembolsar.');
 const pi=typeof s.payment_intent==='string'?s.payment_intent:s.payment_intent?.id;
 if(!/^pi_[A-Za-z0-9]+$/.test(pi||'')||
  (review.stripe_payment_intent_id&&review.stripe_payment_intent_id!==pi))
  throw Error('Stripe ha devuelto un PaymentIntent distinto del esperado');
 return pi;
}
export async function listInvoiceAdjustments(sql){
 const records=await sql`SELECT a.id,a.draft_id,a.kind,a.amount_cents,a.reason,
  a.replacement_details,a.status,a.stripe_refund_id,a.correction_invoice_id,
  a.correction_invoice_url,a.replacement_invoice_id,a.replacement_invoice_url,
  a.error_note,a.created_at,a.completed_at,a.correction_sent_at,a.replacement_sent_at,
  r.company_name,r.billing_email,r.total_cents,
  d.title,d.payment_status,i.provider_invoice_id AS original_invoice_id
  FROM advertising_invoice_adjustments a
  JOIN advertising_invoice_reviews r ON r.draft_id=a.draft_id
  JOIN advertiser_campaign_drafts d ON d.id=a.draft_id
  JOIN advertising_invoice_issuance i ON i.draft_id=a.draft_id
  ORDER BY a.created_at DESC LIMIT 150`;
 return {adjustments:records,requires_admin_confirmation:true,auto_refunds:false};
}
export async function createInvoiceAdjustment(sql,body){
 const draftId=numericId(body?.draft_id),kind=String(body?.kind||'');
 const reason=safeText(body?.reason,700),key=String(body?.request_key||'');
 if(!Object.hasOwn(kindNames,kind)||reason.length<10)
  throw Error('Indica el tipo y un motivo de al menos diez caracteres');
 if(!/^[A-Za-z0-9_-]{12,100}$/.test(key))throw Error('Identificador de solicitud inválido');
 const [r]=await sql`SELECT r.draft_id,r.total_cents,r.company_name,r.customer_tax_id,
  r.billing_email,r.billing_address,r.billing_postal,r.billing_city,
  r.billing_region,r.billing_country,r.review_status,
  d.payment_status,i.provider_invoice_id,i.status AS invoice_status
  FROM advertising_invoice_reviews r
  JOIN advertiser_campaign_drafts d ON d.id=r.draft_id
  JOIN advertising_invoice_issuance i ON i.draft_id=r.draft_id
  WHERE r.draft_id=${draftId}`;
 if(!r||r.review_status!=='checked'||r.invoice_status!=='sent'||!r.provider_invoice_id)
  throw Error('Solo puedes corregir una factura original ya emitida y enviada');
 if(!['paid','refunded'].includes(r.payment_status))
  throw Error('La contratación no tiene un pago confirmado');
 let amount=Number(body?.amount_cents),replacement={};
 if(kind==='billing_details'){
  if(r.payment_status==='refunded')throw Error('No se pueden cambiar los datos de una contratación totalmente devuelta');
  amount=Number(r.total_cents);
  replacement=newDetails(body?.replacement_details);
  requireFiscalDetails(replacement);
  const [prior]=await sql`SELECT id FROM advertising_invoice_adjustments WHERE
    draft_id=${draftId} AND kind='billing_details' AND status NOT IN ('rejected','refund_failed') LIMIT 1`;
  if(prior)throw Error('Ya hay una rectificación de datos en este anuncio; comprueba el historial');
 }else{
  if(!Number.isSafeInteger(amount)||amount<=0)throw Error('El importe de devolución no es válido');
  const [used]=await sql`SELECT COALESCE(SUM(amount_cents),0)::int AS cents
    FROM advertising_invoice_adjustments
    WHERE draft_id=${draftId} AND kind IN ('refund_full','refund_partial')
    AND status NOT IN ('rejected','refund_failed')`;
  const left=Number(r.total_cents)-Number(used?.cents||0);
  if(amount>left)throw Error('La devolución solicitada supera el importe que queda disponible');
  if(kind==='refund_full'&&(amount!==Number(r.total_cents)||left!==Number(r.total_cents)))
   throw Error('Para una devolución completa no puede existir otra devolución previa');
  if(kind==='refund_partial'&&amount>=left)
   throw Error('Para devolver el importe restante completo utiliza devolución completa o revisa las anteriores');
 }
 // database unique index prevents overlapping adjustments for one original invoice.
 const [created]=await sql`INSERT INTO advertising_invoice_adjustments
   (request_key,draft_id,kind,amount_cents,reason,replacement_details)
   VALUES (${key},${draftId},${kind},${amount},${reason},${JSON.stringify(replacement)}::jsonb)
   ON CONFLICT(request_key) DO NOTHING
   RETURNING id,draft_id,kind,status`;
 if(!created)throw Error('Esta solicitud ya existe. Actualiza la bandeja antes de intentarlo de nuevo');
 return {created:true,...created,message:'Solicitud registrada para revisión. No se ha devuelto dinero ni emitido ninguna rectificativa.'};
}
export async function rejectInvoiceAdjustment(sql,idInput){
 const id=numericId(idInput);
 const [updated]=await sql`UPDATE advertising_invoice_adjustments SET
    status='rejected',updated_at=now() WHERE id=${id} AND status='pending_review'
    RETURNING id`;
 if(!updated)throw Error('Solo puedes rechazar solicitudes que aún no se hayan ejecutado');
 return {rejected:true,id,message:'Solicitud rechazada sin devolver dinero ni crear facturas.'};
}
async function persist(sql,id,status,error=''){
 await sql`UPDATE advertising_invoice_adjustments SET status=${status},
    error_note=${String(error).slice(0,340)},updated_at=now() WHERE id=${id}`;
}
async function disableFullyRefundedAds(sql,r){
 await sql`UPDATE advertiser_campaign_drafts SET payment_status='refunded',
  status='cancelled',updated_at=now() WHERE id=${r.draft_id} AND payment_status='paid'`;
 if(r.published_ad_id)
  await sql`UPDATE ad_campaigns SET enabled=FALSE,updated_at=now()
   WHERE id=${r.published_ad_id} AND kind='paid'`;
 if(r.published_event_id)
  await sql`UPDATE sponsored_events SET enabled=FALSE,updated_at=now()
   WHERE id=${r.published_event_id} AND advertiser_draft_id=${r.draft_id}`;
 if(r.source_lead_id)
  await sql`UPDATE advertising_enquiries SET payment_status='refunded'
   WHERE id=${r.source_lead_id}`;
}
async function ensureRefund(sql,adjustment,r){
 let refund;
 if(adjustment.stripe_refund_id){
  refund=await stripeRequest('GET','/refunds/'+encodeURIComponent(adjustment.stripe_refund_id));
 }else{
  const intent=await checkoutPaymentIntent(r);
  refund=await stripeRequest('POST','/refunds',{
   payment_intent:intent,amount:String(adjustment.amount_cents),
   reason:'requested_by_customer',
   'metadata[dparranda_adjustment_id]':String(adjustment.id)
  },'dparranda-approved-refund-'+adjustment.id+'-v1');
 }
 if(!/^re_[A-Za-z0-9]+$/.test(refund?.id||'')||
  Number(refund.amount)!==Number(adjustment.amount_cents)||
  !['pending','succeeded','failed','canceled','requires_action'].includes(refund.status))
  throw Error('Stripe devolvió una respuesta de devolución inesperada');
 const existing=adjustment.stripe_refund_id;
 if(existing&&refund.id!==existing)throw Error('Stripe cambió el identificador de la devolución');
 await sql`UPDATE advertising_invoice_adjustments SET stripe_refund_id=${refund.id},
   status=${refund.status==='succeeded'?'refund_succeeded':refund.status==='pending'?'refund_pending':'refund_failed'},
   updated_at=now() WHERE id=${adjustment.id}`;
 if(refund.status==='pending')return {status:'refund_pending',message:'Stripe está procesando la devolución; no se ha emitido todavía la rectificativa. Usa «Consultar y continuar».'};
 if(refund.status!=='succeeded')return {status:'refund_failed',message:'La devolución no se completó en Stripe. Revisa el estado y el método de devolución antes de continuar.'};
 if(adjustment.kind==='refund_full')await disableFullyRefundedAds(sql,r);
 return null;
}
async function invoiceCorrection(sql,adjustment,r,cfg){
 const original=await getLegalInvoice(cfg,r.original_invoice_id);
 const contact=String(original.content?.main?.contact||'');
 if(!/^con_[A-Za-z0-9_-]+$/.test(contact))
  throw Error('El proveedor no devuelve el contacto fiscal de la factura original');
 const date=String(adjustment.issue_date).slice(0,10);
 const fiscal={...adjustment,title:r.title,issue_date:date};
 let negativeId=adjustment.correction_invoice_id;
 if(!negativeId){
  const negative=await createCorrectionInvoice(cfg,fiscal,r.original_invoice_id,contact);
  negativeId=negative.id;
  await sql`UPDATE advertising_invoice_adjustments SET
   correction_invoice_id=${negative.id},correction_invoice_url=${negative.url},
   status='correction_issued',updated_at=now() WHERE id=${adjustment.id}`;
 }
 let replacementId=adjustment.replacement_invoice_id;
 if(adjustment.kind==='billing_details'&&!replacementId){
  const details={...adjustment.replacement_details,draft_id:'adj-'+adjustment.id};
  requireFiscalDetails(details);
  const newContact=await createOrFindContact(cfg,{
   customer_tax_id:details.customer_tax_id,company_name:details.company_name,
   billing_email:details.billing_email,billing_address:details.billing_address,
   billing_postal:details.billing_postal,billing_city:details.billing_city,
   billing_region:details.billing_region,billing_country:details.billing_country,
   draft_id:'adj-'+adjustment.id
  });
  const replacement=await createReplacementInvoice(cfg,fiscal,newContact);
  replacementId=replacement.id;
  await sql`UPDATE advertising_invoice_adjustments SET
   replacement_invoice_id=${replacement.id},replacement_invoice_url=${replacement.url},
   status='replacement_issued',updated_at=now() WHERE id=${adjustment.id}`;
 }
 // Both documents must be created before mail; retry uses separate idempotency keys.
 const {issuer}=await loadInvoiceIssuer(sql);
 const sendTo=adjustment.kind==='billing_details'?
  adjustment.replacement_details.billing_email:r.billing_email;
 if(!adjustment.correction_sent_at){
  await sendLegalInvoice(cfg,negativeId,sendTo,issuer.copy_email,
   'correction-'+adjustment.id);
  await sql`UPDATE advertising_invoice_adjustments SET correction_sent_at=now(),updated_at=now()
   WHERE id=${adjustment.id}`;
 }
 if(adjustment.kind==='billing_details'&&!adjustment.replacement_sent_at){
  await sendLegalInvoice(cfg,replacementId,sendTo,issuer.copy_email,
   'replacement-'+adjustment.id);
  await sql`UPDATE advertising_invoice_adjustments SET replacement_sent_at=now(),updated_at=now()
   WHERE id=${adjustment.id}`;
 }
 const [done]=await sql`UPDATE advertising_invoice_adjustments SET
   status='completed',completed_at=now(),error_note='',updated_at=now()
   WHERE id=${adjustment.id} RETURNING id`;
 return {status:'completed',id:done?.id,negative_invoice_id:negativeId,
  replacement_invoice_id:replacementId||null,
  message:'Facturación rectificada y envío solicitado al proveedor para cliente y copia administrativa.'};
}
export async function processInvoiceAdjustment(sql,idInput){
 const id=numericId(idInput),readiness=await invoiceIssuanceReadiness(sql),cfg=providerConfiguration();
 if(!readiness.can_issue||!cfg.configured||
  !/^[A-Za-z0-9_-]{2,35}$/.test(cfg.rectification_series||''))
  throw Error('La operación requiere FacturaDirecta con serie de rectificativas, IGIC verificado y Stripe real.');
 const [r]=await sql`SELECT a.*,r.total_cents,r.company_name,r.customer_tax_id,
   r.billing_email,r.billing_address,r.billing_postal,r.billing_city,r.billing_region,
   r.billing_country,r.stripe_checkout_session_id,r.stripe_payment_intent_id,
   d.title,d.plan,d.days,d.placement,d.source_lead_id,d.payment_status,
   d.published_ad_id,d.published_event_id,i.provider_invoice_id AS original_invoice_id,
   i.status AS original_invoice_status
  FROM advertising_invoice_adjustments a
  JOIN advertising_invoice_reviews r ON r.draft_id=a.draft_id
  JOIN advertiser_campaign_drafts d ON d.id=a.draft_id
  JOIN advertising_invoice_issuance i ON i.draft_id=a.draft_id
  WHERE a.id=${id}`;
 if(!r||!r.original_invoice_id||r.original_invoice_status!=='sent'||
  !['paid','refunded'].includes(r.payment_status))
  throw Error('La factura original no está emitida o el pago no está confirmado');
 if(r.status==='completed')return {status:'completed',already:true};
 if(['rejected','refund_failed'].includes(r.status))throw Error('Esta solicitud no está disponible para ejecutar');
 const [claim]=await sql`UPDATE advertising_invoice_adjustments SET
  status='processing',processing_started_at=now(),reviewed_at=COALESCE(reviewed_at,now()),
  error_note='',updated_at=now()
  WHERE id=${id} AND (status IN ('pending_review','needs_attention','refund_pending',
    'refund_succeeded','correction_issued','replacement_issued') OR
    (status='processing' AND processing_started_at<now()-interval '20 minutes'))
  RETURNING id`;
 if(!claim)throw Error('Operación en curso: actualiza el listado antes de reintentar');
 try{
  if(r.kind!=='billing_details'&&!r.correction_invoice_id){
   const pending=await ensureRefund(sql,r,r);
   if(pending)return pending;
  }
  const output=await invoiceCorrection(sql,r,r,cfg);
  return output;
 }catch(err){
  await persist(sql,id,'needs_attention',String(err?.message||'Error durante la operación'));
  throw err;
 }
}
