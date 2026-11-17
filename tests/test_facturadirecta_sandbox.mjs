// Offline test of the actual Stripe-test -> FacturaDirecta-sandbox issuance path.
import test from 'node:test';
import assert from 'node:assert/strict';
import {facturadirectaSandboxStatus} from '../lib/facturadirecta-sandbox.js';
import {invoiceIssuanceReadiness,issueCheckedInvoice} from '../lib/advertising-invoice-issuance.js';
import {processInvoiceAdjustment} from '../lib/advertising-invoice-adjustments.js';
import {request} from '../lib/facturadirecta-invoices.js';
const env={
 DPARRANDA_BILLING_MODE:'sandbox',DPARRANDA_STRIPE_MODE:'test',
 DPARRANDA_STRIPE_PAYMENTS_ENABLED:'true',
 STRIPE_SECRET_KEY:'sk_test_test_only_offline',STRIPE_WEBHOOK_SECRET:'whsec_test_only_offline',
 FACTURADIRECTA_SANDBOX_API_KEY:'ABC123.'+'q'.repeat(32),
 FACTURADIRECTA_SANDBOX_COMPANY_ID:'com_sandboxtest1234567890',
 FACTURADIRECTA_SANDBOX_ENABLED:'true'
};
const saved=Object.fromEntries(Object.keys(env).map(k=>[k,process.env[k]]));
function activate(){Object.assign(process.env,env)}
function restore(){for(const k of Object.keys(env)){
 if(saved[k]===undefined)delete process.env[k];else process.env[k]=saved[k]
}}
test.after(restore);
const fakeResponse=(url,options={})=>{
 const path=String(url),method=options.method;
 if(path.endsWith('/settings/company'))return Response.json({content:{company:{
  id:env.FACTURADIRECTA_SANDBOX_COMPANY_ID,sandbox:true,name:'Empresa de pruebas'}}});
 if(path.endsWith('/settings/taxes/sales'))return Response.json({items:[{
  id:'S_IGIC_7',taxGroup:'IGIC',value:0.07,category:'standard_vat',current:true,
  autoApplied:false,selectorFlags:['line']} ]});
 if(path.endsWith('/settings/series/invoice'))return Response.json({items:[
  {serie:'F-##-',invoiceType:'complete',theme:'thm_test'},
  {serie:'R-##-',invoiceType:'complete_correction',theme:'thm_test'}]});
 if(path.includes('/contacts?'))return Response.json({items:[]});
 if(path.endsWith('/contacts')&&method==='POST')return Response.json({content:{uuid:'con_fake123'}});
 if(path.endsWith('/invoices')&&method==='POST')return Response.json({
  content:{uuid:'inv_fake123'},webUrl:'https://example.invalid/invoice/sandbox'});
 if(path.includes('/invoices/inv_fake123/send'))return Response.json({ok:true});
 throw Error('URL inesperada en simulador de red: '+path);
};
const issuer={legal_name:'Emisor solo pruebas',tax_id:'12345678Z',
 billing_address:'Calle de ejemplo 1',billing_postal:'35118',
 billing_city:'Agüimes',billing_region:'Las Palmas',billing_country:'España',
 copy_email:'hola@dparranda.es',general_igic_confirmed:false};
