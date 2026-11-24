import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { ECI_PROGRAMMES, eciOfficialImageUrl, eciOfficialImageKind, browserPosterUrl } from '../lib/official-poster.js';
import { relayOfficialPoster } from '../api/official-poster.js';
import { pageForKey, renderLanding, officialPosterUrl } from '../lib/seo-pages.js';
import { renderEventPage } from '../lib/event-seo.js';
import { renderMallPage } from '../lib/mall-seo.js';

const showsImage='https://www.centroscomerciales.elcorteingles.es/centroscomerciales/uploads/events/eci-eventosinfantiles.jpg';
const marketImage='https://www.centroscomerciales.elcorteingles.es/centroscomerciales/uploads/events/ECI%20MERCADILLOS_001_1920x960px_ES_000%201%20(1)%20(2).jpg';
const detail='El organizador anuncia una actividad navideña con fecha y horario confirmados en el Mercado de Navidad de Mesa y López. Entrada libre. Consulta la fuente oficial antes de acudir.';
function sample(kind='shows', id=1064) {
  const rule=ECI_PROGRAMMES[kind];
  return {
    id,title:kind==='shows'?'Payaso Che Pedro · Navidad en Mesa y López':'Mercado Navideño Las Palmas',
    start:'2026-12-04T18:00:00',end:'2026-12-04T19:00:00',
    venue:'El Corte Inglés José Mesa y López',municipality:'Las Palmas de Gran Canaria',
    category:'familia',accuracy:'municipality',details:detail,source_name:rule.source_name,
    source_url:rule.source_url,image_origin:rule.source_url,
    image_url:kind==='shows'?showsImage:marketImage,
    image_status:'official_remote',image_alt:'Imagen oficial del programa'
  };
}
function responseSink(){
  const headers={};
  const obj={
    code:0,body:null,headers,
    setHeader(k,v){headers[k.toLowerCase()]=v;return this;},
    status(s){this.code=s;return this;},
    end(b){this.body=b;return this;}
  };
  return obj;
}
function fakeRemote(bytes=Buffer.from('f'.repeat(128)),mime='image/jpeg',length=bytes.length) {
  return new Response(bytes,{status:200,headers:{
    'content-type':mime,'content-length':String(length)
  }});
}
const dbWith=(event)=>()=>async()=>event?[{payload:event}]:[];

test('only the exact verified Mesa y López programme sources can be relayed',()=>{
  assert.equal(eciOfficialImageKind(sample('shows')),'shows');
  assert.equal(eciOfficialImageKind(sample('market')),'market');
  assert.equal(eciOfficialImageUrl(sample('shows'),'shows'),showsImage);
  assert.equal(eciOfficialImageUrl(sample('market'),'market'),marketImage);
  assert.equal(eciOfficialImageUrl({...sample(),source_url:'https://evil.example'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),image_origin:'https://evil.example'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),image_url:'http://evil.example/a.jpg'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),image_url:'https://localhost/a.jpg'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),image_url:'https://www.centroscomerciales.elcorteingles.es/admin/secret.jpg'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),image_url:showsImage+'?token=123'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),image_status:'promotional'},'shows'),'');
  assert.equal(eciOfficialImageUrl({...sample(),paid_promotion:true},'shows'),'');
});

