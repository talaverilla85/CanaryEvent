// No external calls leave this test: provider and SQL are faked.
import test from 'node:test';
import assert from 'node:assert/strict';
import {providerConfiguration,billingProviderStatus,isCanaryBuyer,buildInvoicePayload} from '../lib/facturadirecta-invoices.js';
import {invoiceIssuanceReadiness,issueCheckedInvoice} from '../lib/advertising-invoice-issuance.js';

const keys=['FACTURADIRECTA_API_KEY','FACTURADIRECTA_COMPANY_ID','FACTURADIRECTA_IGIC_SALES_TAX_ID',
 'FACTURADIRECTA_INVOICE_SERIES','FACTURADIRECTA_ACCOUNT_CODE','FACTURADIRECTA_FISCAL_SETUP_CONFIRMED',
 'DPARRANDA_STRIPE_MODE'];
const original=Object.fromEntries(keys.map(k=>[k,process.env[k]]));
const activate=()=>{
 process.env.FACTURADIRECTA_API_KEY='AbC123.'+'x'.repeat(32);
 process.env.FACTURADIRECTA_COMPANY_ID='empresa_prueba';
 process.env.FACTURADIRECTA_IGIC_SALES_TAX_ID='tax_IGIC_7';
 process.env.FACTURADIRECTA_INVOICE_SERIES='DP-##-';
 process.env.FACTURADIRECTA_ACCOUNT_CODE='705000';
 process.env.FACTURADIRECTA_FISCAL_SETUP_CONFIRMED='true';
 process.env.DPARRANDA_STRIPE_MODE='live';
};
const reset=()=>{for(const k of keys){
 if(original[k]===undefined)delete process.env[k];else process.env[k]=original[k]
}};
const issuer={
 legal_name:'Persona de pruebas',tax_id:'12345678Z',billing_address:'Calle Test 1',
 billing_postal:'35118',billing_city:'Agüimes',billing_region:'Las Palmas',billing_country:'España',
 copy_email:'hola@dparranda.es',general_igic_confirmed:true,igic_general_rate_percent:7
};
const review={
 draft_id:17,company_name:'Empresa Cliente SL',customer_tax_id:'B12345674',
 billing_email:'facturas@example.invalid',billing_address:'Calle Prueba 5',
 billing_postal:'35001',billing_city:'Las Palmas de Gran Canaria',
 billing_region:'Las Palmas',billing_country:'España',
 title:'Anuncio de prueba',plan:'local',days:30,placement:'banner',total_cents:1900,
 review_status:'checked',payment_status:'paid',paid_at:'2026-11-17T13:00:00Z',
 stripe_checkout_session_id:'cs_live_ABC123'
};

