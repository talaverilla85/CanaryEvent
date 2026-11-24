import test from 'node:test';
import assert from 'node:assert/strict';
import {
  mallEventIdentity, mallGroups, mallPageForSlug, mallPagesWithContent,
  renderMallPage, renderMallSitemap, mallNavigationLinks
} from '../lib/mall-seo.js';

const detail='Actividad navideña del centro con fecha y hora contrastadas, programa publicado por la organización y condiciones a consultar en la fuente oficial antes de asistir.';
const official=(id,title,date,extra={})=>({
  id,title,start:date+'T17:00:00',end:null,
  municipality:'Las Palmas de Gran Canaria',venue:'Centro Comercial Las Arenas',
  source_name:'Centro Comercial Las Arenas · Club Arenillo',
  source_url:'https://cclasarenas.com/club-arenillo-programacion-navidad-2026/',
  details:detail,category:'familia',image_status:'official_remote',
  image_url:'https://cclasarenas.com/wp-content/uploads/2026/11/cartel-programa.jpg',
  image_alt:'Imagen oficial del programa navideño de Las Arenas',
  accuracy:'venue',...extra
});
const events=[
  official(101,'Taller de muñecos de nieve · Navidad en Las Arenas','2026-12-05',{
    details:detail+' Horario anunciado: 11:00–14:00, 17:00–20:00 h.',
    start:'2026-12-05T11:00:00',end:'2026-12-05T20:00:00'
  }),
  official(102,'Tren de renos · Navidad en Las Arenas','2026-12-06'),
  official(103,'Visita de Papá Noel · Navidad en Las Arenas','2026-12-07'),
  official(104,'Tren de renos · Navidad en Las Arenas','2026-12-08'),
  official(111,'Mercado Navideño Las Palmas','2026-11-20',{
    venue:'El Corte Inglés José Mesa y López',source_name:'El Corte Inglés Mesa y López · Mercado de Navidad',
    source_url:'https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/mercado-navideno-las-palmas',
    end:'2027-01-05T23:00:00',accuracy:'municipality'
  }),
  official(112,'Payaso Che Pedro · Navidad en Mesa y López','2026-12-04',{
    venue:'El Corte Inglés José Mesa y López',source_name:'El Corte Inglés Mesa y López · Espectáculos de Navidad',
    source_url:'https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/una-navidad-llena-de-magia-risas-y-diversion-para-toda-la-familia',
    accuracy:'municipality'
  }),
  official(113,'Mago Aníbal · Navidad en Mesa y López','2026-12-05',{
    venue:'El Corte Inglés José Mesa y López',source_name:'El Corte Inglés Mesa y López · Espectáculos de Navidad',
    source_url:'https://www.centroscomerciales.elcorteingles.es/centroscomerciales/es/eci/centros/centro-comercial-jose-mesa-y-lopez/eventos/una-navidad-llena-de-magia-risas-y-diversion-para-toda-la-familia',
    accuracy:'municipality'
  })
];

test('known verified centres derive stable URLs without static per-centre page files',()=>{
  const groups=mallGroups(events,'2026-11-24');
  assert.deepEqual(groups.map(g=>g.slug),['las-arenas','mesa-y-lopez']);
  assert.equal(groups.find(g=>g.slug==='las-arenas').events.length,4);
  assert.equal(groups.find(g=>g.slug==='mesa-y-lopez').events.length,3);
  assert.equal(mallEventIdentity(events[0]).slug,'las-arenas');
  assert.equal(mallEventIdentity(events[4]).slug,'mesa-y-lopez');
  const source=official(155,'Un concierto de estreno','2026-12-03',{
    venue:'Centro Comercial El Muelle',source_name:'Centro Comercial El Muelle · agenda oficial'
  });
  assert.equal(mallEventIdentity(source).slug,'el-muelle');
});

