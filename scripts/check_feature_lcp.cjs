/* Lighthouse LCP regression: the already-painted feature motif must survive
   catalog refreshes; only photos should be replaced. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const html=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8');
const start=html.indexOf('function clearFeaturedPhotos(media){');
const end=html.indexOf('\nfunction renderEditorial(',start);
assert.ok(start>0&&end>start,'Feature media helper not found');
assert.match(html,/<div class="dp-feature-media" id="dpFeatureMedia"><span class="dp-feature-fallback"/,
 'Feature motif should be available before JavaScript and catalog fetch');

const motif={className:'dp-feature-fallback'};
const photo={tagName:'IMG',removed:false,remove(){this.removed=true}};
const items=[motif,photo];
const media={
 prepends:0,
 querySelector(selector){
  assert.equal(selector,'.dp-feature-fallback');
  return items.find(x=>x.className==='dp-feature-fallback')||null;
 },
 querySelectorAll(selector){
  assert.equal(selector,'img');
  return items.filter(x=>x.tagName==='IMG'&&!x.removed);
 },
 prepend(element){this.prepends++;items.unshift(element)}
};
let created=0;
const context={document:{createElement(tag){
 assert.equal(tag,'span');
 created++;
 return {className:'',textContent:'',setAttribute(k,v){this[k]=v}};
}}};
vm.createContext(context);
vm.runInContext(html.slice(start,end),context);
const clear=()=>vm.runInContext('clearFeaturedPhotos(media)',Object.assign(context,{media}));

clear();
assert.equal(items[0],motif,'Existing motif must keep identity');
assert.equal(created,0,'No duplicate or late motif is created');
assert.equal(media.prepends,0,'No mutation to initial motif');
assert.ok(photo.removed,'Only obsolete poster should be removed');
clear();
assert.equal(created,0,'Repeated rendering should not recreate motif');

const missing={
 prepends:0,items:[],
 querySelector(){return this.items[0]||null},
 querySelectorAll(){return []},
 prepend(node){this.items.unshift(node);this.prepends++}
};
vm.runInContext('clearFeaturedPhotos(missing)',Object.assign(context,{missing}));
assert.equal(missing.prepends,1,'Fallback should be restored only when absent');
assert.equal(missing.items[0].textContent,'✳');
console.log('Featured LCP motif stable across catalog refresh and filters');
