import test from 'node:test';
import assert from 'node:assert/strict';
import handler from '../api/advertise-interest.js';

const vars={
 DPARRANDA_LEADS_ENABLED:'true',
 DPARRANDA_ADVERTISING_SALES_ENABLED:'true',
 DATABASE_URL:'postgres://not-used.example.invalid/dparranda',
 DPARRANDA_LEGAL_NAME:'Titular de pruebas autorizado',
 DPARRANDA_LEGAL_ADDRESS:'Calle de pruebas 12, Gran Canaria',
 DPARRANDA_LEGAL_NIF:'12345678Z',
 DPARRANDA_PRIVACY_EMAIL:'pruebas@example.com'
};
const saved=Object.fromEntries(Object.keys(vars).map(k=>[k,process.env[k]]));
test.before(()=>Object.assign(process.env,vars));
test.after(()=>{for(const k of Object.keys(vars)){
 if(saved[k]===undefined)delete process.env[k];else process.env[k]=saved[k];
}});
async function validation(body){
 const res={
  headers:{},statusCode:null,body:null,
  setHeader(k,v){this.headers[k]=v;return this},
  status(code){this.statusCode=code;return this},
  end(data){this.body=JSON.parse(data);return this}
 };
 await handler({method:'POST',headers:{origin:'https://dparranda.es',host:'dparranda.es'},body},res);
 return res;
}
const base=()=>({
 company:'Negocio de prueba',contact:'Nombre de prueba',email:'cliente@example.com',telephone:'600123456',legal_name:'Razón social de pruebas SL',
 consent:true,proposal:true,
 campaign:{
  kind:'banner',plan:'local',days:30,municipalities:['Agüimes'],
  start:'2030-01-01',title:'Prueba de anuncio',
  destination:'https://example.com',description:'Una descripción válida y suficientemente larga',
  image_data:null,eventDate:'',eventTown:'',eventVenue:''
 }
});
test('solo se rechaza cuando falta identidad fiscal o teléfono',async()=>{
 const b=base();b.telephone='';b.legal_name='';
 b.campaign.destination='';
 b.campaign.description='';
 b.campaign.start='2025-01-01';
 b.campaign.image_data=null;
 const r=await validation(b);
 assert.equal(r.statusCode,400);
 assert.ok(r.body.invalid_fields.some(x=>x.includes('teléfono')));
 assert.ok(r.body.invalid_fields.some(x=>x.includes('razón social')));
 assert.ok(!r.body.invalid_fields.some(x=>/enlace|descripción|imagen|fecha/.test(x)));
 assert.ok(!r.body.error.includes('cliente@example.com'));
});
test('el correo válido y el consentimiento siguen siendo obligatorios',async()=>{
 const b=base();b.email='invalido';b.consent=false;
 const r=await validation(b);
 assert.equal(r.statusCode,400);
 assert.ok(r.body.invalid_fields.some(x=>x.includes('correo electrónico')));
 assert.ok(r.body.invalid_fields.some(x=>x.includes('privacidad')));
});
test('los campos estructurales de tarifa se siguen validando para evitar precios corruptos',async()=>{
 const b=base();b.campaign.days=365;
 const r=await validation(b);
 assert.equal(r.statusCode,400);
 assert.ok(r.body.invalid_fields.some(x=>x.includes('tarifa')));
});
test('el contrato separa revisión inicial de aprobación y pago',async()=>{
 const {readFileSync}=await import('node:fs');
 const src=readFileSync(new URL('../api/advertise-interest.js',import.meta.url),'utf8');
 const admin=readFileSync(new URL('../api/admin.js',import.meta.url),'utf8');
 assert.ok(src.includes('saved_image AS'));
 assert.ok(src.includes("const link=safeText(draft.destination,850)"));
 assert.ok(src.includes("WHERE ${image}::text IS NOT NULL"));
 assert.ok(admin.includes('validAdApprovalUrl(draft.destination)'));
 assert.ok(admin.includes("if(decision==='approved_for_payment'"));
});
