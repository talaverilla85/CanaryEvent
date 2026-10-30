import { db } from '../lib/admin-auth.js';
export default async function handler(req,res) {
  res.setHeader('X-Content-Type-Options','nosniff');
  if(req.method!=='GET'){res.status(405).end();return;}
  const sql=db();
  if(!sql){res.status(503).json({error:'Base de datos no configurada'});return;}
  try {
    const rows=await sql`SELECT p.payload,o.hidden,o.title_override,o.details_override,
      o.venue_override,o.price_override,o.free_override,o.category_override,o.canonical_event_id
      FROM published_events p LEFT JOIN event_overrides o ON o.event_id=p.id
      WHERE p.active AND COALESCE(o.hidden,FALSE)=FALSE AND o.canonical_event_id IS NULL
      ORDER BY p.payload->>'start',p.id LIMIT 3500`;
    const events=rows.map(({payload,...o})=>{
      const e={...payload};
      for(const [source,dest] of [['title_override','title'],['details_override','details'],
        ['venue_override','venue'],['price_override','price'],['category_override','category']])
        if(o[source]!==null&&o[source]!==undefined)e[dest]=o[source];
      if(o.free_override!==null&&o.free_override!==undefined)e.free=Number(o.free_override);
      return e;
    });
    res.setHeader('Cache-Control','public, s-maxage=45, stale-while-revalidate=120');
    return res.status(200).json({events,generated_at:new Date().toISOString(),timezone:'Atlantic/Canary',origin:'postgresql'});
  }catch(e){
    console.error('DParranda public catalog query failed:',e?.name||'Error');
    res.setHeader('Cache-Control','no-store');
    return res.status(503).json({error:'Catálogo PostgreSQL temporalmente no disponible'});
  }
}