test('auto generated Christmas page contains full dates, official media, source, canonical and structured ItemList',()=>{
  const result=renderMallPage('las-arenas',events,{today:'2026-11-24'});
  assert.ok(result);
  assert.equal(result.indexable,true);
  assert.equal(result.total,4);
  assert.match(result.html,/<h1>Navidad en Centro Comercial Las Arenas 2026–2027<\/h1>/);
  assert.match(result.html,/Navidad en Centro Comercial Las Arenas 2026–2027 \| Programación y horarios/);
  assert.match(result.html,/canonical" href="https:\/\/dparranda.es\/centros-comerciales\/las-arenas"/);
  assert.match(result.html,/meta name="robots" content="index,follow/);
  assert.match(result.html,/Tren de renos/);
  assert.match(result.html,/Dos sesiones: 11:00–14:00 y 17:00–20:00/);
  assert.match(result.html,/Imagen oficial del programa navideño de Las Arenas/);
  assert.match(result.html,/https:\/\/cclasarenas.com\/wp-content\/uploads\/2026\/11\/cartel-programa.jpg/);
  assert.match(result.html,/Fuente del evento/);
  assert.match(result.html,/"@type":"ItemList"/);
  assert.match(result.html,/"numberOfItems":4/);
  assert.match(result.html,/"@type":"BreadcrumbList"/);
  assert.doesNotMatch(result.html,/ESPACIO PATROCINADO/);
  assert.doesNotMatch(result.html,/drive\.google\.com/i);
});

test('Mesa y López merges its separate official market and shows sources without changing venue',()=>{
  const result=renderMallPage('mesa-y-lopez',events,{today:'2026-11-24'});
  assert.ok(result?.indexable);
  assert.equal(result.total,3);
  assert.match(result.html,/Navidad en El Corte Inglés José Mesa y López/);
  assert.match(result.html,/Mercado Navideño Las Palmas/);
  assert.match(result.html,/Payaso Che Pedro/);
  assert.match(result.html,/Mago Aníbal/);
  assert.match(result.html,/centro-comercial-jose-mesa-y-lopez/);
});

test('weak centres are rendered noindex, absent centres are not published or in sitemap',()=>{
  const tiny=[official(1,'Taller de Navidad','2026-12-01')];
  const weak=renderMallPage('las-arenas',tiny,{today:'2026-11-24'});
  assert.ok(weak && !weak.indexable);
  assert.match(weak.html,/noindex,follow/);
  assert.equal(renderMallPage('siete-palmas',tiny,{today:'2026-11-24'}),null);
  assert.equal(renderMallPage('../admin',tiny,{today:'2026-11-24'}),null);
  assert.doesNotMatch(renderMallSitemap(tiny,'2026-11-24'),/centros-comerciales\/las-arenas/);
  assert.deepEqual(mallNavigationLinks(tiny,'2026-11-24'),[]);
});

test('only distinct and sufficiently documented event programmes may be indexed',()=>{
  const repeat=[official(1,'Taller del centro','2026-12-01'),
    official(2,'Taller del centro','2026-12-02'),
    official(3,'Taller del centro','2026-12-03')];
  assert.equal(renderMallPage('las-arenas',repeat,{today:'2026-11-24'}).indexable,false);
  const poor=[...events,official(301,'Descuento especial','2026-12-02',{details:'Oferta',paid_promotion:true}),
    official(302,'Actividad comercial','2026-12-04',{source_name:'Empresa anunciante',details:detail}),
    official(303,'Taller familiar','2026-12-04',{source_url:'javascript:alert(1)'})];
  assert.equal(renderMallPage('las-arenas',poor,{today:'2026-11-24'}).total,4);
});

test('sitemap automatically adds qualifying centres and removes them when programme ends',()=>{
  const xml=renderMallSitemap(events,'2026-11-24');
  assert.match(xml,/https:\/\/dparranda.es\/centros-comerciales\/las-arenas/);
  assert.match(xml,/https:\/\/dparranda.es\/centros-comerciales\/mesa-y-lopez/);
  assert.equal((xml.match(/<loc>/g)||[]).length,2);
  assert.deepEqual(mallPagesWithContent(events,'2026-11-24').map(p=>p.path),[
    '/centros-comerciales/las-arenas','/centros-comerciales/mesa-y-lopez'
  ]);
  assert.match(mallNavigationLinks(events,'2026-11-24')[0].title,/Navidad en/);
  assert.doesNotMatch(renderMallSitemap(events,'2027-03-01'),/centros-comerciales/);
  assert.equal(renderMallPage('las-arenas',events,{today:'2027-03-01'}),null);
});

test('a future non-Christmas programme gets an evergreen events page',()=>{
  const regular=[
    official(201,'Taller de dibujo','2027-03-06',{details:detail.replaceAll('navideña','familiar')}),
    official(202,'Festival de ciencia','2027-03-07',{details:detail.replaceAll('navideña','familiar')}),
    official(203,'Cuentacuentos infantil','2027-03-08',{details:detail.replaceAll('navideña','familiar')})
  ];
  const page=mallPageForSlug(regular,'las-arenas','2027-03-01');
  assert.equal(page.heading,'Eventos en Centro Comercial Las Arenas');
  assert.equal(page.path,'/centros-comerciales/las-arenas');
  assert.equal(renderMallPage('las-arenas',regular,{today:'2027-03-01'}).indexable,true);
});

test('untrusted HTML in venue and titles cannot execute in generated landing',()=>{
  const input=[
    ...events.slice(0,3),
    official(401,'<img src=x onerror=alert(1)>','2026-12-09')
  ];
  const page=renderMallPage('las-arenas',input,{today:'2026-11-24'});
  assert.doesNotMatch(page.html,/<img src=x onerror/);
  assert.match(page.html,/&lt;img src=x onerror/);
  assert.doesNotMatch(page.html,/href="javascript:/);
});
