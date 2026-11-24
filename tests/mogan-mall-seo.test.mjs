import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import { officialPosterUrl, pageForKey, renderLanding } from '../lib/seo-pages.js';
import {renderEventPage} from '../lib/event-seo.js';
import {renderMallPage, mallPageForSlug, renderMallSitemap} from '../lib/mall-seo.js';

const pdf='https://drive.google.com/file/d/1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v/view';
const image='https://drive.google.com/thumbnail?id=1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v&sz=w640';
const source='Centro Comercial Mogán Mall · Agenda de Navidad 2026';
const details='Actividad familiar anunciada en el programa oficial de Navidad de Mogan Mall en Puerto Rico de Gran Canaria. Fecha, hora y recinto verificados en el cartel oficial publicado por el centro. Consulta condiciones y cambios de horario en el documento original.';
const e=(id,title,start)=>({
  id,title:title+' · Navidad en Mogán Mall',start,
  municipality:'Mogán',venue:'Centro Comercial Mogán Mall',
  source_name:source,source_url:pdf,image_origin:pdf,
  image_url:image,image_status:'official_remote',
  image_alt:'Imagen oficial de la agenda navideña 2026 de Mogán Mall',
  details,category:'familia',accuracy:'municipality',free:null
});
const entries=[
  e(2010,'Jurassic Garden','2026-11-28T18:00:00'),
  e(2011,'Castillo hinchable con Don Sonrisas','2026-11-27T16:30:00'),
  e(2012,'Concierto The Royal Voice','2026-12-19T19:00:00'),
  e(2013,'Visita de Papá Noel','2026-12-23T17:30:00'),
];

test('Mogán Mall official PDF cover is strictly source-bound; no arbitrary Drive images',()=>{
  assert.equal(officialPosterUrl(entries[0]),image);
  assert.equal(officialPosterUrl({...entries[0],image_origin:'https://evil.example'}),'');
  assert.equal(officialPosterUrl({...entries[0],image_url:'https://drive.google.com/thumbnail?id=evil&sz=w640'}),'');
  assert.equal(officialPosterUrl({...entries[0],source_name:'Organizador falso'}),'');
  assert.equal(officialPosterUrl({...entries[0],image_status:'other'}),'');
});

test('Mogán Mall Christmas collection automatically qualifies and contains sources, images and structured list',()=>{
  const page=mallPageForSlug(entries,'mogan-mall','2026-11-24');
  assert.equal(page?.path,'/centros-comerciales/mogan-mall');
  assert.match(page?.heading||'',/Navidad en Centro Comercial Mogán Mall 2026–2027/);
  const result=renderMallPage('mogan-mall',entries,{today:'2026-11-24'});
  assert.equal(result.indexable,true);
  assert.equal(result.total,4);
  assert.match(result.html,/<h1>Navidad en Centro Comercial Mogán Mall 2026–2027<\/h1>/);
  assert.match(result.html,/src="https:\/\/drive.google.com\/thumbnail\?id=1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v&amp;sz=w640"/);
  assert.match(result.html,/Imagen oficial de la agenda navideña 2026 de Mogán Mall/);
  assert.match(result.html,/Fuente del evento/);
  assert.match(result.html,/"@type":"ItemList"/);
  assert.match(result.html,/https:\/\/drive.google.com\/file\/d\/1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v\/view/);
  assert.match(renderMallSitemap(entries,'2026-11-24'),/centros-comerciales\/mogan-mall/);
  assert.doesNotMatch(renderMallSitemap(entries,'2027-03-01'),/centros-comerciales\/mogan-mall/);
  assert.doesNotMatch(result.html,/drive\.google\.com\/file\/d\/.*?\/edit/);
});

test('individual event remains readable, credits the source and uses the official poster',()=>{
  const page=renderEventPage(entries[0],{today:'2026-11-24'});
  assert.match(page.html,/img src="https:\/\/drive.google.com\/thumbnail\?id=/);
  assert.match(page.html,/Consultar la fuente/);
  assert.match(page.html,/https:\/\/drive.google.com\/file\/d\/1VxOoS5Y20SZCoFPqLlxEgPCHIkk9YT3v\/view/);
});

test('front-end PWA recognizes exactly the Mogán Mall official PDF source and displays its poster',()=>{
  const html=readFileSync(new URL('../public/index.html',import.meta.url),'utf8');
  assert.match(html,/moganAllowed/);
  assert.match(html,/url\.href===moganImage/);
  assert.match(html,/e\.image_origin===moganPdf/);
  assert.match(html,/e\.source_name==='Centro Comercial Mogán Mall · Agenda de Navidad 2026'/);
});
