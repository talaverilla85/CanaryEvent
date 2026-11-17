// Pure functional test: no server, database, Stripe, FacturaDirecta or email.
import test from 'node:test';
import assert from 'node:assert/strict';
import {simulateInvoiceWorkflow} from '../lib/advertising-invoice-simulator.js';

test('Demo 30/60 días usa las tarifas y desglosa exactamente 7% incluido',()=>{
 const prices={local:1900,zona:4900,insular:9900};
 for(const [plan,price] of Object.entries(prices))
  for(const days of [30,60]){
   const result=simulateInvoiceWorkflow({plan,days,scenario:'sale'});
   assert.equal(result.amount_cents,price*(days/30));
   assert.equal(result.documents[0].amount_cents,result.amount_cents);
   assert.equal(result.documents[0].base_cents+result.documents[0].igic_cents,result.amount_cents);
   assert.equal(result.documents[0].rate_percent,7);
   assert.equal(result.documents.length,1);
   assert.equal(result.legal_invoice,false);
   assert.equal(result.real_payment,false);
   assert.equal(result.external_requests,0);
   assert.equal(result.database_changes,0);
   assert.equal(result.customer_emails_sent,0);
   assert.equal(result.verified_provider_sandbox,false);
   assert.match(result.notice,/SIN VALIDEZ FISCAL/);
  }
});
test('Corrección fiscal anula importe simulado y crea sustitución sin refund',()=>{
 const s=simulateInvoiceWorkflow({plan:'zona',days:30,scenario:'billing_details'});
 assert.equal(s.documents.length,3);
 assert.equal(s.documents[0].amount_cents,4900);
 assert.equal(s.documents[1].amount_cents,-4900);
 assert.equal(s.documents[1].rectification_code,'R4');
 assert.equal(s.documents[1].linked_to,s.documents[0].reference);
 assert.equal(s.documents[2].amount_cents,4900);
 assert.equal(s.refund_cents,0);
 assert.equal(s.documents.reduce((n,d)=>n+d.amount_cents,0),4900);
});
test('Devoluciones parcial y total no afectan saldo ni dinero real',()=>{
 const partial=simulateInvoiceWorkflow({plan:'zona',scenario:'refund_partial'});
 assert.equal(partial.refund_cents,1200);
 assert.equal(partial.documents[1].amount_cents,-1200);
 assert.equal(partial.documents[1].base_cents+partial.documents[1].igic_cents,-1200);
 assert.equal(partial.documents[1].rectification_code,'R1');
 assert.equal(partial.steps.at(-1).status,'simulado');
 const full=simulateInvoiceWorkflow({plan:'local',scenario:'refund_full'});
 assert.equal(full.refund_cents,1900);
 assert.equal(full.documents[1].amount_cents,-1900);
 assert.equal(full.documents.reduce((n,d)=>n+d.amount_cents,0),0);
 assert.equal(full.real_payment,false);
});
test('No llama a red, no accede a BD ni usa datos del emisor del usuario',()=>{
 const oldFetch=globalThis.fetch;
 globalThis.fetch=async()=>{throw new Error('NETWORK ACCESS FORBIDDEN')};
 try{
  for(const scenario of ['sale','billing_details','refund_full','refund_partial']){
   const result=simulateInvoiceWorkflow({plan:'insular',scenario});
   assert.equal(result.documents.every(d=>d.fiscal_validity===false&&d.provider_document===false),true);
   assert.equal(result.documents.every(d=>d.customer.includes('FICTICIO')),true);
   assert.equal(result.documents.every(d=>d.issuer.includes('FICTICIO')),true);
  }
 }finally{globalThis.fetch=oldFetch}
 assert.throws(()=>simulateInvoiceWorkflow({scenario:'real_invoice'}),/no admitido/);
 assert.throws(()=>simulateInvoiceWorkflow({plan:'other'}),/no admitidos/);
 assert.throws(()=>simulateInvoiceWorkflow({days:21}),/no admitidos/);
});
