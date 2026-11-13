// Runtime commercial checks: real application modules, mocked Resend/Stripe HTTP.
// No production credentials, outbound network requests or database writes.
import test from 'node:test';
import assert from 'node:assert/strict';
import {expectedAmount,ensureApprovedPayment,stripePaymentsReady} from '../lib/stripe-advertising.js';
import {createEmailAccessToken,parseEmailAccessToken,sendWelcomeEmail,
 sendChangesRequestedEmail,sendPaymentApprovedEmail,sendPaymentConfirmedEmail} from '../lib/advertiser-mail.js';
import {canaryToday} from '../lib/advertiser-publication.js';

const env={
 DPARRANDA_LEADS_ENABLED:'true',
 DPARRANDA_SESSION_SECRET:'only-a-fake-test-secret-that-is-more-than-32-characters',
 DATABASE_URL:'postgresql://test.invalid/neondb',
 RESEND_CUSTOMER_EMAILS_ENABLED:'true',
 RESEND_FROM_EMAIL:'hola@dparranda.es',
 RESEND_API_KEY:'re_example_no_real_requests',
 DPARRANDA_STRIPE_MODE:'test',
 DPARRANDA_STRIPE_PAYMENTS_ENABLED:'true',
 STRIPE_SECRET_KEY:'sk_test_example_no_real_requests',
 STRIPE_WEBHOOK_SECRET:'whsec_example'
};
for(const [key,value] of Object.entries(env))process.env[key]=value;
const account={id:9,access_version:1,active:true,company:'Anunciante de prueba',
 contact_name:'Cliente ficticio',email:'test@example.invalid'};
const info={account,draft:{id:17,title:'Campaña de prueba'},leadId:37};

test('Tarifas locales, zonas e insulares son precios del servidor',()=>{
 for(const [plan,price] of Object.entries({local:1900,zona:4900,insular:9900})){
  assert.equal(expectedAmount(plan,30),price);
  assert.equal(expectedAmount(plan,60),price*2);
 }
 assert.equal(expectedAmount('desconocido',30),null);
 assert.equal(expectedAmount('local',45),null);
 assert.match(canaryToday(),/^20\d{2}-\d{2}-\d{2}$/);
 assert.equal(stripePaymentsReady(),true);
});

test('El acceso personal se firma y rechaza modificaciones',()=>{
 const token=createEmailAccessToken(account);
 assert.match(token,/^mail\./);
 assert.deepEqual(parseEmailAccessToken(token),{id:9,version:1});
 assert.equal(parseEmailAccessToken(token.slice(0,-1)+(token.endsWith('a')?'b':'a')),null);
 assert.equal(parseEmailAccessToken('mail.9.2.9999999999.'+'0'.repeat(64)),null);
});

