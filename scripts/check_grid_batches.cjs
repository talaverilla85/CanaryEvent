/* Test the actual batch writer with a simulated frame/task queue. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8');
const start=html.indexOf('let lastGridMarkup=null;');
const end=html.indexOf('function render(){',start);
assert.ok(start>0 && end>start,'Cannot locate live batched grid code');

const frames=[],tasks=[];
const grid={
  innerHTML:'',
  insertAdjacentHTML(position,value){
    assert.equal(position,'beforeend');
    this.innerHTML+=value;
  }
};
const context={
  $:id=>{assert.equal(id,'eventsGrid');return grid;},
  requestAnimationFrame:callback=>{frames.push(callback);return frames.length;},
  setTimeout:callback=>{tasks.push(callback);return tasks.length;}
};
vm.createContext(context);
vm.runInContext(html.slice(start,end),context);
const write=rows=>vm.runInContext('commitGridRows(rows)',Object.assign(context,{rows}));
const flush=()=>{
 for(let i=0;i<100&&(frames.length||tasks.length);i++){
  for(const callback of frames.splice(0))callback();
  for(const callback of tasks.splice(0))callback();
 }
 assert.equal(frames.length+tasks.length,0,'Pending tasks did not finish');
};
const rows=Array.from({length:25},(_,i)=>'<article>'+i+'</article>');
write(rows);
assert.equal(grid.innerHTML,rows.slice(0,8).join(''),'First batch should be small');
assert.ok(frames.length,'Subsequent rows must yield to the browser');
flush();
assert.equal(grid.innerHTML,rows.join(''),'All cards must preserve order');
write(rows);
assert.equal(grid.innerHTML,rows.join(''),'Same state must not rebuild the list');
assert.equal(frames.length+tasks.length,0,'Unchanged markup needs no extra tasks');

const previous=Array.from({length:24},(_,i)=>'<p>old'+i+'</p>');
const latest=Array.from({length:17},(_,i)=>'<p>new'+i+'</p>');
write(previous);
write(latest);
flush();
assert.equal(grid.innerHTML,latest.join(''),'Stale tasks must not append after new filters');
write([]);
flush();
assert.equal(grid.innerHTML,'','Empty state should clear cards');
console.log('Batched event grid OK (ordering, yield, cancellation, idempotence)');