test('ninguna clave de sandbox permite escribir en empresa real',async()=>{
 activate();
 let n=0;const original=globalThis.fetch;
 globalThis.fetch=async(url,opts)=>{n++;
  if(String(url).endsWith('/settings/company'))return Response.json({content:{
   company:{id:env.FACTURADIRECTA_SANDBOX_COMPANY_ID,sandbox:false}}});
  throw Error('No debe accederse a impuestos ni emitir');
 };
 try{
  await assert.rejects(facturadirectaSandboxStatus(),/BLOQUEADO/);
  assert.equal(n,1);
 }finally{globalThis.fetch=original;restore()}
});
test('modo test comprueba API, serie, impuesto y Stripe antes de autorizar facturas de prueba',async()=>{
 activate();const old=globalThis.fetch;
 globalThis.fetch=async(url,opts)=>fakeResponse(url,opts);
 try{
  const s=await facturadirectaSandboxStatus();
  assert.equal(s.verified,true);assert.equal(s.ready,true);
  assert.equal(s.igic_tax_id,'S_IGIC_7');
  assert.equal(s.invoice_series,'F-##-');
  const ready=await invoiceIssuanceReadiness(async()=>[issuer]);
  assert.equal(ready.sandbox_mode,true);
  assert.equal(ready.can_issue,true);
  assert.equal(ready.stripe_live,false);
  assert.equal(ready.rectifications_ready,true);
  assert.equal(JSON.stringify(s).includes(env.FACTURADIRECTA_SANDBOX_API_KEY),false);
 }finally{globalThis.fetch=old;restore()}
});
test('pago test revisado emite solo factura sandbox y correo de prueba sin publicar anuncio',async()=>{
 activate();let existing=null;const hits=[];
 const old=globalThis.fetch;
 globalThis.fetch=async(url,opts={})=>{
  hits.push({url:String(url),method:opts.method||'GET',body:opts.body?JSON.parse(opts.body):null});
  return fakeResponse(url,opts);
 };
 const review={draft_id:33,title:'Publicidad de ensayo',plan:'zona',days:30,placement:'banner',
  company_name:'Anunciante ficticio',customer_tax_id:'00000000T',billing_email:'externo@example.invalid',
  billing_address:'Calle de ejemplo 2',billing_postal:'35001',
  billing_city:'Las Palmas de Gran Canaria',billing_region:'Las Palmas',billing_country:'ES',
  total_cents:4900,review_status:'checked',payment_status:'paid',paid_at:new Date(),
  stripe_checkout_session_id:'cs_test_ABC123'};
 const sql=async(strings,...values)=>{
  const q=strings.join('?');
  if(q.includes('FROM advertising_invoice_issuer'))return [issuer];
  if(q.includes('FROM advertising_invoice_reviews r JOIN advertiser_campaign_drafts d'))return [review];
  if(q.includes('FROM advertising_invoice_issuance WHERE draft_id'))return existing?[existing]:[];
  if(q.includes('INSERT INTO advertising_invoice_issuance')){
   assert.ok(values.includes('facturadirecta-sandbox'));
   existing={provider:'facturadirecta-sandbox',status:'issuing',provider_invoice_id:null};
   return [{provider_contact_id:null,issue_date:'2026-11-17'}];
  }
  if(q.includes('UPDATE advertising_invoice_issuance SET provider_contact_id'))return [];
  if(q.includes("status='issued',provider_invoice_id=")){
   existing={provider:'facturadirecta-sandbox',status:'issued',provider_invoice_id:'inv_fake123',
    provider_invoice_url:'https://example.invalid/invoice/sandbox'};
   return [{provider_invoice_id:'inv_fake123'}];
  }
  if(q.includes("UPDATE advertising_invoice_issuance SET status='sending'"))return [{provider_invoice_id:'inv_fake123'}];
  if(q.includes("status='sent',sent_at=")){
   existing={...existing,status:'sent'};return [{draft_id:33}];
  }
  throw Error('SQL inesperado '+q.slice(0,130));
 };
 try{
  const one=await issueCheckedInvoice(sql,33);
  assert.equal(one.status,'sent');
  assert.equal((await issueCheckedInvoice(sql,33)).already,true);
  assert.equal(hits.filter(x=>x.url.endsWith('/invoices')&&x.method==='POST').length,1);
  const created=hits.find(x=>x.url.endsWith('/invoices')&&x.method==='POST');
  assert.equal(created.body.content.type,'invoice');
  assert.equal(created.body.content.main.fiscalPosition,'emp');
  assert.equal(created.body.content.main.lines[0].unitPrice,49);
  assert.equal(created.body.content.main.docNumber.series,'F-##-');
  const mail=hits.find(x=>x.url.endsWith('/send'));
  assert.equal(mail.body.to,'prueba@example.com');
  assert.equal(mail.body.cc,'');
  assert.ok(!hits.some(x=>x.url.includes('com_production')));
 }finally{globalThis.fetch=old;restore()}
});
test('no acepta Stripe live ni credenciales reales en modo sandbox',async()=>{
 activate();process.env.DPARRANDA_STRIPE_MODE='live';
 process.env.STRIPE_SECRET_KEY='sk_live_wrong_mode';
 const old=globalThis.fetch;globalThis.fetch=async(url,opts)=>fakeResponse(url,opts);
 try{
  const ready=await invoiceIssuanceReadiness(async()=>[issuer]);
  assert.equal(ready.can_issue,false);
 }finally{globalThis.fetch=old;restore()}
});

