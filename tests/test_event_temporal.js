/* Deterministic regression tests for Canary-time event availability.
 * Run: node tests/test_event_temporal.js
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const T = require('../public/temporal.js');

const now = '2026-10-29T22:40';
const event = (start, end = null) => ({start, end});
const cases = [
  ['19:00 start without verified end',event('2026-10-29T19:00:00'),true],
  ['19:30 start without verified end',event('2026-10-29T19:30:00'),true],
  ['20:00 start without verified end',event('2026-10-29T20:00:00'),true],
  ['already ended with explicit finish',event('2026-10-29T19:00:00','2026-10-29T20:30:00'),true],
  ['ends at current minute',event('2026-10-29T19:00:00','2026-10-29T22:40:00'),true],
  ['ongoing concert until 23:15',event('2026-10-29T20:00:00','2026-10-29T23:15:00'),false],
  ['late concert 23:00',event('2026-10-29T23:00:00'),false],
  ['starts at current minute',event('2026-10-29T22:40:00'),false],
  ['unknown hours today',event('2026-10-29'),false],
  ['multiday exhibition ends tomorrow',event('2026-10-15','2026-10-30'),false],
  ['multiday exhibition ends today',event('2026-10-15','2026-10-29'),false],
  ['multiday with verified finishing hour',event('2026-10-27T18:00:00','2026-10-30T01:00:00'),false],
  ['multiday opening hour past, no daily schedule',event('2026-10-28T19:00:00','2026-10-30'),false],
  ['yesterday one-off without end',event('2026-10-28T19:00:00'),true],
  ['tomorrow at midnight',event('2026-10-30T00:05:00'),false],
  ['yesterday ending 02:00 today',event('2026-10-28T23:30:00','2026-10-29T02:00:00'),true]
];
for (const [name, e, expected] of cases) {
  assert.equal(T.hasFinished(e,now),expected,name);
}
assert.equal(T.isInProgress(event('2026-10-29T20:00:00','2026-10-29T23:15:00'),now),true);
assert.equal(T.isInProgress(event('2026-10-29T20:00:00'),now),false);
assert.equal(T.hasUnconfirmedHours(event('2026-10-29'),now),true);
assert.equal(T.hasUnconfirmedHours(event('2026-10-29T23:00:00'),now),false);

// The same expiry rule must guard ALL filters (not just "today").
const html = fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8');
const start=html.indexOf('function inFilter(e){');
const stop=html.indexOf('function eventScore(e){',start);
assert.ok(start>=0&&stop>start,'Home page contains inFilter');
const state={when:'today',dateRange:null};
const plusDays=(d,n)=>new Date(Date.parse(d+'T00:00:00Z')+n*86400000).toISOString().slice(0,10);
const func=new Function('DParrandaTime','localTimeKey','todayKey','plusDays','eventEndDate','state',
  html.slice(start,stop)+';return inFilter;');
const filter=func(T,()=>now,()=>now.slice(0,10),plusDays,e=>(e.end||e.start).slice(0,10),state);
for(const when of ['today','week','weekend','all','custom']) {
  state.when=when;
  if(when==='custom')state.dateRange={start:'2026-10-01',end:'2026-10-31'};
  assert.equal(filter(event('2026-10-29T19:00:00')),false,'Past concert in '+when);
}
state.when='today';
assert.equal(filter(event('2026-10-29T23:00:00')),true);
assert.equal(filter(event('2026-10-29T20:00:00','2026-10-29T23:15:00')),true);
assert.equal(filter(event('2026-10-29','2026-10-30')),true);
console.log('PASS: '+cases.length+' time fixtures, ongoing and all-filter regression checks.');