test('SEO cards, event details, and the automatic mall page show images from DParranda',()=>{
  const events=[
    sample('shows',1064),{...sample('shows',1065),title:'Mago Aníbal'},
    {...sample('shows',1066),title:'Payaso Tadeo'},
    sample('market',1063)
  ];
  assert.equal(officialPosterUrl(events[0]),showsImage);
  assert.equal(browserPosterUrl(events[0],showsImage),'/api/official-poster?kind=shows');
  assert.equal(browserPosterUrl(events[3],marketImage),'/api/official-poster?kind=market');
  const christmas=renderLanding(pageForKey('navidad'),events,{today:'2026-11-24'});
  assert.match(christmas.html,/src="\/api\/official-poster\?kind=shows"/);
  assert.match(christmas.html,/src="\/api\/official-poster\?kind=market"/);
  assert.match(christmas.html,/data-poster-source="https:\/\/www.centroscomerciales.elcorteingles.es/);
  const detailPage=renderEventPage(events[0],{today:'2026-11-24'});
  assert.match(detailPage.html,/src="\/api\/official-poster\?kind=shows"/);
  assert.match(detailPage.html,/https:\/\/www.centroscomerciales.elcorteingles.es\/centroscomerciales\/uploads\/events/);
  const mall=renderMallPage('mesa-y-lopez',events,{today:'2026-11-24'});
  assert.ok(mall?.indexable);
  assert.match(mall.html,/src="\/api\/official-poster\?kind=shows"/);
  assert.match(mall.html,/src="\/api\/official-poster\?kind=market"/);
  assert.match(mall.html,/Fuente del evento/);
  assert.doesNotMatch(mall.html,/drive.google.com/);
});

test('front page permits official shopping-centre image host and chooses the relay',()=>{
  const html=readFileSync(new URL('../public/index.html',import.meta.url),'utf8');
  assert.match(html,/'cclasarenas.com','www.centroscomerciales.elcorteingles.es','sietepalmascc.com'/);
  assert.match(html,/return '\/api\/official-poster\?kind='\+kind/);
  assert.match(html,/e.image_origin===e.source_url/);
});

test('same-origin endpoint streams bytes for approved event with strict GET and CDN caching',async()=>{
  const req={method:'GET',query:{kind:'shows'}},res=responseSink();
  const bytes=Buffer.from('f'.repeat(128));
  const called=[];
  await relayOfficialPoster(req,res,{
    database:dbWith(sample()),
    fetchRemote:async(url,config)=>{called.push({url,config});return fakeRemote(bytes);}
  });
  assert.equal(res.code,200);
  assert.equal(res.headers['content-type'],'image/jpeg');
  assert.equal(res.headers['cross-origin-resource-policy'],'same-origin');
  assert.match(res.headers['cache-control'],/s-maxage=3600/);
  assert.deepEqual(res.body,bytes);
  assert.equal(called.length,1);
  assert.equal(called[0].url,showsImage);
  assert.equal(called[0].config.redirect,'manual');
});

test('relay rejects arbitrary kinds, unauthorized source rows and bad upstream files',async()=>{
  let res=responseSink();
  await relayOfficialPoster({method:'POST',query:{kind:'shows'}},res,{database:dbWith(sample())});
  assert.equal(res.code,405);
  res=responseSink();
  await relayOfficialPoster({method:'GET',query:{kind:'https://evil.example'}},res,{database:dbWith(sample())});
  assert.equal(res.code,404);
  res=responseSink();
  await relayOfficialPoster({method:'GET',query:{kind:'shows'}},res,{database:dbWith(null)});
  assert.equal(res.code,404);
  res=responseSink();
  await relayOfficialPoster({method:'GET',query:{kind:'shows'}},res,{
    database:dbWith({...sample(),source_name:'Unapproved'}),fetchRemote:()=>{throw Error('must not fetch');}
  });
  assert.equal(res.code,404);
  res=responseSink();
  await relayOfficialPoster({method:'GET',query:{kind:'shows'}},res,{
    database:dbWith(sample()),fetchRemote:async()=>fakeRemote(undefined,'text/html')
  });
  assert.equal(res.code,502);
  res=responseSink();
  await relayOfficialPoster({method:'GET',query:{kind:'shows'}},res,{
    database:dbWith(sample()),fetchRemote:async()=>fakeRemote(undefined,'image/jpeg',2_500_001)
  });
  assert.equal(res.code,502);
  res=responseSink();
  await relayOfficialPoster({method:'GET',query:{kind:'shows'}},res,{
    database:dbWith(sample()),fetchRemote:async()=>new Response('Redirect',{status:301,headers:{location:'https://evil.example'}})
  });
  assert.equal(res.code,502);
});
