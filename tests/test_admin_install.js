/* Runtime tests for the independent /admin/ install flow. Run: node tests/test_admin_install.js */
'use strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const __dirname=fileURLToPath(new URL('.',import.meta.url));
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../public/admin/install.js'),'utf8');

function setup({ios=false,standalone=false}={}){
 const handlers={},elements={},storage=new Map(),calls=[];
 const create=id=>{
  const events={};
  return {
   id,hidden:id==='adminInstallDock',open:false,textContent:'',children:[],
   addEventListener(name,cb){(events[name]??=[]).push(cb)},
   click(){for(const fn of events.click||[])fn({target:this})},
   replaceChildren(){this.children=[]},
   append(el){this.children.push(el)},
   showModal(){this.open=true},
   close(){this.open=false},
   setAttribute(n){if(n==='open')this.open=true},
   removeAttribute(n){if(n==='open')this.open=false}
  };
 };
 for(const id of ['adminInstallDock','adminInstallBtn','adminInstallDismiss',
  'adminInstallGuide','adminInstallSteps','adminInstallIntro','adminInstallClose']){
  elements[id]=create(id);
 }
 const localStorage={
  setItem(k,v){storage.set(k,v)},getItem(k){return storage.get(k)||null}
 };
 const window={
  matchMedia(query){return {matches:query.includes('display-mode')?standalone:false,addEventListener(){}}},
  addEventListener(event,cb){(handlers[event]??=[]).push(cb)}
 };
 const navigator={
  standalone:false,userAgent:ios?'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)':'Mozilla/5.0 (Linux; Android 15)',
  platform:ios?'iPhone':'Linux',maxTouchPoints:ios?5:1,
  serviceWorker:{register(url,opts){calls.push({url,opts});return Promise.resolve()}}
 };
 const document={getElementById:id=>elements[id]||null,createElement:tag=>create(tag)};
 vm.runInNewContext(source,{window,document,navigator,localStorage,Date,Promise,console},{filename:'admin/install.js'});
 const emit=(event,value={})=>{for(const cb of handlers[event]||[])cb(value)};
 return {elements,emit,calls,storage};
}

async function test(){
 const a=setup();
 assert.equal(a.elements.adminInstallDock.hidden,false,'uninstalled browser invites installation');
 a.elements.adminInstallBtn.click();
 assert.equal(a.elements.adminInstallGuide.open,true,'manual browser fallback opens a guide');
 assert.equal(a.elements.adminInstallSteps.children.length,3);
 a.elements.adminInstallClose.click();
 assert.equal(a.elements.adminInstallGuide.open,false);
 a.emit('load');
 assert.equal(a.calls.length,1,'register an independent admin service worker');
 assert.equal(a.calls[0].url,'/admin/sw.js');
 assert.equal(a.calls[0].opts.scope,'/admin/');

 const b=setup({ios:true});
 b.elements.adminInstallBtn.click();
 assert.match(b.elements.adminInstallIntro.textContent,/Safari/);
 assert.match(b.elements.adminInstallSteps.children[1].textContent,/pantalla de inicio/);

 const c=setup({standalone:true});
 assert.equal(c.elements.adminInstallDock.hidden,true,'installed app hides install CTA');

 const d=setup();
 d.elements.adminInstallDismiss.click();
 assert.equal(d.elements.adminInstallDock.hidden,true,'dismiss CTA in this visit');

 const e=setup();
 let calls=0,prevented=false;
 e.emit('beforeinstallprompt',{
  preventDefault(){prevented=true},
  prompt(){calls++;return Promise.resolve()},
  userChoice:Promise.resolve({outcome:'accepted'})
 });
 e.elements.adminInstallBtn.click();
 await new Promise(setImmediate);
 assert.equal(prevented,true);
 assert.equal(calls,1);
 assert.equal(e.elements.adminInstallDock.hidden,true,'native installation hides CTA');
 assert.ok(Number(e.storage.get('dparranda_admin_installed_hint_v1'))>0);

 const f=setup();
 f.emit('appinstalled');
 assert.equal(f.elements.adminInstallDock.hidden,true);
 console.log('PASS: admin PWA button, manual guidance, native installation, scope and hiding');
}
test().catch(e=>{console.error(e);process.exitCode=1});
