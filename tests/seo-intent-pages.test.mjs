import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SEO_PAGES, pageForKey, canaryToday, intentPeriod, familyFriendly,
  upcomingEvents, christmasRelated, landingIndexable, renderLanding, renderIntentSitemap
} from '../lib/seo-pages.js';

const official=(id,title,start,extra={})=>({
 id,title,start,end:null,municipality:'Las Palmas de Gran Canaria',
 venue:'Teatro Pérez Galdós',accuracy:'venue',category:'cultura',
 details:'El organizador confirma esta función con un programa detallado, una hora de comienzo y un lugar definido para asistentes en Gran Canaria.',
 source_url:'https://teatroperezgaldos.es/cartelera',
 ...extra
});

test('five evergreen intent pages have unique readable URL, title and metadata',()=>{
 const types=['weekend','today','kids','christmas','free'];
 assert.equal(SEO_PAGES.filter(p=>p.kind).length,5);
 assert.deepEqual(SEO_PAGES.filter(p=>p.kind).map(p=>p.kind),types);
 assert.equal(new Set(SEO_PAGES.map(p=>p.path)).size,10);
 for(const page of SEO_PAGES.filter(p=>p.kind)){
   assert.equal(pageForKey(page.key),page);
   assert.match(page.path,/^\/[a-z-]+$/);
   assert.match(page.title,/D’Parranda/);
   assert.ok(page.description.length>=80);
 }
});


test('Christmas selection includes official family, retail-centre and municipal plans, but no sales or sponsored events',()=>{
 const christmas=pageForKey('navidad');
 const data=[
  official(201,'Visita de Papá Noel','2026-12-20T17:00:00'),
  official(202,'Encendido de luces de Navidad','2026-11-27T19:00:00'),
  official(203,'Cabalgata de Reyes Magos','2027-01-05T18:00:00'),
  official(204,'Gran mercadillo navideño','2026-12-02T12:00:00'),
  official(205,'Rebajas de invierno','2026-12-03T10:00:00'),
  official(206,'Concierto de Los Coquillos','2026-12-04T20:00:00'),
  official(207,'Visita de Papá Noel','2026-12-05T17:00:00',{paid_promotion:true}),
  official(208,'Taller infantil de Navidad ya terminado','2026-11-20T17:00:00')
 ];
 const result=upcomingEvents(data,christmas,'2026-11-23');
 assert.deepEqual(result.map(x=>x.id),[202,204,201,203]);
 assert.equal(christmasRelated(data[4]),false);
 assert.equal(christmasRelated(data[0]),true);
 assert.equal(landingIndexable(christmas,result),true);
 assert.match(renderIntentSitemap(data,'2026-11-23'),/\/navidad-gran-canaria/);
 assert.doesNotMatch(renderIntentSitemap([data[0],data[1]],'2026-11-23'),/\/navidad-gran-canaria/);
 const empty=renderLanding(christmas,data,{today:'2027-01-07'});
 assert.equal(empty.indexable,false);
});

test('one Christmas workshop card clearly includes both sessions on the same date',()=>{
 const event=official(812,'Taller de muñecos de nieve · Navidad en Las Arenas',
   '2026-12-05T11:00:00',{
     end:'2026-12-05T20:00:00',
     details:'Actividad navideña familiar. Horario anunciado: 11:00–14:00, 17:00–20:00 h. Consulta la programación oficial.',
   });
 const html=renderLanding(pageForKey('navidad'),[event],{today:'2026-11-23'}).html;
 assert.equal((html.match(/class="event-card"/g)||[]).length,1);
 assert.match(html,/Dos sesiones: 11:00–14:00 y 17:00–20:00/);
 assert.doesNotMatch(html,/11:00–20:00/);
});

