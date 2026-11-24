// Read-only, fixed-source image relay for the Mesa y López official programme.
// Their image server advertises Cross-Origin-Resource-Policy: same-site, which
// prevents the browser embedding images directly on dparranda.es.
// Source images are looked up from published_events, never arbitrary user URLs.
// Images are delivered in memory; nothing is uploaded or archived to Drive.
import { db } from '../lib/admin-auth.js';
import { ECI_PROGRAMMES, eciOfficialImageUrl } from '../lib/official-poster.js';

const MAX_BYTES=2_500_000;
const ALLOWED_MIME=new Set(['image/jpeg','image/png','image/webp']);

export async function relayOfficialPoster(req,res,{database=db,fetchRemote=fetch}={}) {
  res.setHeader('X-Content-Type-Options','nosniff');
  res.setHeader('Cross-Origin-Resource-Policy','same-origin');
  if(req.method!=='GET') return res.status(405).end();
  const kind=typeof req.query?.kind==='string' ? req.query.kind : '';
  if(!Object.hasOwn(ECI_PROGRAMMES,kind)) return res.status(404).end();
  const sql=database();
  if(!sql) return res.status(503).end();
  const rule=ECI_PROGRAMMES[kind];
  try {
    const rows=await sql`SELECT p.payload
      FROM published_events p
      LEFT JOIN event_overrides o ON o.event_id=p.id
      WHERE p.active=TRUE AND COALESCE(o.hidden,FALSE)=FALSE
        AND o.canonical_event_id IS NULL
        AND p.payload->>'source_name'=${rule.source_name}
        AND p.payload->>'image_status'='official_remote'
      ORDER BY p.id LIMIT 10`;
    const source=rows.map(row=>eciOfficialImageUrl(row.payload,kind)).find(Boolean);
    if(!source) return res.status(404).end();
    const controller=new AbortController();
    const timeout=setTimeout(()=>controller.abort(),10000);
    try {
      const remote=await fetchRemote(source,{
        redirect:'manual',signal:controller.signal,
        headers:{Accept:'image/jpeg,image/png,image/webp'}
      });
      if(remote.status!==200) return res.status(502).end();
      const mime=(remote.headers.get('content-type')||'').split(';')[0].trim().toLowerCase();
      const stated=Number(remote.headers.get('content-length')||0);
      if(!ALLOWED_MIME.has(mime)||!Number.isFinite(stated)||
          stated>MAX_BYTES || stated<0) return res.status(502).end();
      if(!remote.body) return res.status(502).end();
      const reader=remote.body.getReader();
      const chunks=[];
      let size=0;
      try {
        for(;;){
          const {done,value}=await reader.read();
          if(done)break;
          size+=value.byteLength;
          if(size>MAX_BYTES) { await reader.cancel(); return res.status(502).end(); }
          chunks.push(Buffer.from(value));
        }
      }finally{reader.releaseLock();}
      if(size<50) return res.status(502).end();
      res.setHeader('Content-Type',mime);
      res.setHeader('Content-Length',String(size));
      res.setHeader('Cache-Control','public, max-age=600, s-maxage=3600, stale-while-revalidate=7200');
      return res.status(200).end(Buffer.concat(chunks,size));
    } finally {clearTimeout(timeout);}
  }catch(err){
    console.error('DParranda official programme image relay failed:',err?.name||'Error');
    return res.status(502).end();
  }
}
export default async function handler(req,res){
  return relayOfficialPoster(req,res);
}
