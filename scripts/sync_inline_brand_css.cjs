/* Keep both published DParranda design layers inline and byte-for-byte
   synchronized with their editable source CSS.
   Inline CSS removes two render-blocking requests without visual changes. */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const htmlPath=path.join(root,'public/index.html');
const theme=fs.readFileSync(path.join(root,'public/brand/dparranda-theme.css'),'utf8');
const editorial=fs.readFileSync(path.join(root,'public/brand/dparranda-editorial.css'),'utf8');
const start='<!-- DPARRANDA_INLINE_BRAND_START -->';
const end='<!-- DPARRANDA_INLINE_BRAND_END -->';
const cssBlock=start+'\n<style id="dparranda-brand-styles">\n'+theme+'\n'+editorial+'\n</style>\n'+end;
const html=fs.readFileSync(htmlPath,'utf8');
const legacy=/<link rel="stylesheet" href="\/brand\/dparranda-theme\.css\?v=\d+">\s*<link rel="stylesheet" href="\/brand\/dparranda-editorial\.css\?v=\d+">/;
let expected;
if(html.includes(start)){
 const i=html.indexOf(start),j=html.indexOf(end,i);
 if(j<0)throw Error('Inline brand styles are missing their end marker');
 expected=html.slice(0,i)+cssBlock+html.slice(j+end.length);
}else{
 if(!legacy.test(html))throw Error('Expected two CSS link tags');
 expected=html.replace(legacy,cssBlock);
}
if(process.argv.includes('--check')){
 if(html!==expected)throw Error('Inline CSS is stale: run node scripts/sync_inline_brand_css.cjs');
 if(/<link rel="stylesheet" href="\/brand\/dparranda-(?:theme|editorial)\.css/.test(html))
   throw Error('Render-blocking brand CSS request remains');
 console.log('DParranda inline brand CSS matches source files');
}else{
 if(html!==expected)fs.writeFileSync(htmlPath,expected,'utf8');
 console.log('DParranda brand CSS embedded without render-blocking requests');
}
