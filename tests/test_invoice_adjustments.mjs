// Offline contract tests for corrections and refunds. Real Stripe/FacturaDirecta APIs NEVER called.
import test from 'node:test';
import assert from 'node:assert/strict';
import {buildCorrectionPayload,createCorrectionInvoice,providerConfiguration} from '../lib/facturadirecta-invoices.js';
import {createInvoiceAdjustment,rejectInvoiceAdjustment,processInvoiceAdjustment}
 from '../lib/advertising-invoice-adjustments.js';

const fiscalEnv={
 FACTURADIRECTA_API_KEY:'AbC123.'+'x'.repeat(32),
 FACTURADIRECTA_COMPANY_ID:'empresa_prueba',
 FACTURADIRECTA_IGIC_SALES_TAX_ID:'S_IGIC_7',
 FACTURADIRECTA_INVOICE_SERIES:'DP-##-',
 FACTURADIRECTA_RECTIFICATION_SERIES:'RDP-##-',
 FACTURADIRECTA_ACCOUNT_CODE:'705000',
 FACTURADIRECTA_FISCAL_SETUP_CONFIRMED:'true',
 DPARRANDA_STRIPE_MODE:'live',
 DPARRANDA_STRIPE_PAYMENTS_ENABLED:'true',
 STRIPE_SECRET_KEY:'sk_live_fake_offline',
 STRIPE_WEBHOOK_SECRET:'whsec_fake_offline'
};
const before=Object.fromEntries(Object.keys(fiscalEnv).map(k=>[k,process.env[k]]));
const activate=()=>Object.assign(process.env,fiscalEnv);
const restore=()=>{for(const k of Object.keys(fiscalEnv)){
 if(before[k]===undefined)delete process.env[k];else process.env[k]=before[k];
}};
const issuer={legal_name:'Autónomo prueba',tax_id:'12345678Z',
 billing_address:'Calle Test 4',billing_postal:'35118',billing_city:'Agüimes',
 billing_region:'Las Palmas',billing_country:'España',copy_email:'hola@dparranda.es',
 general_igic_confirmed:true};
const review={draft_id:7,total_cents:4900,company_name:'Cliente Original',
 customer_tax_id:'B12345674',billing_email:'cliente@example.invalid',
 billing_address:'Calle uno',billing_postal:'35001',billing_city:'Las Palmas',
 billing_region:'Las Palmas',billing_country:'ES',review_status:'checked',
 payment_status:'paid',invoice_status:'sent',provider_invoice_id:'inv_original'};
const invoiceRow={...review,id:11,kind:'refund_partial',amount_cents:1200,
 reason:'Se devuelve un importe por incidencia de servicio',
 status:'pending_review',request_key:'unique-request-token-12345',
 stripe_payment_intent_id:'pi_fake',
 stripe_checkout_session_id:'cs_live_abc123',
 original_invoice_id:'inv_original',original_invoice_status:'sent',
 title:'Publicidad',plan:'zona',days:30,placement:'banner',source_lead_id:null,
 published_ad_id:null,published_event_id:null,issue_date:'2026-11-17',
 correction_invoice_id:null,correction_sent_at:null};

test('Rectificativas FacturaDirecta enlazadas y con valor negativo, R1 o R4 según motivo',()=>{
 activate();
 try{
  const cfg=providerConfiguration();
  const correction=buildCorrectionPayload(cfg,{
   originalInvoiceId:'inv_original',originalContact:'con_1234',amountCents:1200,
   issueDate:'2026-11-17',kind:'refund_partial',reason:'Devolución 12 euros',title:'Publicidad'});
  const main=correction.content.main;
  assert.equal(main.correctedInvoice,'inv_original');
  assert.equal(main.verifactu.TipoFactura,'R1');
  assert.equal(main.docNumber.series,'RDP-##-');
  assert.equal(main.lines[0].unitPrice,-12);
  assert.equal(main.draft,false);
  assert.equal(main.taxIncludedPrices,true);
  assert.equal(main.lines[0].tax[0],'S_IGIC_7');
  const corrected=buildCorrectionPayload(cfg,{
   originalInvoiceId:'inv_original',originalContact:'con_1234',amountCents:4900,
   issueDate:'2026-11-17',kind:'billing_details',reason:'Error en razón social',title:'Publicidad'});
  assert.equal(corrected.content.main.verifactu.TipoFactura,'R4');
  assert.equal(corrected.content.main.lines[0].lineTotal,-49);
  assert.throws(()=>buildCorrectionPayload({...cfg,rectification_series:''},{
   originalInvoiceId:'inv_original',originalContact:'con_1234',amountCents:1200,
   issueDate:'2026-11-17',kind:'refund_full',reason:'Devolución'}),/serie fiscal/);
 }finally{restore()}
});

