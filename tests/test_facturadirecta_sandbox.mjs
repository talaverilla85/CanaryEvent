// Offline test of the actual Stripe-test -> FacturaDirecta-sandbox issuance path.
import test from 'node:test';
import assert from 'node:assert/strict';
import {facturadirectaSandboxStatus} from '../lib/facturadirecta-sandbox.js';
import {invoiceIssuanceReadiness,issueCheckedInvoice} from '../lib/advertising-invoice-issuance.js';
import {processInvoiceAdjustment} from '../lib/advertising-invoice-adjustments.js';
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