test('El proveedor solo se considera conectado con todos sus parámetros fiscales',()=>{
 for(const k of keys)delete process.env[k];
 assert.equal(billingProviderStatus().connected,false);
 activate();
 assert.equal(providerConfiguration().configured,true);
 delete process.env.FACTURADIRECTA_FISCAL_SETUP_CONFIRMED;
 assert.equal(providerConfiguration().configured,false);
 reset();
});
test('El tipo general IGIC 7% no se aplica automáticamente a clientes peninsulares',()=>{
 assert.equal(isCanaryBuyer(review),true);
 assert.equal(isCanaryBuyer({...review,billing_postal:'28001'}),false);
 assert.equal(isCanaryBuyer({...review,billing_country:'FR'}),false);
 assert.equal(isCanaryBuyer({...review,billing_postal:'28001',billing_country:'España'}),false);
});
test('Una factura emitible mantiene serie, fecha e importe ya pagado',()=>{
 activate();
 const cfg=providerConfiguration();
 const payload=buildInvoicePayload(cfg,{...review,issue_date:'2026-11-17'},'con_cliente_ficticio');
 assert.equal(payload.content.main.draft,false);
 assert.equal(payload.content.main.external,false);
 assert.equal(payload.content.main.simplified,false);
 assert.equal(payload.content.main.taxIncludedPrices,true);
 assert.equal(payload.content.main.date,'2026-11-17');
 assert.equal(payload.content.main.docNumber.series,'DP-##-');
 assert.equal(payload.content.main.lines[0].unitPrice,19);
 assert.deepEqual(payload.content.main.lines[0].tax,['tax_IGIC_7']);
 assert.throws(()=>buildInvoicePayload(cfg,review,'con_cliente_ficticio'),/fecha fiscal/);
 reset();
});
test('Guardar el emisor no basta: sin proveedor o Stripe real nunca se puede emitir',async()=>{
 for(const k of keys)delete process.env[k];
 const sql=async()=>[issuer];
 const status=await invoiceIssuanceReadiness(sql);
 assert.equal(status.can_issue,false);
 assert.ok(status.missing.length>=2);
 let requests=0;
 const fetch0=globalThis.fetch;
 globalThis.fetch=async()=>{requests++;throw Error('No debe salir una petición')};
 try{await assert.rejects(()=>issueCheckedInvoice(sql,17),/No se puede emitir/)}
 finally{globalThis.fetch=fetch0;reset()}
 assert.equal(requests,0);
});
test('El pago real validado y revisado emite una sola factura y envía PDF a cliente con copia',async()=>{
 activate();
 const requests=[];
 const fetch0=globalThis.fetch;
 globalThis.fetch=async (url,opts)=>{
  const body=opts.body?JSON.parse(opts.body):null;
  requests.push({url,method:opts.method,body,headers:opts.headers});
  if(url.includes('/contacts?'))return Response.json({items:[]});
  if(url.endsWith('/contacts'))return Response.json({content:{uuid:'con_cliente_ficticio'}});
  if(url.endsWith('/invoices'))return Response.json({content:{uuid:'inv_factura_unica'},webUrl:'https://app.facturadirecta.com/factura'});
  if(url.includes('/invoices/inv_factura_unica/send'))return Response.json({ok:true});
  throw Error('unexpected URL: '+url);
 };
 let existing=null;
 const sql=async(parts,...values)=>{
  const q=parts.join('?');
  if(q.includes('FROM advertising_invoice_issuer'))return [issuer];
  if(q.includes('FROM advertising_invoice_reviews r JOIN advertiser_campaign_drafts d'))return [review];
  if(q.includes('FROM advertising_invoice_issuance WHERE draft_id'))return existing?[existing]:[];
  if(q.includes('INSERT INTO advertising_invoice_issuance')){
   existing={status:'issuing',provider_invoice_id:null,issue_date:'2026-11-17'};
   return [{draft_id:17,provider_contact_id:null,provider_invoice_id:null,issue_date:'2026-11-17'}];
  }
  if(q.includes('UPDATE advertising_invoice_issuance SET provider_contact_id'))return [];
  if(q.includes("status='issued',provider_invoice_id=")){
   existing={status:'issued',provider_invoice_id:'inv_factura_unica',
    provider_invoice_url:'https://app.facturadirecta.com/factura'};
   return [{provider_invoice_id:'inv_factura_unica'}];
  }
  if(q.includes("UPDATE advertising_invoice_issuance SET status='sending'"))return [{provider_invoice_id:'inv_factura_unica'}];
  if(q.includes("status='sent',sent_at=")){
   existing={...existing,status:'sent'};return [{draft_id:17}];
  }
  throw Error('unknown SQL '+q.slice(0,160));
 };
 try{
  const result=await issueCheckedInvoice(sql,17);
  assert.equal(result.status,'sent');
  assert.equal(requests.length,4);
  assert.equal(requests.filter(x=>x.url.endsWith('/invoices')).length,1);
  const generated=requests.find(x=>x.url.endsWith('/invoices'));
  assert.equal(generated.body.content.main.draft,false);
  assert.equal(generated.body.content.main.lines[0].unitPrice,19);
  const delivery=requests.find(x=>x.url.endsWith('/send'));
  assert.equal(delivery.body.to,'facturas@example.invalid');
  assert.equal(delivery.body.cc,'hola@dparranda.es');
  assert.match(delivery.headers['Idempotency-Key'],/dp-invoice-send/);
  assert.equal((await issueCheckedInvoice(sql,17)).status,'sent');
  assert.equal(requests.length,4,'retry must not create nor send a second invoice');
 }finally{globalThis.fetch=fetch0;reset()}
});
test('Incluso con el proveedor configurado, un borrador sin revisar nunca se emite',async()=>{
 activate();
 let fetchCount=0;
 const initial=globalThis.fetch;
 globalThis.fetch=async()=>{fetchCount++;throw Error('Unexpected call')};
 const sql=async(parts)=>{
  const q=parts.join('?');
  if(q.includes('FROM advertising_invoice_issuer'))return [issuer];
  if(q.includes('FROM advertising_invoice_reviews r JOIN advertiser_campaign_drafts d'))
   return [{...review,review_status:'pending'}];
  return [];
 };
 try{await assert.rejects(()=>issueCheckedInvoice(sql,17),/pago real confirmado y datos revisados/)}
 finally{globalThis.fetch=initial;reset()}
 assert.equal(fetchCount,0);
});