test('Crear una solicitud pendiente nunca cobra, reembolsa ni emite facturas',async()=>{
 const oldFetch=globalThis.fetch;let called=0;
 globalThis.fetch=async()=>{called++;throw Error('Unexpected network')};
 const sql=async(parts,...values)=>{
  const q=parts.join('?');
  if(q.includes('SELECT r.draft_id,r.total_cents'))return [review];
  if(q.includes('SELECT COALESCE(SUM(amount_cents)'))return [{cents:0}];
  if(q.includes('INSERT INTO advertising_invoice_adjustments'))return [{
   id:11,draft_id:7,kind:'refund_partial',status:'pending_review'
  }];
  throw Error('unexpected SQL: '+q.slice(0,180));
 };
 try{
  const pending=await createInvoiceAdjustment(sql,{draft_id:7,kind:'refund_partial',
   amount_cents:1200,reason:'Se ha acordado devolver una parte del servicio',
   request_key:'unique-request-token-12345'});
  assert.equal(pending.created,true);
  assert.equal(pending.status,'pending_review');
  assert.equal(called,0);
  await assert.rejects(()=>createInvoiceAdjustment(sql,{draft_id:7,kind:'refund_partial',
   amount_cents:5500,reason:'Se ha acordado devolver una parte del servicio',
   request_key:'unique-request-token-12346'}),/supera el importe/);
 }finally{globalThis.fetch=oldFetch}
});

test('Rechazar una solicitud pendiente no afecta a Stripe',async()=>{
 const sql=async()=>[{id:11}];
 const res=await rejectInvoiceAdjustment(sql,11);
 assert.equal(res.rejected,true);
});

test('Antes de conectar FacturaDirecta, ejecutar una devolución real está bloqueado',async()=>{
 const oldFetch=globalThis.fetch;let calls=0;
 globalThis.fetch=async()=>{calls++;throw Error('Unexpected network')};
 const sql=async()=>[issuer];
 try{await assert.rejects(()=>processInvoiceAdjustment(sql,11),/requiere FacturaDirecta/)}
 finally{globalThis.fetch=oldFetch}
 assert.equal(calls,0);
});

test('Devolución parcial real se confirma en Stripe antes de emitir una única rectificativa',async()=>{
 activate();
 const oldFetch=globalThis.fetch;
 let refundPosts=0,fdInvoices=0;
 const http=[];
 let state={...invoiceRow},refundState='pending';
 globalThis.fetch=async(url,options={})=>{
  http.push({url,method:options.method});
  const send=v=>Response.json(v);
  if(url.includes('stripe.com/v1/checkout/sessions/'))
   return send({id:'cs_live_abc123',livemode:true,currency:'eur',
    amount_total:4900,payment_status:'paid',payment_intent:'pi_fake'});
  if(url.endsWith('stripe.com/v1/refunds')&&options.method==='POST'){
   refundPosts++;return send({id:'re_fake',amount:1200,status:'pending'});
  }
  if(url.endsWith('stripe.com/v1/refunds/re_fake'))
   return send({id:'re_fake',amount:1200,status:refundState});
  if(url.endsWith('/invoices/inv_original')&&options.method==='GET')
   return send({content:{uuid:'inv_original',main:{contact:'con_orig'}}});
  if(url.endsWith('/invoices')&&options.method==='POST'){
   fdInvoices++;return send({content:{uuid:'inv_rectificativa'},webUrl:'https://app.facturadirecta.com/inv/test'});
  }
  if(url.includes('/invoices/inv_rectificativa/send'))
   return send({ok:true});
  throw Error('unexpected HTTP '+url);
 };
 const sql=async(parts,...v)=>{
  const q=parts.join('?');
  if(q.includes('FROM advertising_invoice_issuer'))return [issuer];
  if(q.includes('FROM advertising_invoice_adjustments a'))return [state];
  if(q.includes("UPDATE advertising_invoice_adjustments SET\n  status='processing'")){
   if(state.status==='completed')return [];
   state.status='processing';return [{id:11,issue_date:'2026-11-17'}];
  }
  if(q.includes('UPDATE advertising_invoice_adjustments SET stripe_refund_id=')){
   state.stripe_refund_id=v[0];state.status=v[1];return [];
  }
  if(q.includes('UPDATE advertising_invoice_adjustments SET\n   correction_invoice_id=')){
   state.correction_invoice_id=v[0];state.correction_invoice_url=v[1];return [];
  }
  if(q.includes('UPDATE advertising_invoice_adjustments SET correction_sent_at=')){
   state.correction_sent_at=new Date();return [];
  }
  if(q.includes('UPDATE advertising_invoice_adjustments SET\n   status=\'completed\'')){
   state.status='completed';return [{id:11}];
  }
  if(q.includes("UPDATE advertising_invoice_adjustments SET status=")){
   state.status=v[0];return [];
  }
  throw Error('unexpected SQL '+q.slice(0,150));
 };
 try{
  const pending=await processInvoiceAdjustment(sql,11);
  assert.equal(pending.status,'refund_pending');
  assert.equal(refundPosts,1);
  assert.equal(fdInvoices,0);
  refundState='succeeded';
  const result=await processInvoiceAdjustment(sql,11);
  assert.equal(result.status,'completed');
  assert.equal(fdInvoices,1);
  assert.equal(refundPosts,1);
  const replay=await processInvoiceAdjustment(sql,11);
  assert.equal(replay.already,true);
  assert.equal(refundPosts,1);
  assert.equal(fdInvoices,1);
 }finally{globalThis.fetch=oldFetch;restore()}
});
