// Private invoice view and manually confirmed delivery using Resend.
// FacturaDirecta remains the invoice/PDF provider; Resend is ONLY the email transport.
// Never create a new invoice in this module, and never deliver sandbox documents to clients.
import {providerConfiguration,getLegalInvoice,request} from './facturadirecta-invoices.js';
import {verifiedSandboxBillingProvider} from './facturadirecta-sandbox.js';
import {sandboxBillingMode,invoiceIssuanceReadiness} from './advertising-invoice-issuance.js';
import {resendTestConfigured} from './resend-test.js';
import {loadInvoiceIssuer} from './advertising-invoice-issuer.js';

const EMAIL=/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeEmail=v=>String(v||'').trim().toLowerCase();
const validateId=v=>{
 const n=Number(v);
 if(!Number.isSafeInteger(n)||n<1)throw Error('Identificador de contratación inválido');
 return n;
};
const validInvoiceId=v=>/^inv_[a-zA-Z0-9_-]{6,95}$/.test(String(v||''));
const stripeSessionForMode=(r,sandbox)=>
 String(r.stripe_checkout_session_id||'').startsWith(sandbox?'cs_test_':'cs_live_');
const invoiceProviderForMode=sandbox=>sandbox?'facturadirecta-sandbox':'facturadirecta';
const liveResendReady=()=>
 process.env.DPARRANDA_INVOICE_RESEND_LIVE_ENABLED==='true'&&
 process.env.RESEND_CUSTOMER_EMAILS_ENABLED==='true'&&
 /^re_[A-Za-z0-9_-]+$/.test(String(process.env.RESEND_API_KEY||''))&&
 EMAIL.test(safeEmail(process.env.RESEND_FROM_EMAIL))&&
 !/@resend\.dev$/i.test(String(process.env.RESEND_FROM_EMAIL||''));