test('la devolución Stripe TEST genera rectificativa en FacturaDirecta SANDBOX sin tocar producción',async()=>{
 activate();const old=globalThis.fetch;
 let stripeRefunds=0,providerCorrections=0;const calls=[];
 const row={id:20,draft_id:33,kind:'refund_partial',amount_cents:1200,
  total_cents:4900,reason:'Incidencia con campaña de publicidad de prueba',status:'pending_review',
  stripe_checkout_session_id:'cs_test_ABC123',stripe_payment_intent_id:'pi_testABC123',
  original_invoice_id:'inv_original',original_invoice_status:'sent',
  original_invoice_provider:'facturadirecta-sandbox',
  payment_status:'paid',company_name:'Prueba',billing_email:'externo@example.invalid',
  title:'Anuncio de prueba',plan:'zona',days:30,placement:'banner',issue_date:'2026-11-17',
  correction_invoice_id:null,correction_sent_at:null};
 globalThis.fetch=async(url,options={})=>{
  const u=String(url),method=options.method||'GET';calls.push(u);
  if(u.endsWith('/settings/company')||u.endsWith('/settings/taxes/sales')||
    u.endsWith('/settings/series/invoice'))return fakeResponse(u,options);
  if(u.includes('stripe.com/v1/checkout/sessions/'))return Response.json({
   id:'cs_test_ABC123',livemode:false,amount_total:4900,currency:'eur',
   payment_status:'paid',payment_intent:'pi_testABC123'});
  if(u.endsWith('stripe.com/v1/refunds')&&method==='POST'){
   stripeRefunds++;return Response.json({id:'re_testREFUND',amount:1200,status:'succeeded'});
  }
  if(u.endsWith('/invoices/inv_original')&&method==='GET')
   return Response.json({content:{uuid:'inv_original',main:{contact:'con_testORIGINAL'}}});
  if(u.endsWith('/invoices')&&method==='POST'){
   providerCorrections++;return Response.json({content:{uuid:'inv_testRECTIF'}});}
  if(u.endsWith('/invoices/inv_testRECTIF/send'))return Response.json({ok:true});
  throw Error('HTTP inesperado '+u);
 };
 const sql=async(parts,...v)=>{
  const q=parts.join('?');
  if(q.includes('FROM advertising_invoice_adjustments a'))return [row];
  if(q.includes('FROM advertising_invoice_issuer'))return [issuer];
  if(q.includes("status='processing'")&&q.includes('UPDATE advertising_invoice_adjustments SET')){
   row.status='processing';return [{id:20,issue_date:'2026-11-17'}];}
  if(q.includes('UPDATE advertising_invoice_adjustments SET stripe_refund_id=')){
   row.stripe_refund_id=v[0];row.status=v[1];return [];}
  if(q.includes('UPDATE advertising_invoice_adjustments SET\n   correction_invoice_id=')){
   row.correction_invoice_id=v[0];return [];}
  if(q.includes('UPDATE advertising_invoice_adjustments SET correction_sent_at=')){
   row.correction_sent_at=new Date();return [];}
  if(q.includes("status='completed'")&&q.includes('UPDATE advertising_invoice_adjustments')){
   row.status='completed';return [{id:20}];}
  if(q.includes('UPDATE advertising_invoice_adjustments SET status=')){
   row.status=v[0];return [];}
  throw Error('SQL inesperada '+q.slice(0,160));
 };
 try{
  const result=await processInvoiceAdjustment(sql,20);
  assert.equal(result.status,'completed');
  assert.equal(stripeRefunds,1);
  assert.equal(providerCorrections,1);
  assert.ok(calls.some(x=>x.includes(env.FACTURADIRECTA_SANDBOX_COMPANY_ID)));
  assert.equal((await processInvoiceAdjustment(sql,20)).already,true);
  assert.equal(stripeRefunds,1);
 }finally{globalThis.fetch=old;restore()}
});

