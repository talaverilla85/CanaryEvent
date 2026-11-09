/* Execute exactly the browser poster URL selection function in isolation. */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../public/index.html'),'utf8');
const first=html.indexOf('function verifiedImage(e){');
const last=html.indexOf('\nfunction coverHtml(e,',first);
assert.ok(first>0&&last>first,'verifiedImage function not found');
const expected='https://www.eventosgrancanaria.com/controlpanel/files/gridfs/6a955c6a013a6268e0795f4b';
const local='/posters/6a955c6a013a6268e0795f4b.webp';
const map={};
map[expected]=local;
const ctx={URL,window:{DParrandaPosterThumbs:map},IMAGE_HOSTS:new Set([
 'www.eventosgrancanaria.com','ingenio.es'
])};
vm.createContext(ctx);
vm.runInContext(html.slice(first,last),ctx);
const verify=x=>vm.runInContext('verifiedImage(event)',Object.assign(ctx,{event:x}));
assert.equal(verify({
 image_url:expected,image_status:'official_remote',
}),local,'Official poster must load local WebP when present');
assert.equal(verify({
 image_url:expected,image_status:'official_remote',
 paid_promotion:true
}),local,'Promotional flag without a promo URL still validates the official URL');
assert.equal(verify({
 image_url:'/sponsors/approved.webp',paid_promotion:true
}),'/sponsors/approved.webp','Sponsor image must remain original');
assert.equal(verify({
 image_url:'/api/media?id=12',paid_promotion:true
}),'/api/media?id=12','Sponsor media must remain original');
assert.equal(verify({
 image_url:'https://example.evil.invalid/controlpanel/files/gridfs/x',
 image_status:'official_remote'
}),'','Unapproved image host cannot be loaded');
ctx.window.DParrandaPosterThumbs[expected]='https://evil.invalid/stolen.webp';
assert.equal(verify({image_url:expected,image_status:'official_remote'}),expected,
 'Invalid manifest path falls back to the verified original');
delete ctx.window.DParrandaPosterThumbs;
assert.equal(verify({image_url:expected,image_status:'official_remote'}),expected,
 'If the manifest script fails, the public catalog must still show official posters');
assert.ok(html.indexOf('/posters/manifest.js')<first,'Load manifest before choosing images');
assert.ok(html.includes('name="robots" content="noindex,nofollow"'));
console.log('Poster selection OK: static WebP, fallback official poster, unchanged sponsored media');
