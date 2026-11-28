import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { validPwaEvent, growthStatsPayload, PWA_EVENT_TYPES } from '../lib/pwa-growth.js';

const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');

test('only four exact anonymous event types are accepted',()=>{
 assert.deepEqual(PWA_EVENT_TYPES,[
   'install_click','native_install','standalone_first','standalone_day'
 ]);
 for(const event of PWA_EVENT_TYPES)assert.equal(validPwaEvent({event}),event);
 for(const body of [null,{},[],{event:'fake'},{event:'install_click',id:'device123'},
   {event:'install_click',ip:'127.0.0.1'},{event:'install_click',user_agent:'x'}]){
   assert.equal(validPwaEvent(body),'');
 }
});

test('growth summary is numeric, grouped and never invents distinct people',()=>{
 const data=growthStatsPayload([
  {event_type:'install_click',today:'4',last_7_days:'11',last_30_days:'20',total:'40'},
  {event_type:'native_install',today:'1',last_7_days:'3',last_30_days:'7',total:'10'},
  {event_type:'invalid_event',total:'999'}
 ],[
  {day:'2026-11-28',event_type:'install_click',count:'4'},
  {day:'2026-11-28',event_type:'native_install',count:'1'},
  {day:'2026-11-28',event_type:'fake',count:'1000'},
  {day:'not a date',event_type:'install_click',count:'3000'}
 ]);
 assert.equal(data.metrics.install_click.last_30_days,20);
 assert.equal(data.metrics.native_install.total,10);
 assert.equal(data.metrics.standalone_first.total,0);
 assert.equal(data.daily.length,2);
 assert.equal(data.daily[0].day,'2026-11-28');
 assert.equal(data.daily[1].count,1);
 assert.match(data.notes,/no personas únicas/i);
});

test('backend uses pre-existing API, same-origin check, no identifier columns, auth-only reporting',()=>{
 const ads=read('api/ads.js'),admin=read('api/admin.js'),schema=read('sql/postgres_schema.sql');
 assert.match(ads,/op==='pwa-event'\)return recordPwaSignal/);
 assert.match(ads,/function recordPwaSignal\(req,res\)/);
 assert.match(ads,/if\(!sameOrigin\(req\)\)/);
 assert.match(ads,/if\(!event\)return res.status\(400\)/);
 assert.match(ads,/ON CONFLICT\(day,event_type\)/);
 assert.doesNotMatch(ads.slice(ads.indexOf('async function recordPwaSignal'),ads.indexOf('export default async function')),/x-forwarded-for|remoteAddress|userAgent/i);
 assert.match(admin,/if\(!authenticated\(req\)\)/);
 assert.match(admin,/op==='pwa-growth-stats'/);
 assert.match(admin,/FROM pwa_daily_stats GROUP BY event_type/);
 assert.match(schema,/CREATE TABLE IF NOT EXISTS pwa_daily_stats/);
 assert.match(schema,/PRIMARY KEY\(day,event_type\)/);
 assert.doesNotMatch(schema.slice(schema.indexOf('CREATE TABLE IF NOT EXISTS pwa_daily_stats'),schema.indexOf('CREATE TABLE IF NOT EXISTS catalog_sync')),/device_id|user_id|ip_address|user_agent|fingerprint|cookie/i);
 assert.equal(readdirSync(new URL('../api/',import.meta.url)).filter(p=>p.endsWith('.js')).length,12);
});

test('admin has independent growth section and avoids claims about unique installations',()=>{
 const html=read('public/admin/index.html'),js=read('public/admin/admin.js');
 for(const id of ['tabGrowth','growthSection','growthClicks30','growthNative30',
 'growthFirst30','growthDays30','growthDailyRows','growthStatus','refreshGrowth'])
   assert.ok(html.includes('id="'+id+'"'),id);
 assert.match(html,/No representan personas únicas/);
 assert.match(js,/await api\('pwa-growth-stats'\)/);
 assert.match(js,/setSection\('growth'\)/);
 assert.match(js,/growthDailyRows/);
});

test('install prompt emits aggregate signals without tracking personal identifiers',()=>{
 const src=read('public/install_prompt.js');
 assert.match(src,/reportMetric\('install_click'\)/);
 assert.match(src,/native_install/);
 assert.match(src,/standalone_first/);
 assert.match(src,/standalone_day/);
 assert.match(src,/timeZone:'Atlantic\/Canary'/);
 assert.match(src,/navigator.sendBeacon/);
 assert.match(src,/keepalive:true/);
 assert.doesNotMatch(src,/getCurrentPosition\(|randomUUID|crypto\.randomUUID|navigator\.geolocation/);
});