test('Correo de bienvenida y revisión salen con marca, contenido y enlace de acceso',async t=>{
 const original=globalThis.fetch;const sent=[];
 globalThis.fetch=async (url,opts)=>{
  assert.equal(url,'https://api.resend.com/emails');
  sent.push({body:JSON.parse(opts.body),key:opts.headers['Idempotency-Key']});
  return Response.json({id:'email_fake_sent'});
 };
 t.after(()=>{globalThis.fetch=original});
 assert.equal((await sendWelcomeEmail(info)).status,'sent');
 assert.equal((await sendChangesRequestedEmail(info,'Cambiar el cartel','revision_test_2')).status,'sent');
 assert.equal(sent.length,2);
 assert.equal(sent[0].body.from,'DParranda <hola@dparranda.es>');
 assert.equal(sent[0].body.to[0],account.email);
 assert.equal(sent[0].body.subject,'D’Parranda · Hemos recibido tu anuncio');
 assert.doesNotMatch(sent[0].body.subject,/#[0-9]+/);
 assert.match(sent[0].body.html,/https:\/\/dparranda\.es\/anunciantes\/#[^"]+/);
 assert.match(sent[1].body.html,/Cambiar el cartel/);
 assert.match(sent[1].body.html,/Revisar y corregir mi anuncio/);
 assert.notEqual(sent[0].key,sent[1].key);
});

test('Cobro y confirmación comunican el precio y el estado sin afirmar incorrectamente que no se ha pagado',async t=>{
 const original=globalThis.fetch;const sent=[];
 globalThis.fetch=async (url,opts)=>{sent.push(JSON.parse(opts.body));return Response.json({id:'email_fake_sent'})};
 t.after(()=>{globalThis.fetch=original});
 assert.equal((await sendPaymentApprovedEmail(info,'https://buy.stripe.com/test_token',4900,'zona',30,'plink_example')).status,'sent');
 assert.equal((await sendPaymentConfirmedEmail(info,'evt_fake_123')).status,'sent');
 assert.match(sent[0].subject,/49,00 €/);
 assert.match(sent[0].html,/https:\/\/buy\.stripe\.com\/test_token/);
 assert.match(sent[1].body||sent[1].html,/Hemos registrado tu contratación/);
 assert.doesNotMatch(sent[1].html,/No se ha realizado ningún cobro/);
});

test('Desactivación del correo impide envíos reales al anunciante',async t=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>{throw Error('No debe existir ninguna petición HTTP')};
 t.after(()=>{globalThis.fetch=original;process.env.RESEND_CUSTOMER_EMAILS_ENABLED='true'});
 process.env.RESEND_CUSTOMER_EMAILS_ENABLED='false';
 assert.equal((await sendWelcomeEmail(info)).status,'pending_domain');
});

test('Aprobación Stripe válida crea un único enlace para el importe exacto y envía el correo',async t=>{
 const original=globalThis.fetch;const requests=[];
 globalThis.fetch=async (url,opts)=>{
  requests.push({url,opts});
  if(url==='https://api.stripe.com/v1/payment_links')
   return Response.json({id:'plink_123456789',url:'https://buy.stripe.com/test_example',livemode:false});
  if(url==='https://api.resend.com/emails')return Response.json({id:'email_fake_sent'});
  throw Error('Unexpected URL: '+url);
 };
 t.after(()=>{globalThis.fetch=original});
 const sql=async (pieces,...params)=>{
  const query=pieces.join('?');
  if(query.includes('SELECT d.id,d.plan,d.days,d.price_cents'))
   return [{id:17,plan:'local',days:30,price_cents:1900,status:'approved_for_payment',
    payment_status:'unavailable',stripe_payment_link_id:null,stripe_payment_url:null,
    title:info.draft.title,placement:'banner',event_start:null,
    campaign_start_iso:'2026-12-20',email:account.email}];
  if(query.includes('UPDATE advertiser_campaign_drafts SET')&&query.includes('stripe_payment_link_id'))
   return [{id:17}];
  if(query.includes('SELECT a.id AS account_id'))
   return [{account_id:9,company:account.company,contact_name:account.contact_name,
    email:account.email,access_version:1,active:true,draft_id:17,
    title:info.draft.title,status:'pending_payment',source_lead_id:37}];
  throw Error('Consulta inesperada en prueba de aprobación: '+query.slice(0,120));
 };
 const result=await ensureApprovedPayment(sql,17);
 assert.equal(result.status,'ready');
 assert.equal(result.email_status,'sent');
 assert.equal(result.amount_cents,1900);
 assert.equal(requests.length,2);
 const payment=new URLSearchParams(requests[0].opts.body);
 assert.equal(payment.get('line_items[0][price_data][unit_amount]'),'1900');
 assert.equal(payment.get('line_items[0][price_data][product_data][description]'),info.draft.title);
 assert.equal(payment.get('metadata[dparranda_draft_id]'),'17');
 assert.equal(payment.get('restrictions[completed_sessions][limit]'),'1');
});

test('El pago no puede autorizarse cuando el importe o la fecha del evento son inválidos',async t=>{
 const original=globalThis.fetch;
 globalThis.fetch=async()=>{throw Error('No debe iniciarse un cobro')};
 t.after(()=>{globalThis.fetch=original});
 async function check(data){
  const sql=async()=>[data];
  return assert.rejects(()=>ensureApprovedPayment(sql,7));
 }
 const base={id:7,plan:'local',days:30,price_cents:1900,status:'approved_for_payment',
  payment_status:'pending',stripe_payment_link_id:null,stripe_payment_url:null,
  title:'Evento de prueba',placement:'evento',event_start:'2025-01-10T20:00',
  campaign_start_iso:'2025-01-01',email:account.email};
 await check(base);
 await check({...base,placement:'banner',price_cents:200});
});