test('el botón de administración puede crear un documento de sandbox verificable por API, sin Stripe',async()=>{
 activate();
 const old=globalThis.fetch,calls=[];
 globalThis.fetch=async(url,options={})=>{
  const s=String(url),method=options.method||'GET';
  calls.push({s,method,body:options.body?JSON.parse(options.body):null});
  if(s.endsWith('/invoices/inv_SANDBOX_TEST/pdf')&&method==='PUT')
   return Response.json({url:'https://app.facturadirecta.com/tmp/sandbox-test.pdf',filename:'test.pdf'});
  if(s.endsWith('/invoices/inv_SANDBOX_TEST')&&method==='GET')
   return Response.json({content:{uuid:'inv_SANDBOX_TEST',main:{
    lines:[{text:'Publicidad D’Parranda · DParranda SANDBOX TEST sin validez fiscal'}]
   }},webUrl:'https://app.facturadirecta.com/view/test-document'});
  if(s.endsWith('/invoices')&&method==='POST')
   return Response.json({content:{uuid:'inv_SANDBOX_TEST'}});
  if(s.endsWith('/contacts')&&method==='POST')
   return Response.json({content:{uuid:'con_SANDBOX_TEST'}});
  return fakeResponse(url,options);
 };
 try{
  const {facturadirectaSandboxAction}=await import('../lib/facturadirecta-sandbox.js');
  const created=await facturadirectaSandboxAction({action:'invoice',plan:'zona',days:30,
   test_id:'abc1234567890def1234567890abcd'});
  assert.equal(created.id,'inv_SANDBOX_TEST');
  assert.equal(created.amount_cents,4900);
  assert.equal(created.sandbox,true);
  assert.match(created.url,/facturadirecta\.com/);
  assert.match(created.pdf_url,/sandbox-test\.pdf/);
  assert.ok(calls.some(x=>x.s.endsWith('/invoices/inv_SANDBOX_TEST/pdf')&&x.method==='PUT'));
  const posted=calls.find(x=>x.s.endsWith('/invoices')&&x.method==='POST');
  assert.equal(posted.body.content.type,'invoice');
  assert.equal(posted.body.content.main.fiscalPosition,'emp');
  assert.equal(posted.body.content.main.taxIncludedPrices,true);
  assert.equal(posted.body.content.main.lines[0].unitPrice,49);
  assert.ok(calls.every(x=>x.s.includes(env.FACTURADIRECTA_SANDBOX_COMPANY_ID)));
  assert.ok(calls.every(x=>!x.s.includes('stripe.com')));
 }finally{globalThis.fetch=old;restore()}
});

