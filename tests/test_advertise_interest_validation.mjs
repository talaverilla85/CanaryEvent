import test from 'node:test';
import assert from 'node:assert/strict';
import handler from '../api/advertise-interest.js';

const vars={
 DPARRANDA_LEADS_ENABLED:'true',
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
 company:'Negocio de prueba',contact:'Nombre de prueba',email:'cliente@example.com',telephone:'',
 consent:true,proposal:true,
 campaign:{
  kind:'banner',plan:'local',days:30,municipalities:['Agüimes'],
  start:'2030-01-01',title:'Prueba de anuncio',
  destination:'https://example.com',description:'Una descripción válida y suficientemente larga',
  image_data:null,eventDate:'',eventTown:'',eventVenue:''
 }
});
test('la API distingue el problema de imagen sin culpar al contacto',async()=>{
 const r=await validation(base());
 assert.equal(r.statusCode,400);
 assert.ok(r.body.invalid_fields.some(x=>x.startsWith('imagen del anuncio')));
 assert.ok(!r.body.invalid_fields.some(x=>/persona de contacto|correo electrónico|nombre del negocio/.test(x)));
 assert.ok(!r.body.error.includes('cliente@example.com'));
});
test('descripciones de menos de 12 caracteres se identifican de manera explícita',async()=>{
 const b=base();b.campaign.description='Corto';
 const r=await validation(b);
 assert.equal(r.statusCode,400);
 assert.ok(r.body.invalid_fields.some(x=>x.includes('mínimo 12 caracteres')));
});
test('fecha de inicio pasada se diferencia del resto de los datos',async()=>{
 const b=base();b.campaign.start='2025-01-01';
 const r=await validation(b);
 assert.equal(r.statusCode,400);
 assert.ok(r.body.invalid_fields.some(x=>x.includes('fecha de inicio')));
});
