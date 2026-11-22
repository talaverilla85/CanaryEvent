import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SEO_PAGES, pageForKey, canaryToday, intentPeriod, familyFriendly,
  upcomingEvents, landingIndexable, renderLanding, renderIntentSitemap
} from '../lib/seo-pages.js';

const official=(id,title,start,extra={})=>({
 id,title,start,end:null,municipality:'Las Palmas de Gran Canaria',
 venue:'Teatro Pérez Galdós',accuracy:'venue',category:'cultura',
 details:'El organizador confirma esta función con un programa detallado, una hora de comienzo y un lugar definido para asistentes en Gran Canaria.',
 source_url:'https://teatroperezgaldos.es/cartelera',
 ...extra
});

test('four evergreen intent pages have unique readable URL, title and metadata',()=>{
 const types=['weekend','today','kids','free'];
 assert.equal(SEO_PAGES.filter(p=>p.kind).length,4);
 assert.deepEqual(SEO_PAGES.filter(p=>p.kind).map(p=>p.kind),types);
 assert.equal(new Set(SEO_PAGES.map(p=>p.path)).size,9);
 for(const page of SEO_PAGES.filter(p=>p.kind)){
   assert.equal(pageForKey(page.key),page);
   assert.match(page.path,/^\/[a-z-]+$/);
   assert.match(page.title,/D’Parranda/);
   assert.ok(page.description.length>=80);
 }
});
test('weekend changes in Canary local dates (including Sunday and year boundaries)',()=>{
 const weekend=pageForKey('fin-de-semana');
 assert.deepEqual(intentPeriod(weekend,'2026-11-23'),
   {start:'2026-11-27',end:'2026-11-29',
    label:'Del viernes, 27 de noviembre de 2026 al domingo, 29 de noviembre de 2026'});
 assert.equal(intentPeriod(weekend,'2026-11-27').start,'2026-11-27');
 assert.equal(intentPeriod(weekend,'2026-11-28').start,'2026-11-27');
 assert.equal(intentPeriod(weekend,'2026-11-29').start,'2026-11-27');
 assert.equal(intentPeriod(weekend,'2026-11-30').start,'2026-12-04');
 assert.equal(intentPeriod(weekend,'2026-12-31').end,'2027-01-03');
 assert.equal(intentPeriod(pageForKey('hoy'),'2026-11-22').end,'2026-11-22');
 assert.equal(canaryToday(new Date('2026-07-01T23:30:00Z')),'2026-07-02');
 assert.equal(canaryToday(new Date('2026-11-22T23:30:00Z')),'2026-11-22');
});
test('weekend selection contains only real starts in that weekend, not ongoing programmes',()=>{
 const data=[
   official(1,'Concierto del viernes','2026-11-27T20:00:00'),
   official(2,'Taller sábado','2026-11-28T10:00:00'),
   official(3,'Teatro domingo','2026-11-29T19:00:00'),
   official(4,'Seminario que dura semanas','2026-10-01T09:00:00',{end:'2026-12-10'}),
   official(5,'Lunes posterior','2026-11-30T20:00:00'),
   official(6,'Viernes anterior','2026-11-20T20:00:00'),
   official(7,'Actividad terminada','2026-11-29T11:00:00',{end:'2026-11-21'}),
   official(-899,'Sesión auxiliar','2026-11-28T12:00:00')
 ];
 const weekend=pageForKey('fin-de-semana');
 assert.deepEqual(upcomingEvents(data,weekend,'2026-11-23').map(e=>e.id),[1,2,3]);
 assert.deepEqual(upcomingEvents(data,weekend,'2026-11-29').map(e=>e.id),[3]);
});
test('today includes start dates exactly today, not every day of a long event',()=>{
 const e=[
   official(1,'Evento de hoy','2026-11-22T19:00:00'),
   official(2,'Actividad de varios meses','2026-10-10',{end:'2026-12-20'}),
   official(3,'Evento de mañana','2026-11-23T19:00:00')
 ];
 assert.deepEqual(upcomingEvents(e,pageForKey('hoy'),'2026-11-22').map(x=>x.id),[1]);
 assert.deepEqual(upcomingEvents(e,pageForKey('hoy'),'2026-11-23').map(x=>x.id),[3]);
});
test('kids selection accepts explicit family audience, rejects adult plays mentioning family',()=>{
 const e=[
   official(1,'Memoria de pez','2026-12-12T18:00:00',{details:'Teatro familiar inspirado en historias populares para disfrutar en familia. La compañía ofrece una experiencia cercana y emocionante en el teatro municipal.'}),
   official(2,'Gran comedia de pareja','2026-12-12T19:00:00',{category:'familia',
     details:'Una comedia sobre la familia, la pareja y la crisis de la mediana edad. Los personajes afrontan cambios en una puesta en escena especialmente intensa.'}),
   official(3,'Escuela de cine Scarface','2026-12-13T18:00:00',{category:'familia'}),
   official(4,'Cuentacuentos infantil','2026-12-13T11:00:00'),
   official(5,'Senderos en familia','2026-12-14T10:00:00'),
   official(6,'Teatro familiar navideño','2026-12-15T17:00:00')
 ];
 const kids=upcomingEvents(e,pageForKey('con-ninos'),'2026-11-22');
 assert.deepEqual(kids.map(x=>x.id),[1,4,5,6]);
 assert.equal(familyFriendly(e[1]),false);
 assert.equal(familyFriendly(e[0]),true);
});
test('free means confirmed free, not missing price, zero or vague promotions',()=>{
 const e=[
   official(1,'Concierto gratuito','2026-12-10T20:00:00',{free:1,price:'Gratis'}),
   official(2,'Otro evento','2026-12-11T20:00:00',{free:null,price:''}),
   official(3,'Entrada sin confirmar','2026-12-12T20:00:00',{free:0,price:'Desde 0 €'}),
   official(4,'Feria gratis','2026-12-13T12:00:00',{free:true}),
 ];
 assert.deepEqual(upcomingEvents(e,pageForKey('gratis'),'2026-11-22').map(x=>x.id),[1,4]);
});
test('quality-gated intent pages avoid thin sitemap entries and include verified ones',()=>{
 const today=pageForKey('hoy'), kids=pageForKey('con-ninos');
 const events=[
   official(1,'Teatro familiar','2026-12-11T19:00:00'),
   official(2,'Musical familiar','2026-12-12T19:00:00'),
   official(3,'Senderos en familia','2026-12-13T10:00:00'),
   official(4,'Solo datos mínimos','2026-12-11T11:00:00',{details:'Consulta la fuente oficial.'})
 ];
 assert.equal(landingIndexable(kids,upcomingEvents(events,kids,'2026-11-22')),true);
 assert.equal(landingIndexable(today,upcomingEvents(events,today,'2026-12-11')),false);
 const xml=renderIntentSitemap(events,'2026-11-22');
 assert.match(xml,/\/que-hacer-con-ninos-gran-canaria/);
 assert.doesNotMatch(xml,/\/que-hacer-hoy-gran-canaria/);
 assert.doesNotMatch(xml,/\/planes-gratis-gran-canaria/);
 assert.doesNotMatch(xml,/\/que-hacer-este-fin-de-semana-gran-canaria/);
 assert.equal((xml.match(/<loc>/g)||[]).length,1);
});
test('multiple performances of one show cannot falsely qualify a thin landing',()=>{
 const kids=pageForKey('con-ninos');
 const sessions=[
  official(101,'Teatro familiar navideño','2026-12-11T19:00:00'),
  official(102,'Teatro familiar navideño','2026-12-12T19:00:00'),
  official(103,'Teatro familiar navideño','2026-12-13T19:00:00')
 ];
 assert.equal(landingIndexable(kids,upcomingEvents(sessions,kids,'2026-11-22')),false);
 const thin=renderLanding(pageForKey('hoy'),[sessions[0]],{today:'2026-12-11'});
 assert.equal(thin.indexable,false);
 assert.match(thin.html,/Teatro familiar navideño/);
 assert.doesNotMatch(thin.html,/Próximamente más planes/);
});
test('intent HTML is crawlable, correctly canonicalized and shows date not fictitious availability',()=>{
 const weekend=pageForKey('fin-de-semana');
 const events=[
   official(1,'Concierto viernes','2026-11-27T19:30:00'),
   official(2,'Actividad sábado','2026-11-28T10:00:00'),
   official(3,'Actividad domingo','2026-11-29T10:00:00'),
 ];
 const result=renderLanding(weekend,events,{today:'2026-11-23'});
 assert.equal(result.indexable,true);
 assert.equal(result.total,3);
 assert.match(result.html, /<link rel="canonical" href="https:\/\/dparranda\.es\/que-hacer-este-fin-de-semana-gran-canaria"/);
 assert.match(result.html, /<meta name="robots" content="index,follow/);
 assert.match(result.html, /viernes, 27 de noviembre de 2026/);
 assert.match(result.html, /Concierto viernes/);
 assert.match(result.html, /\/evento\/1/);
 assert.match(result.html, /que-hacer-con-ninos-gran-canaria/);
 assert.match(result.html, /planes-gratis-gran-canaria/);
 assert.doesNotMatch(result.html, /href="javascript:/);
 const poor=renderLanding(weekend,[events[0]],{today:'2026-11-23'});
 assert.equal(poor.indexable,false);
 assert.match(poor.html, /noindex,follow/);
});
