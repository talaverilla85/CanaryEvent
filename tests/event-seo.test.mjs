import test from 'node:test';
import assert from 'node:assert/strict';
import {
 parseEventId,eventUrl,eventIndexable,eventExpired,eventPageRemoved,renderEventPage,renderEventSitemap
} from '../lib/event-seo.js';

const valid={
 id:654,title:'De la Aurora al Día',start:'2026-11-22T19:00:00',end:null,
 municipality:'Las Palmas de Gran Canaria',venue:'Teatro Pérez Galdós',
 category:'musica',accuracy:'venue',free:null,price:'',
 details:'Concierto de música antigua dedicado a Mateo Romero, conocido como el Maestro Capitán, con voces e instrumentos históricos en un programa del teatro. Una propuesta cultural para disfrutar de la música barroca en Gran Canaria.',
 source_url:'https://teatroperezgaldos.es/',source_name:'Teatro Pérez Galdós',
 image_url:'https://www.eventosgrancanaria.com/controlpanel/files/gridfs/6aabf7f0013a6268e079c63c',
 image_status:'official_remote'
};
test('stable numeric event URL, no slugs or changing titles',()=>{
 assert.equal(eventUrl(valid),'https://dparranda.es/evento/654');
 assert.equal(parseEventId('654'),654);
 assert.equal(parseEventId('-28220261122'),-28220261122);
 for(const bad of ['0','NaN','1-script','1/other','9007199254740992','-0',''])assert.equal(parseEventId(bad),null);
});
test('source-generated daily shopping workshops stay visible but not indexed as near-duplicates',()=>{
 const e={...valid,id:9001,start:'2026-12-04T17:00:00',
   source_name:'Centro Comercial Las Arenas · Club Arenillo',
   title:'Tren de renos del Polo Norte en Las Arenas'};
 assert.equal(eventIndexable(e,true,'2026-11-23'),false);
 assert.equal(eventIndexable({...e,source_name:'El Corte Inglés Mesa y López · Espectáculos de Navidad'},
                              true,'2026-11-23'),false);
 const page=renderEventPage(e,{active:true,today:'2026-11-23'});
 assert.equal(page.indexable,false);
 assert.match(page.html,/noindex,follow/);
 assert.doesNotMatch(renderEventSitemap([e],'2026-11-23'),/\/evento\/9001/);
});

test('complete verified event receives canonical and Event structured data',()=>{
 assert.equal(eventIndexable(valid,true,'2026-11-21'),true);
 const page=renderEventPage(valid,{active:true,today:'2026-11-21'});
 assert.equal(page.indexable,true);
 assert.match(page.html, /<link rel="canonical" href="https:\/\/dparranda\.es\/evento\/654">/);
 assert.match(page.html, /<meta name="robots" content="index,follow/);
 assert.match(page.html, /"@type":"Event"/);
 assert.match(page.html, /"startDate":"2026-11-22T19:00:00\+00:00"/);
 assert.match(page.html, /Teatro Pérez Galdós/);
 assert.match(page.html, /Abrir en D’Parranda/);
 assert.match(page.html, /brand\/dparranda-logo.svg/);
 assert.doesNotMatch(page.html, /mailto:|Ayúdanos a completar o corregir/);
});
test('winter and summer Canary offsets match the season',()=>{
 const summer={...valid,start:'2027-07-14T19:00:00'};
 const html=renderEventPage(summer,{active:true,today:'2027-07-01'}).html;
 assert.match(html, /"startDate":"2027-07-14T19:00:00\+01:00"/);
});
test('event with thin description still has page but stays out of sitemap',()=>{
 const thin={...valid,id:1001,accuracy:'municipality',details:'Consulta la fuente oficial.'};
 const rendered=renderEventPage(thin,{active:true,today:'2026-11-21'});
 assert.equal(rendered.indexable,false);
 assert.match(rendered.html, /noindex,follow/);
 assert.doesNotMatch(rendered.html, /"@type":"Event"/);
 assert.match(rendered.html, /\/evento\/1001/);
 const sitemap=renderEventSitemap([valid,thin], '2026-11-21');
 assert.match(sitemap, /\/evento\/654/);
 assert.doesNotMatch(sitemap, /\/evento\/1001/);
});
test('expired or withdrawn events are removed, but incomplete active ones remain available',()=>{
 assert.equal(eventPageRemoved(valid,true,'2026-11-22'),false);
 assert.equal(eventPageRemoved(valid,true,'2026-11-23'),true);
 assert.equal(eventPageRemoved(valid,false,'2026-11-21'),true);
 const unknownDate={...valid,id:1002,start:'',end:null};
 assert.equal(eventExpired(unknownDate,'2026-11-29'),false);
 assert.equal(eventPageRemoved(unknownDate,true,'2026-11-29'),false);
 assert.equal(eventIndexable(unknownDate,true,'2026-11-29'),false);
 const past=renderEventPage(valid,{active:true,today:'2026-11-29'});
 const archived=renderEventPage(valid,{active:false,today:'2026-11-21'});
 assert.equal(past.indexable,false);
 assert.equal(archived.indexable,false);
 assert.match(past.html,/ESTE EVENTO YA HA TERMINADO/);
 assert.match(archived.html,/YA NO FIGURA EN LA AGENDA ACTUAL/);
 assert.match(past.html,/Descubrir próximos planes/);
 assert.doesNotMatch(past.html,/href="\/\?evento=654"/);
 assert.match(archived.html,/href="\/que-hacer-en-gran-canaria"/);
 assert.match(past.html,/noindex,follow/);
 assert.doesNotMatch(archived.html,/"@type":"Event"/);
});
test('XSS-like content is escaped; fake external URLs are dropped',()=>{
 const e={...valid,id:911,title:'<img src=x onerror=alert(1)>',details:'a'.repeat(160),
 source_url:'javascript:alert(1)',image_url:'javascript:alert(1)'};
 const result=renderEventPage(e,{today:'2026-11-21'});
 assert.equal(result.indexable,false);
 assert.doesNotMatch(result.html,/<img src=x onerror/);
 assert.match(result.html,/<h1>Evento<\/h1>/);
 assert.doesNotMatch(result.html,/href="javascript:/);
});
test('sitemap only contains eligible future canonical URL once',()=>{
 const result=renderEventSitemap([valid,valid,{...valid,id:655,start:'2026-11-01T19:00:00'},
 {...valid,id:656,details:'Periodo de actividad con varias fechas. '+('x'.repeat(155))}], '2026-11-21');
 assert.equal((result.match(/<loc>/g)||[]).length,1);
 assert.match(result,/^\<\?xml version="1\.0"/);
});

test('inline poster fallback script is valid JavaScript',()=>{
 const html=renderEventPage(valid,{today:'2026-11-21'}).html;
 const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(x=>x[1]);
 assert.equal(scripts.length,1);
 for(const code of scripts)assert.doesNotThrow(()=>new Function(code));
});
