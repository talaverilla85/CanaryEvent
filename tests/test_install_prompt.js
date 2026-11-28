/* Run with: node tests/test_install_prompt.js */
'use strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(import.meta.url);
const __dirname=fileURLToPath(new URL('.',import.meta.url));
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../public/install_prompt.js'),'utf8');

function setup({ios=false,mobile=true,standalone=false}={}){
 const state={ios,mobile,standalone,installed:false};
 const reports=[];
 const stored=new Map(),windowEvents={},docEvents={};
 let doc;
 const cls=(initial=[])=>{
   const data=new Set(initial);
   return {contains:x=>data.has(x),add:x=>data.add(x),remove:x=>data.delete(x),
     toggle:(x,force)=>{if(force===undefined)force=!data.has(x);if(force)data.add(x);else data.delete(x);return force}};
 };
 const makeElement=id=>{
   const handlers={};
   return {id,classList:cls(id.includes('Overlay')||id.includes('Dock')?['hidden']:[]),
     handlers,children:[],textContent:'',
     addEventListener:(name,fn)=>{(handlers[name]??=[]).push(fn)},
     focus(){doc.activeElement=this},
     replaceChildren(){this.children=[]},
     append(el){this.children.push(el)},
     click(){(handlers.click||[]).forEach(fn=>fn({target:this}))}};
 };
 const ids=['dpInstallDock','dpInstallAction','dpInstallDismiss',
   'dpInstallGuideOverlay','dpInstallGuideClose','dpInstallGuideDone',
   'dpInstallGuideDescription','dpInstallGuideSteps'];
 const el=Object.fromEntries(ids.map(id=>[id,makeElement(id)]));
 doc={activeElement:null,body:{classList:cls()},
   getElementById:id=>el[id]||null,createElement:tag=>makeElement(tag),
   addEventListener:(name,fn)=>{(docEvents[name]??=[]).push(fn)}};
 const mediaObj={addEventListener:()=>{}};
 const win={
   localStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v)},
   matchMedia:q=>{
     if(q==='(max-width: 720px)')return {matches:state.mobile};
     if(q==='(display-mode: standalone)')return Object.assign({matches:state.standalone},mediaObj);
     return {matches:false};
   },
   addEventListener:(name,fn)=>{(windowEvents[name]??=[]).push(fn)}
 };
 const navigator={sendBeacon:(url,payload)=>{reports.push({url,payload});return true},userAgent:ios?'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)':'Mozilla/5.0 (Linux; Android 15)',
   platform:ios?'iPhone':'Linux',maxTouchPoints:ios?5:1,standalone:false};
 const ctx={window:win,document:doc,navigator,localStorage:win.localStorage,Date,Promise,console,Blob,Intl};
 vm.runInNewContext(source,ctx,{filename:'install_prompt.js'});
 const emit=(name,e={})=>(windowEvents[name]||[]).forEach(fn=>fn(e));
 const shown=()=>!el.dpInstallDock.classList.contains('hidden');
 return {state,stored,el,emit,shown,doc,reports};
}
async function main(){
 let a=setup();
 assert.equal(a.shown(),true,'mobile CTA visible and initially fixed');
 a.el.dpInstallAction.click();
 assert.equal(a.el.dpInstallGuideOverlay.classList.contains('hidden'),false,'manual fallback opens');
 assert.equal(a.el.dpInstallGuideSteps.children.length,3);
 a.el.dpInstallGuideDone.click();
 assert.equal(a.el.dpInstallGuideOverlay.classList.contains('hidden'),true);
 assert.equal(a.shown(),true,'closing guide does not dismiss CTA');

 let i=setup({ios:true});
 i.el.dpInstallAction.click();
 assert.match(i.el.dpInstallGuideDescription.textContent,/Safari/);
 assert.match(i.el.dpInstallGuideSteps.children[1].textContent,/Compartir/);

 let desktop=setup({mobile:false});
 assert.equal(desktop.shown(),false);
 let installed=setup({standalone:true});
 assert.equal(installed.shown(),false);

 let dismissed=setup();
 dismissed.el.dpInstallDismiss.click();
 assert.equal(dismissed.shown(),false);
 assert.equal(dismissed.stored.size,0,'dismiss hides for the visit only without persisting a block');

 let native=setup();
 let calls=0,prevented=false;
 native.emit('beforeinstallprompt',{
   preventDefault(){prevented=true},
   prompt(){calls++;return Promise.resolve()},
   userChoice:Promise.resolve({outcome:'accepted'})
 });
 assert.equal(prevented,true,'keeps native prompt for click');
 native.el.dpInstallAction.click();
 await Promise.resolve();await Promise.resolve();await Promise.resolve();await Promise.resolve();
 assert.equal(calls,1,'native prompt called once during gesture');
 assert.equal(native.shown(),false,'accepted install removes CTA');
 assert.ok(Number(native.stored.get('dparranda_install_confirmed_v1'))>0,'confirmed install is remembered');

 let viaEvent=setup();
 viaEvent.emit('appinstalled');
 assert.equal(viaEvent.shown(),false,'appinstalled removes CTA');
 assert.equal(await i.reports[0].payload.text(),'{"event":"install_click"}','iOS manual guide click is counted');
 assert.equal(native.reports.length,2,'native tap and confirmed install reported once each');
 assert.equal(await native.reports[0].payload.text(),'{"event":"install_click"}');
 assert.equal(await native.reports[1].payload.text(),'{"event":"native_install"}');
 native.emit('appinstalled');
 assert.equal(native.reports.length,2,'native event plus accepted prompt does not double count');
 assert.equal(await viaEvent.reports[0].payload.text(),'{"event":"native_install"}');
 assert.equal(installed.reports.length,2,'first installed standalone open creates two signals');
 assert.equal(await installed.reports[0].payload.text(),'{"event":"standalone_first"}');
 assert.equal(await installed.reports[1].payload.text(),'{"event":"standalone_day"}');
 installed.emit('pageshow');
 assert.equal(installed.reports.length,2,'same-day standalone reload is deduplicated locally');
 console.log('PASS: installation CTA and anonymous growth signals');
}
main().catch(e=>{console.error(e);process.exitCode=1});
