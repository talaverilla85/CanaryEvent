/* Exercise the actual browser filter/cache helpers without the DOM/network. */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8');
function section(a,b){
 const start=html.indexOf(a);
 const end=html.indexOf(b,start);
 assert.ok(start>=0&&end>start,'Could not locate live frontend code');
 return html.slice(start,end);
}
let clockCalls=0,unknownCalls=0,approxCalls=0;
const events=[
 {id:1,title:'Música al atardecer',start:'2026-11-09T18:00:00',municipality:'Telde',venue:'Plaza',category:'musica',distance:10},
 {id:2,title:'Artes escénicas',start:'2026-11-09T13:00:00',municipality:'Telde',venue:'Teatro',category:'cultura',distance:2},
 {id:3,title:'Taller de arte',start:'2026-11-10T09:00:00',municipality:'Agüimes',venue:'Centro',category:'cultura',distance:1}
];
const pad=n=>String(n).padStart(2,'0');
function plusDays(date,offset){
 const d=new Date(date+'T12:00:00Z');
 d.setUTCDate(d.getUTCDate()+offset);
 return d.toISOString().slice(0,10);
}
const ctx={
 state:{events,when:'all',island:'Gran Canaria',freeOnly:false,
   categories:new Set(),municipality:'',query:'',tab:'explore',newOnly:false,
   favorites:new Set(),newEventIds:new Set(),sort:'recommended'},
 localTimeKey:()=>{clockCalls++;return '2026-11-09T12:00'},
 todayKey:()=>{throw new Error('todayKey should be reused from the clock')},
 eventApprox:e=>{approxCalls++;return e.distance},
 eventEndDate:e=>e.end||e.start.slice(0,10),
 plusDays,
 DParrandaTime:{
  hasFinished:()=>false,
  hasUnconfirmedHours:()=>{unknownCalls++;return false},
  isInProgress:()=>false
 }
};
vm.createContext(ctx);
vm.runInContext(section('function inFilter(e,today=', '\nfunction sponsorUrl('),ctx);
function ids(){return Array.from(vm.runInContext('filtered()',ctx),e=>e.id)}
assert.deepEqual(ids(),[2,1,3]);
assert.equal(clockCalls,1,'One timezone lookup per sort');
assert.ok(approxCalls<=events.length,'Distance must be computed once per event');
assert.ok(unknownCalls<=2*events.length,'No comparator-time rechecks');
ctx.state.query='artes';
assert.deepEqual(ids(),[2]);
ctx.state.query='';
ctx.state.sort='near';
assert.deepEqual(ids(),[3,2,1]);
ctx.state.sort='time';
assert.deepEqual(ids(),[2,1,3]);
ctx.state.sort='recommended';
ctx.state.tab='saved';
ctx.state.favorites=new Set([1]);
assert.deepEqual(ids(),[1]);
assert.equal(clockCalls,5);
const stored=new Map();
const page={textContent:''};
let renders=0;
const queued=[];
const official={id:10,title:'Concierto confirmado',start:'2026-11-12T20:00:00',paid_promotion:false};
const paid={id:-99,title:'Campaña limitada',start:'2026-11-12T20:00:00',paid_promotion:true};
stored.set('plangc_event_cache',JSON.stringify({at:Date.now(),events:[official,paid]}));
const cacheCtx={
 localStorage:{
  getItem:key=>stored.get(key)||null,
  setItem:(key,value)=>{stored.set(key,String(value))}
 },
 state:{events:[]},
 $:()=>page,
 render:()=>{renders++},
 setTimeout:fn=>{queued.push(fn);return queued.length}
};
vm.createContext(cacheCtx);
vm.runInContext(section('// Warm-start with a bounded public-only snapshot',
  '\nasync function loadEvents(){'),cacheCtx);
const fetched=vm.runInContext('readCachedCatalog(EVENT_CACHE_WARM_MAX_AGE)',cacheCtx);
assert.equal(fetched.length,1);
assert.equal(fetched[0].id,10);
vm.runInContext('showCachedCatalog()',cacheCtx);
assert.equal(renders,1);
assert.equal(cacheCtx.state.events.length,1);
assert.match(page.textContent,/Actualizando/);
cacheCtx.toSave=[official,paid];
vm.runInContext('scheduleCatalogCache(toSave)',cacheCtx);
assert.equal(queued.length,1,'Cache write must be deferred');
assert.equal(JSON.parse(stored.get('plangc_event_cache')).events.length,2);
queued.shift()();
assert.deepEqual(JSON.parse(stored.get('plangc_event_cache')).events.map(e=>e.id),[10]);
stored.set('plangc_event_cache',JSON.stringify({
 at:Date.now()-8*24*60*60*1000,events:[official]
}));
assert.equal(vm.runInContext('readCachedCatalog(EVENT_CACHE_OFFLINE_MAX_AGE)',cacheCtx),null,
 'A week-old snapshot must not be presented as reliable offline events');
console.log('Catalog runtime OK: one clock per filter, memoized scores, fresh official-only cache, deferred writes');
