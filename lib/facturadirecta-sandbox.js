// Real FacturaDirecta sandbox connector. All writes verify company.sandbox before proceeding.
// Never invokes Stripe, touches the legal issuer, or sends to real customers.
import {request,createOrFindContact,createLegalInvoice,getLegalInvoice,createCorrectionInvoice,
 createReplacementInvoice,sendLegalInvoice} from './facturadirecta-invoices.js';
const PRICE={local:1900,zona:4900,insular:9900};
const MARK='DParranda SANDBOX TEST';
const MAIL='prueba@example.com'; // Reserved domain; sandbox redirects mail to its owner.
const today=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const choose=(rows,pred,explicit)=>{const matches=(rows||[]).filter(pred);return explicit?matches.find(r=>(r.id||r.serie)===explicit)||null:matches.length===1?matches[0]:null};
function auth(){
 const api_key=String(process.env.FACTURADIRECTA_SANDBOX_API_KEY||'').trim();
 const company_id=String(process.env.FACTURADIRECTA_SANDBOX_COMPANY_ID||'').trim();
 if(api_key&&company_id&&(api_key===process.env.FACTURADIRECTA_API_KEY||company_id===process.env.FACTURADIRECTA_COMPANY_ID))
  throw Error('Sandbox debe usar una empresa y clave diferentes de producción.');
 return {api_key,company_id};
}
async function inspect(){
 const base=auth();
 if(!/^[a-zA-Z0-9_-]{3,40}\.[a-zA-Z0-9_-]{12,100}$/.test(base.api_key)||!/^com_[a-zA-Z0-9_-]{10,80}$/.test(base.company_id))
  return {verified:false,ready:false,enabled:false,message:'Configura FACTURADIRECTA_SANDBOX_API_KEY y FACTURADIRECTA_SANDBOX_COMPANY_ID en Vercel.'};
 const company=(await request(base,'GET','/settings/company'))?.content?.company;
 if(company?.sandbox!==true||company.id!==base.company_id)
  throw Error('BLOQUEADO: el proveedor no confirma que esta empresa sea un sandbox. No se ha escrito nada.');
 const [taxes,series]=await Promise.all([request(base,'GET','/settings/taxes/sales'),
  request(base,'GET','/settings/series/invoice')]);
 const tax=choose(taxes.items,t=>t.taxGroup==='IGIC'&&Number(t.value)===0.07&&t.current===true&&
  t.category==='standard_vat'&&t.autoApplied!==true&&t.selectorFlags?.includes('line'),
  process.env.FACTURADIRECTA_SANDBOX_IGIC_SALES_TAX_ID);
 const inv=choose(series.items,s=>s.invoiceType==='complete',process.env.FACTURADIRECTA_SANDBOX_INVOICE_SERIES);
 const rect=choose(series.items,s=>s.invoiceType==='complete_correction',process.env.FACTURADIRECTA_SANDBOX_RECTIFICATION_SERIES);
 const account=process.env.FACTURADIRECTA_SANDBOX_ACCOUNT_CODE||'700000';
 const cfg={...base,tax_id:tax?.id||'',series:inv?.serie||'',rectification_series:rect?.serie||'',
  theme:inv?.theme||'',account};
 const ready=!!cfg.tax_id&&!!cfg.series&&/^[0-9]{3,12}$/.test(account);
 const enabled=process.env.FACTURADIRECTA_SANDBOX_ENABLED==='true';
 return {cfg,verified:true,ready,enabled,company_name:String(company.brand||company.name||'Pruebas').slice(0,100),
  igic_tax_id:cfg.tax_id,invoice_series:cfg.series,rectification_series:cfg.rectification_series,
  missing:[...(!cfg.tax_id?['No hay un único IGIC 7% vigente: configura el impuesto en el sandbox.']:[]),
   ...(!cfg.series?['Configura una serie ordinaria completa en el sandbox.']:[]),
   ...(!cfg.rectification_series?['Configura una serie rectificativa completa en el sandbox.']:[]),
   ...(!enabled?['Configura FACTURADIRECTA_SANDBOX_ENABLED=true para crear documentos de prueba.']:[])],
  message:'Empresa de FacturaDirecta Sandbox verificada mediante la API oficial.'};
}
export async function facturadirectaSandboxStatus(){
 const {cfg,...publicData}=await inspect();return publicData;
}
export async function verifiedSandboxBillingProvider(){
 const state=await inspect();
 requireEnabled(state);
 if(!state.cfg.rectification_series)throw Error('Falta serie de rectificativas para el circuito completo en sandbox');
 return {...state.cfg,sandbox:true};
}

