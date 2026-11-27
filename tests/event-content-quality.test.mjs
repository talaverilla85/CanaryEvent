import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cleanEventDescription, renderEventPage, eventIndexable } from '../lib/event-seo.js';

const malformed='<p>El Club de Mayores organiza una salida cultural para conocer el '
+'Jardín de la Marquesa de Arucas. El Jardín de la ... '
+'<a class="read-more" href="https://eventos.santabrigida.es/eventos/salida-cultural-jardin-de-la-marquesa/">Leer más</a></p>\\n';
const base={
 id:941,title:'«SALIDA CULTURAL JARDÍN DE LA MARQUESA»',
 start:'2026-11-27T09:00:00',end:'2026-11-27T18:00:00',
 municipality:'Santa Brígida',
 venue:'CLUB MUNICIPAL DE MAYORESDE LA VILLA DE SANTA BRIGIDA',
 source_name:'Ayuntamiento de Santa Brígida · agenda de eventos',
 source_url:'https://eventos.santabrigida.es/eventos/salida-cultural-jardin-de-la-marquesa/',
 details:malformed,category:'ocio',accuracy:'municipality',free:null,price:''
};
test('standalone SEO event never prints raw HTML or WordPress read-more',()=>{
 const clean=cleanEventDescription(malformed);
 assert.doesNotMatch(clean,/<p>|<a|href=|\\n|Leer más/);
 const result=renderEventPage(base,{today:'2026-11-27'});
 assert.doesNotMatch(result.html,/&lt;p&gt;|&lt;a |read-more|href=&quot;/);
 assert.match(result.html,/Club de Mayores organiza una salida cultural/);
 assert.match(result.html,/Punto exacto sin verificar; consulta la fuente/);
 assert.equal(eventIndexable(base,true,'2026-11-27'),false);
});
test('public PWA cleans copy before escaping and disables misleading directions',()=>{
 const html=readFileSync(new URL('../public/index.html',import.meta.url),'utf8');
 assert.match(html,/function plainEventDescription\(value\)/);
 assert.match(html,/escapeHTML\(plainEventDescription\(e\.details\)/);
 assert.match(html,/eventUsesMunicipality\(e\)\|\|venueName\(e\)==='Recinto por confirmar'/);
 assert.match(html,/const eventUsesMunicipality=e=>e\.accuracy==='municipality'/);
});
