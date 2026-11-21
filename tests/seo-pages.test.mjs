import test from 'node:test';
import assert from 'node:assert/strict';
import { SEO_PAGES, pageForKey, upcomingEvents, renderLanding, normalizePlace } from '../lib/seo-pages.js';

const sample = [
  {id: 11, title:'Teatro de invierno', start:'2026-11-24T19:00:00', municipality:'Agüimes', venue:'Teatro Cruce de Culturas', category:'cultura', source_url:'https://example.org/11'},
  {id: 12, title:'Concierto del viernes', start:'2026-11-27T20:00:00', municipality:'Agüimes', venue:'Sala local', category:'musica', image_status:'verified'},
  {id: 13, title:'Feria de artesanía', start:'2026-11-30', municipality:'Agüimes', venue:'Plaza principal', category:'ocio'},
  {id: 14, title:'Evento de Telde', start:'2026-11-29', municipality:'Telde', venue:'Teatro', category:'cultura'},
  {id: 15, title:'Pasado', start:'2026-11-01', end:'2026-11-02', municipality:'Agüimes', venue:'Teatro', category:'cultura'},
  {id: 16, title:'Oculto en otro lugar', start:'2026-11-30', municipality:'Ingenio', venue:'Teatro', category:'cultura'}
];

test('pilot routes have unique, readable paths', () => {
  assert.equal(SEO_PAGES.length, 5);
  assert.equal(new Set(SEO_PAGES.map(p => p.path)).size, 5);
  assert.equal(pageForKey('unknown'), null);
  assert.equal(normalizePlace('Agüimes'), 'aguimes');
});

test('municipal pages only include upcoming events from that municipality', () => {
  const page = pageForKey('aguimes');
  const selected = upcomingEvents(sample, page, '2026-11-21');
  assert.deepEqual(selected.map(e => e.id), [11,12,13]);
});

test('island page aggregates upcoming events across municipalities', () => {
  const page = pageForKey('gran-canaria');
  const selected = upcomingEvents(sample, page, '2026-11-21');
  assert.equal(selected.length, 5);
});

test('HTML renders server-side cards, canonical, and structured collection metadata', () => {
  const p = pageForKey('aguimes');
  const result = renderLanding(p, sample, {today:'2026-11-21'});
  assert.equal(result.indexable, true);
  assert.equal(result.total, 3);
  assert.match(result.html, /<title>Qué hacer en Agüimes y Arinaga/);
  assert.match(result.html, /<meta name="robots" content="index,follow/);
  assert.match(result.html, /https:\/\/dparranda\.es\/que-hacer-en-aguimes/);
  assert.match(result.html, /Teatro de invierno/);
  assert.match(result.html, /\/\?evento=11/);
  assert.match(result.html, /"@type":"CollectionPage"/);
});

test('low-content pages stay noindex, with accurate navigation', () => {
  const result = renderLanding(pageForKey('telde'), sample, {today:'2026-11-21'});
  assert.equal(result.total, 1);
  assert.equal(result.indexable, false);
  assert.match(result.html, /<meta name="robots" content="noindex,follow"/);
  assert.match(result.html, /Próximamente más planes/);
});

test('unsafe titles and URLs cannot inject markup or script navigation', () => {
  const malicious = [
    {id: 50, title:'<img src=x onerror=alert(1)>', municipality:'Ingenio', start:'2026-12-01', source_url:'javascript:alert(1)'},
    {id: 51, title:'Evento real', municipality:'Ingenio', start:'2026-12-02'},
    {id: 52, title:'Evento real 2', municipality:'Ingenio', start:'2026-12-03'}
  ];
  const html = renderLanding(pageForKey('ingenio'), malicious, {today:'2026-11-21'}).html;
  assert.doesNotMatch(html, /<img src=x onerror/);
  assert.match(html, /&lt;img src=x/);
  assert.doesNotMatch(html, /href="javascript:/);
});