function verifiedDocument(invoice){
 const m=invoice?.content?.main;
 if(!m?.lines?.some(l=>String(l.text||'').includes(MARK)))
  throw Error('Solo pueden rectificarse o enviarse documentos creados como pruebas DParranda Sandbox.');
 return m;
}
function requireEnabled(s){
 if(!s.verified||!s.ready||!s.enabled)
  throw Error('Sandbox no preparado: revisa variables, IGIC y serie, o pulsa Comprobar conexión.');
}
function testCustomer(id,corrected=false){
 return {draft_id:'sandbox-'+id,company_name:corrected?'Cliente corregido ficticio DParranda':'Cliente ficticio DParranda',
  customer_tax_id:corrected?'12345678Z':'B12345674',billing_email:MAIL,
  billing_address:'Calle Pruebas '+(corrected?'2':'1'),billing_postal:'35001',
  billing_city:'Las Palmas de Gran Canaria',billing_region:'Las Palmas',billing_country:'ES'};
}
export async function facturadirectaSandboxAction(input={}){
 const state=await inspect();requireEnabled(state);
 const cfg=state.cfg,action=String(input.action||''),testId=String(input.test_id||'');
 if(!/^[a-zA-Z0-9_-]{20,70}$/.test(testId))throw Error('Identificador de prueba inválido');
 if(action==='invoice'){
  const plan=String(input.plan||''),days=Number(input.days);
  if(!Object.hasOwn(PRICE,plan)||![30,60].includes(days))throw Error('Tarifa de prueba inválida');
  const customer=testCustomer(testId),contact=await createOrFindContact(cfg,customer);
  const cents=PRICE[plan]*(days/30),row={...customer,plan,days,placement:'banner',
   total_cents:cents,title:MARK+' sin validez fiscal',issue_date:today()};
  const result=await createLegalInvoice(cfg,row,contact);
  const detail=await getLegalInvoice(cfg,result.id);verifiedDocument(detail);
  let pdf_url='',pdf_message='';
  try{
   const pdf=await request(cfg,'PUT','/invoices/'+encodeURIComponent(result.id)+'/pdf');
   const value=String(pdf?.url||'');
   if(/^https:\/\//.test(value))pdf_url=value;
   else pdf_message='El proveedor no devolvió una URL segura para el PDF.';
  }catch{
   pdf_message='No se pudo generar el PDF mediante la API; abre la factura en FacturaDirecta Sandbox.';
  }
  return {sandbox:true,action,id:result.id,url:result.url||detail.webUrl||'',pdf_url,pdf_message,amount_cents:cents,
   message:'Factura de prueba creada en FacturaDirecta Sandbox. No se ha cobrado ni emitido nada fiscalmente válido.'};
 }
 const id=String(input.invoice_id||'');
 const original=await getLegalInvoice(cfg,id),main=verifiedDocument(original);
 if(action==='send'){
  await sendLegalInvoice(cfg,id,MAIL,'hola@dparranda.es','sandbox-'+testId+'-'+id);
  return {sandbox:true,action,id,message:'Envío de prueba aceptado por FacturaDirecta Sandbox; redirigido al usuario de pruebas.'};
 }
 if(action!=='rectify')throw Error('Acción de sandbox no admitida');
 const kind=String(input.kind||'');
 if(!['billing_details','refund_full','refund_partial'].includes(kind)||!cfg.rectification_series)
  throw Error('Rectificativa de sandbox inválida o sin serie configurada.');
 const total=Math.round(Number(main.total)*100);
 if(!Number.isSafeInteger(total)||total<2)throw Error('El total original no se ha podido confirmar');
 const adjustment={id:'sandbox-'+testId,kind,amount_cents:kind==='refund_partial'?Math.floor(total/2):total,
  issue_date:today(),reason:'Prueba de rectificación sin reembolso de dinero',
  title:MARK,plan:'zona',days:30,placement:'banner'};
 let replacementContact;
 if(kind==='billing_details')replacementContact=await createOrFindContact(cfg,testCustomer('corrected-'+testId,true));
 const correction=await createCorrectionInvoice(cfg,adjustment,id,main.contact);
 let replacement=null;
 if(kind==='billing_details')replacement=await createReplacementInvoice(cfg,adjustment,replacementContact);
 return {sandbox:true,action,kind,correction_invoice_id:correction.id,
  replacement_invoice_id:replacement?.id||null,message:'Rectificativa de prueba generada en FacturaDirecta Sandbox. Sin devolución de dinero en Stripe.'};
}
