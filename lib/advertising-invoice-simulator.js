// Pure, read-only demonstration for administrators.
// It NEVER calls Stripe/FacturaDirecta, writes a DB row, sends emails or issues a legal invoice.
import {expectedAmount,STRIPE_LABELS} from './stripe-advertising.js';
import {inclusiveIgicBreakdown} from './advertising-invoice-reviews.js';
import {buildInvoicePayload,buildCorrectionPayload} from './facturadirecta-invoices.js';

const cases=['sale','billing_details','refund_full','refund_partial'];
const mockCfg=Object.freeze({
  series:'SIM-F-2026-',rectification_series:'SIM-R-2026-',
  account:'705000',tax_id:'SIM_IGIC_7'
});
const todayCanary=()=>{
 const values=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{
  timeZone:'Atlantic/Canary',day:'2-digit',month:'2-digit',year:'numeric'
 }).formatToParts(new Date()).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
 return values.year+'-'+values.month+'-'+values.day;
};
function document({reference,kind,amountCents,description,date,reasonCode=null,linkedTo=null}){
 const tax=inclusiveIgicBreakdown(Math.abs(amountCents),7);
 const sign=Math.sign(amountCents);
 return {
  reference,kind,description,date,amount_cents:amountCents,
  base_cents:sign*tax.base_cents,igic_cents:sign*tax.igic_cents,
  rate_percent:7,linked_to:linkedTo,rectification_code:reasonCode,
  customer:'CLIENTE FICTICIO · PRUEBA SIN NIF REAL',
  issuer:'D’PARRANDA · EMISOR FICTICIO · NO REGISTRADO',
  fiscal_validity:false,provider_document:false
 };
}
export function simulateInvoiceWorkflow({plan='zona',days=30,scenario='sale'}={}){
 if(!cases.includes(scenario))throw new Error('Escenario de prueba no admitido');
 const cents=expectedAmount(plan,Number(days));
 if(!cents)throw new Error('Plan o duración de prueba no admitidos');
 const issueDate=todayCanary();
 const fakeRow={draft_id:'DEMO_1',total_cents:cents,plan,days:Number(days),
  placement:'banner',title:'Publicidad ficticia D’Parranda',issue_date:issueDate};
 const normal=buildInvoicePayload(mockCfg,fakeRow,'con_DEMO');
 const initial=document({
  reference:'SIM-F-0001',kind:'original',amountCents:cents,
  description:normal.content.main.lines[0].text,date:issueDate
 });
 const steps=[
  {status:'simulado',label:'Pago Stripe de prueba',details:'Importe ficticio. No se ha cobrado dinero.'},
  {status:'simulado',label:'Revisión de datos',details:'Emisor y cliente inventados.'},
  {status:'simulado',label:'Factura simulada',details:'Documento de demostración sin valor legal.'}
 ];
 const docs=[initial];
 let refundCents=0;
 if(scenario==='billing_details'){
  const negative=buildCorrectionPayload(mockCfg,{
   originalInvoiceId:'inv_DEMO',originalContact:'con_DEMO',
   amountCents:cents,issueDate,reason:'Datos fiscales incorrectos, ejemplo ficticio',
   kind:'billing_details',title:fakeRow.title
  });
  docs.push(document({reference:'SIM-R-0001',kind:'rectificativa',
   amountCents:-cents,description:negative.content.main.lines[0].text,
   date:issueDate,reasonCode:negative.content.main.verifactu.TipoFactura,
   linkedTo:initial.reference
  }));
  docs.push(document({reference:'SIM-F-0002',kind:'sustitución',
   amountCents:cents,description:'Nueva factura con destinatario ficticio corregido',
   date:issueDate
  }));
  steps.push(
   {status:'simulado',label:'Rectificativa R4',details:'Anula el importe fiscal de la original; no se reembolsa dinero.'},
   {status:'simulado',label:'Factura sustituida',details:'Datos fiscales de prueba corregidos. Dos documentos de prueba.'}
  );
 }else if(scenario==='refund_full'||scenario==='refund_partial'){
  refundCents=scenario==='refund_full'?cents:Math.min(cents-100,1200);
  const negative=buildCorrectionPayload(mockCfg,{
   originalInvoiceId:'inv_DEMO',originalContact:'con_DEMO',
   amountCents:refundCents,issueDate,
   reason:'Devolución de ejemplo, sin devolución bancaria',
   kind:scenario,title:fakeRow.title
  });
  docs.push(document({reference:'SIM-R-0001',kind:'rectificativa',
   amountCents:-refundCents,date:issueDate,
   description:negative.content.main.lines[0].text,
   reasonCode:negative.content.main.verifactu.TipoFactura,linkedTo:initial.reference
  }));
  steps.push(
   {status:'simulado',label:'Solicitud de reembolso Stripe',details:'Solo simulación: no se ha creado ninguna devolución.'},
   {status:'simulado',label:'Confirmación ficticia y rectificativa R1',
    details:'La rectificativa se crea en el ejemplo después de una devolución ficticia confirmada.'}
  );
 }
 return {
  simulation:true,real_payment:false,legal_invoice:false,customer_emails_sent:0,
  external_requests:0,database_changes:0,verified_provider_sandbox:false,
  plan,label:STRIPE_LABELS[plan],days:Number(days),scenario,date:issueDate,
  amount_cents:cents,refund_cents:refundCents,
  buyer:'Cliente DEMO · datos totalmente inventados',
  payment_reference:'cs_test_EJEMPLO_NO_REAL',
  steps,documents:docs,
  notice:'SIMULACIÓN LOCAL · SIN VALIDEZ FISCAL · No conectado a Stripe ni FacturaDirecta. El 7 % de IGIC es solo un ejemplo pendiente de confirmación censal.'
 };
}