test('la API propaga diagnóstico de validación de un contacto sin exponer credenciales',async()=>{
 const previous=globalThis.fetch;
 globalThis.fetch=async()=>Response.json({
  statusCode:400,message:'Validation failed',type:'ValidationError',
  errors:[{path:'content.main.fiscalId',message:'Formato de NIF/CIF inválido para España'}]
 },{status:400});
 try{
  await assert.rejects(
   request({company_id:'com_sandboxtest1234567890',api_key:'CREDENCIAL_SECRETA'},'POST','/contacts',{}),
   e=>{
    assert.match(e.message,/HTTP 400/);
    assert.match(e.message,/content\.main\.fiscalId/);
    assert.match(e.message,/Formato de NIF\/CIF inválido/);
    assert.ok(!e.message.includes('CREDENCIAL_SECRETA'));
    assert.ok(!e.message.includes('com_sandboxtest1234567890'));
    return true;
   }
  );
 }finally{globalThis.fetch=previous}
});

test('el cliente ficticio de sandbox usa el identificador del ejemplo oficial en lugar de ceros',async()=>{
 activate();const old=globalThis.fetch;const calls=[];
 globalThis.fetch=async(url,options={})=>{
  const s=String(url);if(s.endsWith('/invoices/inv_SANDBOX_TEST')&&options.method==='GET')
   return Response.json({content:{uuid:'inv_SANDBOX_TEST',main:{
    lines:[{text:'DParranda SANDBOX TEST sin validez fiscal'}]}}});
  if(s.endsWith('/invoices/inv_SANDBOX_TEST/pdf')&&options.method==='PUT')
   return Response.json({url:'https://app.facturadirecta.com/tmp/test.pdf'});
  if(s.endsWith('/invoices')&&options.method==='POST')
   return Response.json({content:{uuid:'inv_SANDBOX_TEST'}});
  if(s.endsWith('/contacts')&&options.method==='POST'){
   const main=JSON.parse(options.body).content.main;
   for(const field of ['name','currency','accounts','fiscalId','fiscalIdCountry','address','zipcode','city','country']){
    assert.ok(Object.hasOwn(main,field),'Falta un campo en el contacto: '+field);
   }
   assert.deepEqual(main.accounts,{client:'430000',clientCredit:'438000'});
   calls.push({value:main.fiscalId,currency:main.currency,accounts:main.accounts});
   return Response.json({content:{uuid:'con_SANDBOX_TEST'}});
  }
  return fakeResponse(url,options);
 };
 try{
  const {facturadirectaSandboxAction}=await import('../lib/facturadirecta-sandbox.js');
  await facturadirectaSandboxAction({action:'invoice',plan:'zona',days:30,
   test_id:'abc1234567890def1234567890abcd'});
  assert.deepEqual(calls,[{value:'B12345674',currency:'EUR',accounts:{client:'430000',clientCredit:'438000'}}]);
 }finally{globalThis.fetch=old;restore()}
});

test('el payload para contactos respeta la configuración contable de cada empresa',async()=>{
 const {createOrFindContact}=await import('../lib/facturadirecta-invoices.js');
 const old=globalThis.fetch;
 globalThis.fetch=async(url,options={})=>{
  if(String(url).includes('/contacts?'))return Response.json({items:[]});
  if(String(url).endsWith('/contacts')){
   const main=JSON.parse(options.body).content.main;
   assert.deepEqual(main.accounts,{client:'430001',clientCredit:'438001'});
   assert.equal(main.currency,'EUR');
   return Response.json({content:{uuid:'con_AAAAAA'}});
  }
  throw Error('Solicitud no esperada '+url);
 };
 try{
  const contact=await createOrFindContact({
   company_id:'com_sandboxtest1234567890',api_key:'Abc.'+'r'.repeat(40),
   contact_client_account:'430001',contact_client_credit_account:'438001'
  },{
   draft_id:31,customer_tax_id:'B12345674',company_name:'Cliente de pruebas',
   billing_country:'ES',billing_email:'prueba@example.com',billing_address:'Ejemplo 1',
   billing_postal:'35001',billing_city:'Las Palmas',billing_region:'Las Palmas'
  });
  assert.equal(contact,'con_AAAAAA');
 }finally{globalThis.fetch=old}
});

