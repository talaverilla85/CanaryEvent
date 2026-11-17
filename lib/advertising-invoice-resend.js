import {providerConfiguration,request,getLegalInvoice} from './facturadirecta-invoices.js';
import {sandboxBillingMode} from './advertising-invoice-issuance.js';
import {verifiedSandboxBillingProvider} from './facturadirecta-sandbox.js';
// Read and resend only an existing provider invoice linked to a paid Stripe campaign.
const EMAIL=/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;
export function allowedInvoiceEmailRecipient(sandbox,original,recipient,testRecipient){
 const expected=sandbox?testRecipient:original;
 if(!EMAIL.test(String(expected||''))||String(recipient||'').trim().toLowerCase()!==String(expected).trim().toLowerCase())
  throw Error(sandbox?'Sandbox: solo se permite enviar al correo de pruebas.':'Solo se permite el correo fiscal original.');
 return String(expected).trim();
}
function safeUrl(raw){
 let u;try{u=new URL(String(raw||''))}catch{return ''}
 if(u.protocol!=='https:'||u.username||u.password)return '';
 const host=u.hostname.toLowerCase();
 if(host==='localhost'||host.endsWith('.localhost')||host.endsWith('.local')||
    /^\d+\.\d+\.\d+\.\d+$/.test(host)||host.includes(':'))return '';
 return u.href;
}
async function linked(sql,rawId){
 const id=Number(rawId),sandbox=sandboxBillingMode();
 if(!Number.isSafeInteger(id)||id<1)throw Error('Contratación inválida');
 const [row]=await sql`SELECT r.draft_id,r.company_name,r.billing_email,r.total_cents,d.title,
 d.payment_status,d.stripe_checkout_session_id,d.paid_at,
 i.provider_invoice_id,i.provider AS invoice_provider
 FROM advertising_invoice_reviews r
 JOIN advertiser_campaign_drafts d ON d.id=r.draft_id
 JOIN advertising_invoice_issuance i ON i.draft_id=r.draft_id WHERE r.draft_id=${id}`;
 if(!row||row.payment_status!=='paid'||!row.paid_at||
  !String(row.stripe_checkout_session_id||'').startsWith(sandbox?'cs_test_':'cs_live_')||
  row.invoice_provider!==(sandbox?'facturadirecta-sandbox':'facturadirecta')||
  !/^inv_[A-Za-z0-9_-]+$/.test(String(row.provider_invoice_id||'')))
  throw Error('No hay factura emitida vinculada a un pago de este entorno.');
 const cfg=sandbox?await verifiedSandboxBillingProvider():providerConfiguration();
 if(!sandbox&&!cfg.configured)throw Error('Proveedor fiscal real no habilitado.');
 const vendor=await getLegalInvoice(cfg,row.provider_invoice_id);
 if(!vendor?.content?.main?.contact||!Array.isArray(vendor.content.main.lines))
  throw Error('El proveedor no confirma el documento.');
 return {row,cfg,sandbox};
}
async function pdfUrl(cfg,id,mode){
 const pdf=await request(cfg,'PUT','/invoices/'+encodeURIComponent(id)+'/pdf',{mode});
 const url=safeUrl(pdf?.url);
 if(!url)throw Error('Factura existente sin URL de PDF válida.');
 return url;
}
export async function existingInvoiceDocument(sql,id){
 const {row,cfg,sandbox}=await linked(sql,id);
 const url=await pdfUrl(cfg,row.provider_invoice_id,'inline');
 const recipient=sandbox?String(process.env.RESEND_TEST_RECIPIENT||'').trim():row.billing_email;
 const enabled=String(process.env.RESEND_API_KEY||'').startsWith('re_')&&
  (sandbox?EMAIL.test(recipient):
  process.env.RESEND_INVOICE_EMAILS_ENABLED==='true'&&
  process.env.RESEND_CUSTOMER_EMAILS_ENABLED==='true'&&EMAIL.test(String(process.env.RESEND_FROM_EMAIL||'')));
 return {id:row.draft_id,url,provider_invoice_id:row.provider_invoice_id,
  sandbox,recipient,resend_available:enabled,customer:row.company_name,title:row.title,
  amount_cents:row.total_cents};
}
export async function sendExistingInvoiceResend(sql,input={}){
 const {row,cfg,sandbox}=await linked(sql,input.id);
 if(!sandbox&&(process.env.RESEND_INVOICE_EMAILS_ENABLED!=='true'||
 process.env.RESEND_CUSTOMER_EMAILS_ENABLED!=='true'))
  throw Error('Envío fiscal real mediante Resend desactivado.');
 const recipient=allowedInvoiceEmailRecipient(sandbox,row.billing_email,input.recipient,
  String(process.env.RESEND_TEST_RECIPIENT||'').trim());
 const from=sandbox?'onboarding@resend.dev':String(process.env.RESEND_FROM_EMAIL||'').trim();
 if(!EMAIL.test(from)||!String(process.env.RESEND_API_KEY||'').startsWith('re_'))
  throw Error('Resend no configurado.');
 const key=String(input.attempt_key||'');
 if(!/^[a-f0-9]{32}$/.test(key))throw Error('Referencia de envío inválida.');
 const url=await pdfUrl(cfg,row.provider_invoice_id,'attachment');
 const ctrl=new AbortController(),timeout=setTimeout(()=>ctrl.abort(),15000);
 let response;
 try{
  response=await fetch('https://api.resend.com/emails',{method:'POST',signal:ctrl.signal,
   headers:{Authorization:'Bearer '+process.env.RESEND_API_KEY,'Content-Type':'application/json',
    'Idempotency-Key':'dp-invoice-'+row.draft_id+'-'+key},
   body:JSON.stringify({
    from:'DParranda <'+from+'>',to:[recipient],
    subject:'D’Parranda · Copia de tu factura publicitaria',
    html:'<p>Te adjuntamos una copia de la factura de D’Parranda.</p>'+
     (sandbox?'<p>PRUEBA SANDBOX · SIN VALIDEZ FISCAL.</p>':''),
    text:'Factura de publicidad D’Parranda'+(sandbox?' · PRUEBA SIN VALIDEZ FISCAL':''),
    attachments:[{filename:'factura-'+row.provider_invoice_id+'.pdf',path:url}]
   })
  });
 }finally{clearTimeout(timeout)}
 const body=await response.json().catch(()=>({}));
 if(!response.ok||typeof body.id!=='string'||!body.id)
  throw Error('Resend rechazó la petición (HTTP '+response.status+').');
 return {accepted:true,resend_id:body.id,recipient,sandbox,
  message:'Resend aceptó la copia del PDF. La entrega final aún no está confirmada.'};
}