test('Christmas card opens details without asking users already on D’Parranda to visit D’Parranda',()=>{
  const p=pageForKey('navidad');
  const e=official(998,'Encendido de Navidad en Guía','2026-11-26T20:30:00',{
    image_status:'official_remote',
    image_url:'https://santamariadeguia.es/wp-content/uploads/2026/11/WhatsApp-Image-2026-11-20-at-14.19.48.jpeg',
    image_alt:'Imagen oficial del encendido',
  });
  const page=renderLanding(p,[e],{today:'2026-11-23'});
  assert.match(page.html,/Ver detalles del evento/);
  assert.doesNotMatch(page.html,/Ver el plan en D’Parranda/);
  assert.match(page.html,/href="\/evento\/998"/);
  assert.match(page.html,/src="https:\/\/santamariadeguia.es\/wp-content/);
  const v=renderLanding(p,[official(618,'III Mercado Navideño','2026-11-28T10:00:00',{
    image_status:'official_remote',image_url:'https://www.vegadesanmateo.es/sites/default/files/noticias/Cartel.jpg',
  })],{today:'2026-11-23'});
  assert.match(v.html,/src="https:\/\/www.vegadesanmateo.es\/sites\/default\/files\/noticias\/Cartel.jpg"/);
});

test('Christmas displays validated official programme artwork, not arbitrary remote images',()=>{
 const item=official(198,'Tren de renos del Polo Norte','2026-12-04T17:00:00',{
  source_name:'Centro Comercial Las Arenas · Club Arenillo',
  source_url:'https://cclasarenas.com/club-arenillo-programacion-navidad-2026/',
  image_url:'https://cclasarenas.com/wp-content/uploads/2026/11/cartel.jpg',
  image_status:'official_remote',
  image_alt:'Imagen oficial del programa navideño de Las Arenas',
 });
 const html=renderLanding(pageForKey('navidad'),[item],{today:'2026-11-23'}).html;
 assert.match(html, /<img class="official-cover[^"]*" src="https:\/\/cclasarenas.com\/wp-content\/uploads\/2026\/11\/cartel.jpg"/);
 assert.match(html, /alt="Imagen oficial del programa navideño de Las Arenas"/);
 const bad=renderLanding(pageForKey('navidad'),[{...item,image_url:'https://evil.example/cartel.jpg'}],{today:'2026-11-23'}).html;
 assert.doesNotMatch(bad, /<img class="official-cover/);
});
test('Christmas page has a current seasonal title, accessible cards and an explicit separately labelled AriMar ad',()=>{
 const page=pageForKey('navidad');
 const e=[
  official(201,'Visita de Papá Noel','2026-12-20T17:00:00'),
  official(202,'Encendido de luces de Navidad','2026-12-19T19:00:00'),
  official(203,'Cabalgata de Reyes Magos','2027-01-05T18:00:00'),
  official(204,'Tren de renos','2026-12-04T17:00:00')
 ];
 const ad={
  id:'arimar-fundador',enabled:true,advertiser:'AriMar',
  headline:'AriMar · comida casera 100 % sin gluten',
  description:'Pide online en Playa de Arinaga',
  button_url:'https://arimarfoodlab.es/pedir',button_text:'Pedir online',
  image:'/sponsors/arimar-pollo-asado.webp',image_alt:'Pollo asado'
 };
 const result=renderLanding(page,e,{today:'2026-11-23',sponsor:ad});
 assert.equal(result.indexable,true);
 assert.match(result.html,/Navidad en Gran Canaria 2026/);
 assert.match(result.html,/canonical" href="https:\/\/dparranda.es\/navidad-gran-canaria/);
 assert.match(result.html,/ESPACIO PATROCINADO/);
 assert.match(result.html,/utm_content=navidad/);
 assert.match(result.html,/data-sponsored-click="arimar-fundador"/);
 assert.equal((result.html.match(/data-sponsored-click="arimar-fundador"/g)||[]).length,1);
 assert.match(result.html,/rel="sponsored noopener noreferrer"/);
 const normal=renderLanding(pageForKey('con-ninos'),e,{today:'2026-11-23',sponsor:ad});
 assert.doesNotMatch(normal.html,/ESPACIO PATROCINADO/);
 const paused=renderLanding(page,e,{today:'2026-11-23',sponsor:{...ad,enabled:false}});
 assert.doesNotMatch(paused.html,/ESPACIO PATROCINADO/);
 assert.match(renderLanding(page,e,{today:'2027-01-02'}).html,/Navidad en Gran Canaria 2026/);
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