test('el botón PDF recupera una factura ya creada sin emitir una segunda factura',async()=>{
 activate();
 const prior=globalThis.fetch;
 const calls=[];
 globalThis.fetch=async(url,options={})=>{
  const path=String(url),method=options.method||'GET';
  calls.push({path,method});
  if(path.endsWith('/invoices/inv_existing123')&&method==='GET')
   return Response.json({content:{uuid:'inv_existing123',main:{
    lines:[{text:'Publicidad de prueba DParranda SANDBOX TEST sin validez fiscal'}]}},
    webUrl:'https://3.facturadirecta.com/company/sandbox/invoice'});
  if(path.endsWith('/invoices/inv_existing123/pdf')&&method==='PUT')
   return Response.json({url:'https://files.facturadirecta.com/invoice/test.pdf',filename:'test.pdf'});
  return fakeResponse(url,options);
 };
 try{
  const {facturadirectaSandboxAction}=await import('../lib/facturadirecta-sandbox.js');
  const result=await facturadirectaSandboxAction({
   action:'pdf',invoice_id:'inv_existing123',test_id:'mysecuretestkey1234567890123456'
  });
  assert.equal(result.sandbox,true);
  assert.equal(result.id,'inv_existing123');
  assert.match(result.pdf_url,/test\.pdf$/);
  assert.ok(!calls.some(x=>x.method==='POST'));
  assert.equal(calls.filter(x=>x.path.endsWith('/invoices/inv_existing123/pdf')).length,1);
 }finally{globalThis.fetch=prior;restore()}
});

test('consulta de PDF bloquea documentos ajenos al escenario de prueba',async()=>{
 activate();
 const prior=globalThis.fetch;
 let pdfCalls=0;
 globalThis.fetch=async(url,options={})=>{
  const path=String(url);
  if(path.endsWith('/invoices/inv_foreign123')&&options.method==='GET')
   return Response.json({content:{uuid:'inv_foreign123',main:{
    lines:[{text:'Factura sin etiqueta de pruebas'}]}}});
  if(path.endsWith('/invoices/inv_foreign123/pdf'))pdfCalls++;
  return fakeResponse(url,options);
 };
 try{
  const {facturadirectaSandboxAction}=await import('../lib/facturadirecta-sandbox.js');
  await assert.rejects(()=>facturadirectaSandboxAction({
   action:'pdf',invoice_id:'inv_foreign123',test_id:'mysecuretestkey1234567890123456'
  }),/Solo pueden/);
  assert.equal(pdfCalls,0);
 }finally{globalThis.fetch=prior;restore()}
});

test('fallo del PDF devuelve motivo y conserva ID de factura sin duplicarla',async()=>{
 activate();
 const prior=globalThis.fetch;
 globalThis.fetch=async(url,options={})=>{
  const path=String(url);
  if(path.endsWith('/invoices/inv_existing123')&&options.method==='GET')
   return Response.json({content:{uuid:'inv_existing123',main:{
    lines:[{text:'DParranda SANDBOX TEST'}]}}});
  if(path.endsWith('/invoices/inv_existing123/pdf')&&options.method==='PUT')
   return Response.json({errors:[{path:'/body',message:'Plantilla de impresión sin configurar'}]},{status:400});
  return fakeResponse(url,options);
 };
 try{
  const {facturadirectaSandboxAction}=await import('../lib/facturadirecta-sandbox.js');
  const result=await facturadirectaSandboxAction({
   action:'pdf',invoice_id:'inv_existing123',test_id:'mysecuretestkey1234567890123456'
  });
  assert.equal(result.id,'inv_existing123');
  assert.equal(result.pdf_url,'');
  assert.match(result.pdf_message,/Plantilla de impresión sin configurar/);
 }finally{globalThis.fetch=prior;restore()}
});