async function loadRecord(sql,id){
 const [r]=await sql`SELECT r.draft_id,r.total_cents,r.company_name,r.billing_email,
   r.customer_tax_id,r.billing_address,r.billing_city,r.billing_postal,r.billing_region,
   r.billing_country,r.review_status,
   d.title,d.payment_status,d.paid_at,d.stripe_checkout_session_id,
   i.status AS issuance_status,i.provider AS invoice_provider,
   i.provider_invoice_id,i.provider_invoice_url,i.issued_at,i.sent_at
   FROM advertising_invoice_reviews r
   JOIN advertiser_campaign_drafts d ON d.id=r.draft_id
   LEFT JOIN advertising_invoice_issuance i ON i.draft_id=r.draft_id
   WHERE r.draft_id=${id}`;
 return r||null;
}
function requireExisting(r,sandbox){
 if(!r||r.payment_status!=='paid'||!r.paid_at||
   !stripeSessionForMode(r,sandbox)||!validInvoiceId(r.provider_invoice_id)||
   r.invoice_provider!==invoiceProviderForMode(sandbox)||
   !['issued','sending','sent'].includes(r.issuance_status))
  throw Error('La contratación no tiene una factura emitida y un pago verificado del entorno actual.');
}
async function pdfUrl(cfg,id,mode='inline'){
 const reply=await request(cfg,'PUT','/invoices/'+encodeURIComponent(id)+'/pdf',{mode});
 const path=String(reply?.url||'');
 let url;
 try{url=new URL(path)}catch{}
 if(!url||url.protocol!=='https:'||url.username||url.password||url.hostname==='localhost'||
   /(?:^|\.)localhost$/.test(url.hostname)||/^(?:127\.|10\.|192\.168\.|169\.254\.)/.test(url.hostname))
  throw Error('FacturaDirecta no ha proporcionado un enlace seguro al PDF.');
 return url.href;
}
async function companyConfig(sandbox){
 if(sandbox)return verifiedSandboxBillingProvider();
 const cfg=providerConfiguration();
 if(!cfg.configured)throw Error('La facturación real no está configurada.');
 return cfg;
}
async function lastDelivery(sql,id){
 const [table]=await sql`SELECT to_regclass('public.advertising_invoice_email_deliveries') AS relation`;
 if(!table?.relation)return null;
 const [r]=await sql`SELECT recipient,sandbox,status,created_at,resend_id
 FROM advertising_invoice_email_deliveries
 WHERE draft_id=${id} ORDER BY created_at DESC LIMIT 1`;
 return r||null;
}
export async function advertisingInvoiceDocument(sql,draftId){
 const id=validateId(draftId),r=await loadRecord(sql,id);
 if(!r)return {found:false,issued:false,can_send:false,message:'No existe un borrador de factura para esta contratación.'};
 const sandbox=sandboxBillingMode(),isPaid=r.payment_status==='paid'&&!!r.paid_at;
 const matched=isPaid&&stripeSessionForMode(r,sandbox)&&r.invoice_provider===invoiceProviderForMode(sandbox);
 const issued=matched&&validInvoiceId(r.provider_invoice_id);
 let link='',pdf_error='';
 if(issued){
  try{
   const cfg=await companyConfig(sandbox);
   await getLegalInvoice(cfg,r.provider_invoice_id);
   link=await pdfUrl(cfg,r.provider_invoice_id,'inline');
  }catch(err){pdf_error=String(err?.message||'No se pudo consultar el PDF').slice(0,360)}
 }
 const latest=issued?await lastDelivery(sql,id):null;
 const canSend=!!issued&&(sandbox?resendTestConfigured():liveResendReady());
 return {found:true,draft_id:id,title:r.title,company_name:r.company_name,
  total_cents:r.total_cents,paid:isPaid,sandbox,environment_matches:matched,
  issued:!!issued,invoice_id:issued?r.provider_invoice_id:null,
  invoice_status:r.issuance_status||null,issued_at:r.issued_at||null,
  billing_email:sandbox?'':r.billing_email,
  pdf_url:link,pdf_error,can_send:canSend&&!!link,
  send_note:!issued?'Factura pendiente: primero revisa y emite el documento desde las herramientas de facturación.':
   !link?'No se puede enviar sin obtener antes el PDF de FacturaDirecta.':
   sandbox?'Modo Sandbox: el PDF solo se enviará a tu correo de pruebas de Resend.':
   !liveResendReady()?'El envío real por Resend está desactivado hasta completar la configuración fiscal y del dominio.':
   'Envío manual con PDF adjunto a través de Resend.',
  last_delivery:latest?{recipient:latest.sandbox?'Cuenta de pruebas Resend':latest.recipient,
   status:latest.status,date:latest.created_at}:null
 };
}
async function ensureLog(sql){
 await sql`CREATE TABLE IF NOT EXISTS advertising_invoice_email_deliveries (
  id BIGSERIAL PRIMARY KEY,
  request_key TEXT NOT NULL UNIQUE,
  draft_id BIGINT NOT NULL REFERENCES advertising_invoice_reviews(draft_id) ON DELETE RESTRICT,
  provider_invoice_id TEXT NOT NULL,
  recipient TEXT NOT NULL,
  sandbox BOOLEAN NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('sending','accepted','error')),
  resend_id TEXT,
  error_note TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
 )`;
}
export async function sendAdvertisingInvoiceResend(sql,body){
 const id=validateId(body?.id),key=String(body?.request_key||'');
 if(!UUID.test(key)||body?.confirmation!=='ENVIAR')
  throw Error('Confirma el envío de la factura desde Administración.');
 const sandbox=sandboxBillingMode(),r=await loadRecord(sql,id);
 requireExisting(r,sandbox);
 if(sandbox&&!resendTestConfigured())
  throw Error('Configura RESEND_API_KEY y RESEND_TEST_RECIPIENT para la prueba.');
 if(!sandbox){
  const ready=await invoiceIssuanceReadiness(sql);
  if(!ready.can_issue||!liveResendReady())
   throw Error('El envío real por Resend no está autorizado. Verifica alta fiscal, Stripe, dominio y habilitación explícita.');
 }
 const {issuer}=await loadInvoiceIssuer(sql);
 const to=sandbox?safeEmail(process.env.RESEND_TEST_RECIPIENT):
  safeEmail(body?.recipient||r.billing_email);
 if(!EMAIL.test(to))throw Error('El correo del destinatario no es válido.');
 const cc=sandbox?'':safeEmail(issuer.copy_email);
 if(!sandbox&&!EMAIL.test(cc))throw Error('Configura tu correo fiscal para recibir la copia.');
 // Avoid changing the recipient of a sandbox invoice to a real customer.
 const from=sandbox?'DParranda <onboarding@resend.dev>':
  'DParranda <'+safeEmail(process.env.RESEND_FROM_EMAIL)+'>';
 const cfg=await companyConfig(sandbox);
 const origin=await getLegalInvoice(cfg,r.provider_invoice_id);
 if(origin.content?.uuid!==r.provider_invoice_id)throw Error('La factura no coincide con FacturaDirecta.');
 // Generate a fresh temporary URL; it is only ever supplied by the verified provider.
 const pdf=await pdfUrl(cfg,r.provider_invoice_id,'attachment');
 await ensureLog(sql);
 const [inserted]=await sql`INSERT INTO advertising_invoice_email_deliveries
  (request_key,draft_id,provider_invoice_id,recipient,sandbox,status)
  VALUES (${key},${id},${r.provider_invoice_id},${to},${sandbox},'sending')
  ON CONFLICT(request_key) DO NOTHING RETURNING id`;
 if(!inserted){
  const [old]=await sql`SELECT draft_id,provider_invoice_id,recipient,sandbox,status,resend_id
    FROM advertising_invoice_email_deliveries WHERE request_key=${key}`;
  if(!old||Number(old.draft_id)!==id||old.provider_invoice_id!==r.provider_invoice_id||
   old.recipient!==to||old.sandbox!==sandbox)
   throw Error('El identificador ya corresponde a otro envío.');
  if(old.status==='accepted')return {accepted:true,already:true,message_id:old.resend_id,
   message:'Este envío ya fue aceptado por Resend. No se ha duplicado.'};
  if(old.status==='sending')throw Error('El envío está en curso. Comprueba el estado antes de repetirlo.');
  await sql`UPDATE advertising_invoice_email_deliveries SET status='sending',updated_at=now(),error_note=''
    WHERE request_key=${key} AND status='error'`;
 }
 try{
  const subject='D’Parranda · Factura de tu contratación publicitaria';
  const bodyHtml='<p>Hola,</p><p>Adjuntamos la factura de tu contratación de publicidad en <strong>D’Parranda</strong>.</p>'+
   '<p><strong>Campaña:</strong> '+esc(r.title||'Publicidad')+'</p>'+
   '<p><strong>Importe:</strong> '+(Number(r.total_cents)/100).toFixed(2)+' €</p>'+
   (sandbox?'<p><strong>PRUEBA SANDBOX · DOCUMENTO SIN VALIDEZ FISCAL.</strong></p>':'')+
   '<p>Gracias por confiar en D’Parranda.</p>';
  const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),15000);
  let response;
  try{
   response=await fetch('https://api.resend.com/emails',{
    method:'POST',signal:controller.signal,headers:{
     Authorization:'Bearer '+process.env.RESEND_API_KEY,
     'Content-Type':'application/json','Idempotency-Key':'dparranda-factura-'+key
    },
    body:JSON.stringify({
     from,to:[to],...(cc&&cc!==to?{cc:[cc]}:{}),
     subject,html:bodyHtml,
     attachments:[{filename:'factura-'+r.provider_invoice_id.slice(4)+'.pdf',path:pdf}]
    })
   });
  }finally{clearTimeout(timeout)}
  const result=await response.json().catch(()=>({}));
  if(!response.ok||typeof result?.id!=='string'||!result.id)
   throw Error('Resend no ha aceptado el envío (HTTP '+response.status+'). Revisa la configuración del remitente.');
  await sql`UPDATE advertising_invoice_email_deliveries
    SET status='accepted',resend_id=${result.id},error_note='',updated_at=now()
    WHERE request_key=${key}`;
  return {accepted:true,sandbox,recipient:sandbox?'Cuenta de pruebas Resend':to,
   resend_id:result.id,message:sandbox?
    'Resend aceptó el PDF para tu correo de pruebas. No se ha escrito a ningún anunciante.':
    'Resend aceptó el correo con el PDF de la factura. Comprueba la entrega en el panel de Resend.'};
 }catch(err){
  await sql`UPDATE advertising_invoice_email_deliveries
   SET status='error',error_note=${String(err?.message||'Error de envío').slice(0,300)},updated_at=now()
   WHERE request_key=${key}`;
  throw err;
 }
}
