import {loadInvoiceIssuer,issuerComplete} from './advertising-invoice-issuer.js';
import {providerConfiguration,billingProviderStatus,isCanaryBuyer,createOrFindContact,createLegalInvoice,sendLegalInvoice} from './facturadirecta-invoices.js';
import {stripeMode,stripePaymentsReady} from './stripe-advertising.js';
import {verifiedSandboxBillingProvider} from './facturadirecta-sandbox.js';

// Three immutable conditions before a fiscal issue:
// (1) a signed Stripe live payment in the database;
// (2) an admin-reviewed draft and a verified tax regime;
// (3) a dedicated fiscal invoicing provider configured for the issuer.
export const sandboxBillingMode=()=>process.env.DPARRANDA_BILLING_MODE==='sandbox';
export async function invoiceIssuanceReadiness(sql){
 if(sandboxBillingMode()){
  let connected=false,correctionSeries='',error='';
  try{
   const cfg=await verifiedSandboxBillingProvider();
   connected=true;correctionSeries=cfg.rectification_series;
  }catch(e){error=String(e.message||'FacturaDirecta Sandbox no configurado').slice(0,180)}
  const stripeTest=stripeMode()==='test'&&stripePaymentsReady()&&
   String(process.env.STRIPE_SECRET_KEY||'').startsWith('sk_test_');
  return {sandbox_mode:true,issuer_complete:false,igic_general_confirmed:false,
   provider_connected:connected,provider_name:'FacturaDirecta Sandbox',
   stripe_live:false,stripe_test:stripeTest,can_issue:connected&&stripeTest,
   review_first:true,automatic_issuance:false,
   rectifications_ready:connected&&!!correctionSeries,
   missing:[...(error?[error]:[]),
    ...(!stripeTest?['Configura Stripe test con webhook test firmado en Vercel.']:[])],
   message:'Modo pruebas: transacciones Stripe test, documentos FacturaDirecta Sandbox, sin validez fiscal.'};
 }
 const {issuer,data_complete}=await loadInvoiceIssuer(sql);
 const provider=billingProviderStatus();
 const correctionSeries=String(providerConfiguration().rectification_series||'');
 const confirmed=issuer.general_igic_confirmed===true;
 const stripeLive=stripeMode()==='live'&&stripePaymentsReady();
 return {sandbox_mode:false,issuer_complete:data_complete,igic_general_confirmed:confirmed,
  provider_connected:provider.connected,provider_name:provider.provider,
  stripe_live:stripeLive,
  can_issue:data_complete&&confirmed&&provider.connected&&stripeLive,
  review_first:true,automatic_issuance:false,
  rectifications_ready:provider.connected&&/^[A-Za-z0-9#._-]{1,35}$/.test(correctionSeries),
  missing:[
   ...(!data_complete?['Completa y guarda los datos fiscales del autónomo.']:[]),
   ...(!confirmed?['Confirma que estás en régimen general del IGIC, sin REPEP.']:[]),
   ...(!provider.connected?['Conecta y valida FacturaDirecta en Vercel.']:[]),
   ...(!stripeLive?['Stripe real no está activado.']:[])
  ]};
}
export async function issueCheckedInvoice(sql,idInput,{skipProviderSend=false}={}){
 const id=Number(idInput);
 if(!Number.isSafeInteger(id)||id<=0)throw Error('Identificador de documento inválido');
 const readiness=await invoiceIssuanceReadiness(sql);
 const cfg=readiness.sandbox_mode?(readiness.can_issue?await verifiedSandboxBillingProvider():null):providerConfiguration();
 const providerName=readiness.sandbox_mode?'facturadirecta-sandbox':'facturadirecta';
 if(!readiness.can_issue||!(cfg?.sandbox||cfg?.configured))
  throw Error('No se puede emitir: faltan datos fiscales, confirmar régimen general o conectar el proveedor y Stripe real.');
 const [r]=await sql`SELECT r.*,d.title,d.plan,d.days,d.placement,d.payment_status,
    d.stripe_checkout_session_id,d.paid_at
   FROM advertising_invoice_reviews r JOIN advertiser_campaign_drafts d ON d.id=r.draft_id
   WHERE r.draft_id=${id}`;
 if(!r||r.review_status!=='checked'||r.payment_status!=='paid'||
  !String(r.stripe_checkout_session_id||'').startsWith(readiness.sandbox_mode?'cs_test_':'cs_live_')||
  !r.paid_at)
  throw Error('La factura requiere pago real confirmado y datos revisados.');
 if(!r.company_name||!r.customer_tax_id||!r.billing_email||
  !r.billing_address||!r.billing_city||!r.billing_region||
  !isCanaryBuyer(r))
  throw Error('El destinatario requiere revisión fiscal: este flujo del 7 % solo admite direcciones fiscales canarias.');
 const [existing]=await sql`SELECT draft_id,provider,status,provider_invoice_id,provider_invoice_url,provider_contact_id,
    processing_started_at,issue_date
   FROM advertising_invoice_issuance WHERE draft_id=${id}`;
 if(existing&&existing.provider!==providerName)
  throw Error('No se puede cruzar una factura de sandbox con una de producción');
 if(existing?.status==='sent')
  return {status:'sent',already:true,invoice_url:existing.provider_invoice_url};
 if(existing?.provider_invoice_id){
  if(skipProviderSend)return {status:'issued',already:true,
   invoice_url:existing.provider_invoice_url,
   message:'Factura ya emitida. Puedes descargar y reenviar el PDF desde la contratación.'};
  return await sendIssuedInvoice(sql,id,r,cfg,existing.provider_invoice_id,existing.provider_invoice_url);
 }
 // Database claim excludes duplicate concurrent issuance (web serverless requests).
 const [claimed]=await sql`INSERT INTO advertising_invoice_issuance
   (draft_id,provider,status,processing_started_at,attempt_count,issue_date)
   VALUES (${id},${providerName},'issuing',now(),1,(now() AT TIME ZONE 'Atlantic/Canary')::date)
   ON CONFLICT(draft_id) DO UPDATE SET status='issuing',
   processing_started_at=now(),attempt_count=advertising_invoice_issuance.attempt_count+1,
   error_note='',updated_at=now()
   WHERE advertising_invoice_issuance.provider=${providerName} AND ((advertising_invoice_issuance.status IN ('pending','error')
    AND advertising_invoice_issuance.provider_invoice_id IS NULL)
    OR (advertising_invoice_issuance.status='issuing'
    AND advertising_invoice_issuance.processing_started_at<now()-interval '20 minutes'))
   RETURNING draft_id,provider_contact_id,provider_invoice_id,issue_date`;
 if(!claimed)throw Error('La emisión ya está en curso. Comprueba el estado antes de reintentar.');
 try{
  const contact=claimed.provider_contact_id||await createOrFindContact(cfg,
   cfg.sandbox?{...r,billing_email:'prueba@example.com'}:r);
  if(!claimed.provider_contact_id)
   await sql`UPDATE advertising_invoice_issuance SET provider_contact_id=${contact},updated_at=now()
    WHERE draft_id=${id} AND status='issuing'`;
  const issued=await createLegalInvoice(cfg,{...r,issue_date:claimed.issue_date},contact);
  const [saved]=await sql`UPDATE advertising_invoice_issuance SET
   status='issued',provider_invoice_id=${issued.id},
   provider_invoice_url=${issued.url},issued_at=now(),
   error_note='',updated_at=now()
   WHERE draft_id=${id} AND status='issuing' RETURNING provider_invoice_id`;
  if(!saved)throw Error('No fue posible guardar el identificador externo. Comprueba el proveedor antes de reintentar.');
  if(skipProviderSend)return {status:'issued',already:false,invoice_url:issued.url,
   message:'Factura emitida en FacturaDirecta. Usa el botón Factura para ver y enviar el PDF mediante Resend.'};
  return await sendIssuedInvoice(sql,id,r,cfg,issued.id,issued.url);
 }catch(err){
  await sql`UPDATE advertising_invoice_issuance
   SET status=CASE WHEN provider_invoice_id IS NULL THEN 'error' ELSE 'issued' END,
    error_note=${String(err?.message||'Error del proveedor').slice(0,340)},updated_at=now()
   WHERE draft_id=${id} AND status IN ('issuing','sending','issued')`;
  throw err;
 }
}
async function sendIssuedInvoice(sql,id,r,cfg,providerId,providerUrl=''){
 const [claimed]=await sql`UPDATE advertising_invoice_issuance SET status='sending',
  processing_started_at=now(),attempt_count=attempt_count+1,updated_at=now()
  WHERE draft_id=${id} AND provider_invoice_id=${providerId}
   AND (status='issued' OR
    (status='sending' AND processing_started_at<now()-interval '20 minutes'))
  RETURNING provider_invoice_id`;
 if(!claimed)throw Error('Factura enviada o envío en curso. Actualiza el listado.');
 const {issuer}=await loadInvoiceIssuer(sql);
 try{
  const sent=await sendLegalInvoice(cfg,providerId,
   cfg.sandbox?'prueba@example.com':r.billing_email,
   cfg.sandbox?'prueba@example.com':issuer.copy_email,id);
  const [updated]=await sql`UPDATE advertising_invoice_issuance SET
   status='sent',sent_at=now(),error_note='',updated_at=now()
   WHERE draft_id=${id} AND status='sending' RETURNING draft_id`;
  if(!updated)throw Error('La respuesta de envío no pudo registrarse. Revisa el proveedor.');
  return {status:'sent',sent:sent.sent,invoice_url:providerUrl,already:false,
   message:'Factura emitida y enviada por el proveedor fiscal al cliente, con copia al emisor.'};
 }catch(err){
  await sql`UPDATE advertising_invoice_issuance SET
   status='issued',error_note=${String(err?.message||'Fallo de envío').slice(0,340)},updated_at=now()
   WHERE draft_id=${id} AND status='sending'`;
  throw err;
 }
}
