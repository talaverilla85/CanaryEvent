// FacturaDirecta REST API adapter. The vendor is responsible for invoice numbering,
// SIF/VeriFactu compliance, rendering the official PDF and sending customer+copy mail.
// No request is made unless the provider, taxpayer regime and individual transaction are ready.
// Docs: https://www.facturadirecta.com/desarrolladores/api/referencia/invoices/
export function providerConfiguration(){
 const key=String(process.env.FACTURADIRECTA_API_KEY||''),
  company=String(process.env.FACTURADIRECTA_COMPANY_ID||''),
  tax=String(process.env.FACTURADIRECTA_IGIC_SALES_TAX_ID||''),
  series=String(process.env.FACTURADIRECTA_INVOICE_SERIES||''),
  account=String(process.env.FACTURADIRECTA_ACCOUNT_CODE||''),
  confirmed=process.env.FACTURADIRECTA_FISCAL_SETUP_CONFIRMED==='true';
 const configured=/^[A-Za-z0-9_-]{3,40}\.[A-Za-z0-9_-]{12,100}$/.test(key)&&
  /^[A-Za-z0-9_-]{6,90}$/.test(company)&&
  /^[A-Za-z0-9_-]{2,90}$/.test(tax)&&series.length>0&&series.length<=35&&
  /^[0-9]{3,12}$/.test(account)&&confirmed;
 return {configured,confirmed,provider:'facturadirecta',api_key:key,
  company_id:company,tax_id:tax,series,account,
  rectification_series:String(process.env.FACTURADIRECTA_RECTIFICATION_SERIES||'')};
}
export function billingProviderStatus(){
 const cfg=providerConfiguration();
 return {provider:'FacturaDirecta',connected:cfg.configured,
  message:cfg.configured?'Proveedor fiscal configurado, pendiente de validación del cliente y del pago.':
   'Falta conectar FacturaDirecta: empresa, clave API, serie e impuesto IGIC, y confirmar su configuración fiscal.'};
}
export function isCanaryBuyer(billing){
 const country=String(billing.billing_country||'').trim().toUpperCase();
 const postal=String(billing.billing_postal||'').replace(/\s/g,'');
 // Only the Canary Islands can use the 7% IGIC route by default.
 // All other destinations require manual accountant review and dedicated tax configuration.
 return ['ES','ESPAÑA','SPAIN'].includes(country)&&/^(35|38)[0-9]{3}$/.test(postal);
}
export async function request(cfg,method,path,body,idempotency){
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),15000);
 try{
  const response=await fetch('https://app.facturadirecta.com/api/'+encodeURIComponent(cfg.company_id)+path,{
   method,signal:controller.signal,
   headers:{'facturadirecta-api-key':cfg.api_key,
    'Accept':'application/json','Content-Type':'application/json',
    ...(idempotency?{'Idempotency-Key':idempotency}:{})},
   ...(body===undefined?{}:{body:JSON.stringify(body)})
  });
  let content={};
  try{content=await response.json()}catch{}
  if(!response.ok)throw new Error('FacturaDirecta rechazó '+method+' '+path+' (HTTP '+response.status+').');
  return content;
 }finally{clearTimeout(timeout)}
}
export async function createOrFindContact(cfg,invoice){
 const tax=invoice.customer_tax_id.replace(/[\s-]/g,'').toUpperCase();
 const list=await request(cfg,'GET','/contacts?'+new URLSearchParams({fiscalId:tax}));
 const existing=(list.items||[]).find(item=>
  String(item.content?.main?.fiscalId||'').toUpperCase()===tax);
 if(existing?.content?.uuid){
  const registered=String(existing.content.main?.name||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim(),
    requested=String(invoice.company_name||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toUpperCase().trim();
  if(registered!==requested)throw new Error('El cliente con ese NIF ya existe en FacturaDirecta con otro nombre fiscal; revisa sus datos en el proveedor.');
  return existing.content.uuid;
 }
 const country=String(invoice.billing_country||'ES').toUpperCase()==='ESPAÑA'?'ES':String(invoice.billing_country||'ES').toUpperCase();
 const payload={content:{type:'contact',main:{
  name:invoice.company_name,fiscalId:tax,fiscalIdCountry:country,
  email:invoice.billing_email,address:invoice.billing_address,
  zipcode:invoice.billing_postal,city:invoice.billing_city,
  region:invoice.billing_region,country
 }}};
 const created=await request(cfg,'POST','/contacts',payload,
  'dp-contact-'+String(invoice.draft_id).padStart(12,'0'));
 const id=created.content?.uuid;
 if(!/^con_[A-Za-z0-9_-]+$/.test(id||''))throw new Error('FacturaDirecta no ha confirmado el cliente');
 return id;
}
export function buildInvoicePayload(cfg,row,contact){
 const total=Number(row.total_cents)/100;
 const day=row.issue_date instanceof Date?row.issue_date.toISOString().slice(0,10):String(row.issue_date||'').slice(0,10);
 if(!/^20\d{2}-\d{2}-\d{2}$/.test(day))throw new Error('No se ha fijado la fecha fiscal de emisión');
 if(!Number.isSafeInteger(Number(row.total_cents))||total<=0)
  throw new Error('Importe de factura inválido');
 const text='Publicidad D’Parranda '+({local:'local',zona:'zona',insular:'insular'}[row.plan]||'')+
  ' · '+row.days+' días · '+(row.placement==='evento'?'evento patrocinado':'banner')+
  ' · '+row.title;
 return {content:{main:{
  draft:false,external:false,voided:false,simplified:false,contact,currency:'EUR',
  date:day,dueDate:day,fiscalPosition:'general',
  account:cfg.account,theme:cfg.theme||process.env.FACTURADIRECTA_INVOICE_THEME||'default',
  docNumber:{series:cfg.series},
  taxIncludedPrices:true,
  lines:[{account:cfg.account,quantity:1,unitPrice:total,discount:0,discountRate:0,
   lineTotal:total,tax:[cfg.tax_id],text}]
 }}};
}
export async function createLegalInvoice(cfg,row,contact){
 const response=await request(cfg,'POST','/invoices',buildInvoicePayload(cfg,row,contact),
  'dp-invoice-paid-'+String(row.draft_id).padStart(12,'0'));
 const id=response.content?.uuid;
 if(!/^inv_[A-Za-z0-9_-]+$/.test(id||''))throw new Error('El proveedor no confirmó la factura definitiva');
 // Never attach receipt or issue a second invoice in Stripe.
 return {id,url:typeof response.webUrl==='string'?response.webUrl:''};
}
export async function sendLegalInvoice(cfg,invoiceId,to,cc,draftId){
 if(!/^inv_[A-Za-z0-9_-]+$/.test(invoiceId)||!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(to))
  throw new Error('Factura o correo no válidos');
 if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(cc))throw new Error('Correo de copia no válido');
 await request(cfg,'PUT','/invoices/'+encodeURIComponent(invoiceId)+'/send',{
  to,cc:to===cc?'':cc,
  subject:'D’Parranda · Factura por tu contratación publicitaria'
 },'dp-invoice-send-'+String(draftId).padStart(12,'0'));
 return {sent:true};
}

// Official documented correction flow: POST /invoices with main.correctedInvoice.
// The original remains registered, the correcting invoice has its own serial number.
export function buildCorrectionPayload(cfg,{originalInvoiceId,originalContact,amountCents,
  issueDate,reason,kind='refund_full',title='Publicidad D’Parranda'}){
 const n=Number(amountCents),date=String(issueDate||'').slice(0,10);
 if(!/^inv_[A-Za-z0-9_-]+$/.test(String(originalInvoiceId||''))||
   !/^con_[A-Za-z0-9_-]+$/.test(String(originalContact||''))||
   !Number.isSafeInteger(n)||n<=0||!/^20\d{2}-\d{2}-\d{2}$/.test(date))
  throw Error('Rectificativa inválida o sin factura de origen');
 if(!/^[A-Za-z0-9#._-]{1,35}$/.test(String(cfg.rectification_series||'')))
  throw Error('Falta la serie fiscal de facturas rectificativas en FacturaDirecta');
 if(!['billing_details','refund_full','refund_partial'].includes(kind))
  throw Error('Tipo de rectificación desconocido');
 const reasonCode=kind==='billing_details'?'R4':'R1';
 const amount=-(n/100);
 return {content:{main:{
  date,dueDate:date,currency:'EUR',draft:false,external:false,voided:false,
  simplified:false,contact:originalContact,
  fiscalPosition:'general',account:cfg.account,
  theme:cfg.theme||process.env.FACTURADIRECTA_INVOICE_THEME||'default',
  docNumber:{series:cfg.rectification_series},
  correctedInvoice:originalInvoiceId,
  verifactu:{TipoFactura:reasonCode},
  taxIncludedPrices:true,
  lines:[{account:cfg.account,quantity:1,unitPrice:amount,lineTotal:amount,
    discount:0,discountRate:0,tax:[cfg.tax_id],
    text:'Rectificación de '+String(title).slice(0,120)+' · '+String(reason).slice(0,200)}]
 }}};
}
export async function getLegalInvoice(cfg,id){
 if(!/^inv_[A-Za-z0-9_-]+$/.test(String(id||'')))throw Error('Factura de origen inválida');
 const result=await request(cfg,'GET','/invoices/'+encodeURIComponent(id));
 if(result?.content?.uuid!==id||!result?.content?.main)
  throw Error('Factura original no confirmada en FacturaDirecta');
 return result;
}
export async function createCorrectionInvoice(cfg,adjustment,original,contact){
 const body=buildCorrectionPayload(cfg,{
  originalInvoiceId:original,originalContact:contact,
  amountCents:adjustment.amount_cents,issueDate:adjustment.issue_date,
  reason:adjustment.reason,kind:adjustment.kind,title:adjustment.title
 });
 const response=await request(cfg,'POST','/invoices',body,
  'dparranda-correct-'+String(adjustment.id).padStart(12,'0')+'-v1');
 const id=response.content?.uuid;
 if(!/^inv_[A-Za-z0-9_-]+$/.test(String(id||'')))throw Error('FacturaDirecta no confirmó la rectificativa');
 return {id,url:typeof response.webUrl==='string'?response.webUrl:''};
}
export async function createReplacementInvoice(cfg,adjustment,contact){
 const row={draft_id:'replacement-'+adjustment.id,total_cents:adjustment.amount_cents,
  plan:adjustment.plan,days:adjustment.days,placement:adjustment.placement,
  title:adjustment.title,issue_date:adjustment.issue_date};
 const response=await request(cfg,'POST','/invoices',buildInvoicePayload(cfg,row,contact),
  'dparranda-replacement-'+String(adjustment.id).padStart(12,'0')+'-v1');
 const id=response.content?.uuid;
 if(!/^inv_[A-Za-z0-9_-]+$/.test(String(id||'')))throw Error('FacturaDirecta no confirmó la factura con los nuevos datos');
 return {id,url:typeof response.webUrl==='string'?response.webUrl:''};
}

export async function verifyFacturaDirectaConnection(){
 const cfg=providerConfiguration();
 if(!cfg.api_key||!cfg.company_id)throw Error('Configura primero la API key y la empresa de FacturaDirecta en Vercel');
 // Safe GET test only, never creates a client, invoice or email.
 await request(cfg,'GET','/apiKeyInfo');
 return {connected:true,provider:'FacturaDirecta',
  series_configured:!!cfg.series,rectification_series_configured:!!cfg.rectification_series,
  tax_configured:!!cfg.tax_id,account_configured:!!cfg.account,
  confirmed:cfg.confirmed,
  message:'Autenticación con FacturaDirecta correcta. Antes de emitir, comprueba series, IGIC, VeriFactu y permisos de escritura en el proveedor.'};
}
