/* Validate script syntax without executing browser code or network requests. */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'public/index.html'),'utf8');
const inline=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(x=>x[1]).filter(x=>x.trim());
if(!inline.length)throw new Error('No inline scripts to validate');
for(const [i,code] of inline.entries())new vm.Script(code,{filename:'index.html:inline-'+i});
for(const file of ['filter_ui.js','reminders.js','temporal.js','install_prompt.js','posters/manifest.js','posters/remote-manifest.js']){
 new vm.Script(fs.readFileSync(path.join(root,'public',file),'utf8'),{filename:file});
}
console.log('Frontend syntax OK: '+inline.length+' inline blocks, 6 external scripts');
