import { db } from '../lib/admin-auth.js';
import { pageForKey, renderLanding } from '../lib/seo-pages.js';
export default async function handler(req,res) {
  const pageKey = typeof req.query?.page === 'string' ? req.query.page : '';
  const seoPage = pageForKey(pageKey);
  res.setHeader('X-Content-Type-Options','nosniff');
  if(pageKey && !seoPage){res.setHeader('X-Robots-Tag','noindex');res.status(404).end('Página no encontrada');return;}
  if(req.method!=='GET' && !(seoPage && req.method==='HEAD')){res.status(405).end();return;}
  const sql=db();
  if(!sql){
    if(seoPage){res.setHeader('X-Robots-Tag','noindex');res.setHeader('Cache-Control','no-store');res.status(503).end('Agenda temporalmente no disponible');return;}
    res.status(503).json({error:'Base de datos no configurada'});return;
  }
  try {
    // Independent public queries run concurrently to reduce cold-start latency.
    const [rows,sponsored]=await Promise.all([
      sql`SELECT p.payload,o.hidden,o.title_override,o.details_override,
      o.venue_override,o.price_override,o.free_override,o.category_override,o.canonical_event_id
      FROM published_events p LEFT JOIN event_overrides o ON o.event_id=p.id
      WHERE p.active AND COALESCE(o.hidden,FALSE)=FALSE AND o.canonical_event_id IS NULL
      ORDER BY p.payload->>'start',p.id LIMIT 3500`,
      sql`SELECT id,title,start,"end",municipality,venue,category,details,price,free,
      source_url,image_url,image_alt,enquiry_id,advertiser,advertiser_draft_id
      FROM sponsored_events WHERE enabled=TRUE AND review_status='approved' AND NOT EXISTS(SELECT 1 FROM advertiser_campaign_drafts test_draft WHERE test_draft.published_event_id=sponsored_events.id AND test_draft.stripe_checkout_session_id LIKE 'cs_test_%') AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=sponsored_events.advertiser_draft_id::text)
        AND left(COALESCE(NULLIF("end",''),start),10)>=to_char((now() AT TIME ZONE 'Atlantic/Canary')::date,'YYYY-MM-DD')
        AND (campaign_starts_at IS NULL OR campaign_starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date))
        AND (campaign_ends_at IS NULL OR campaign_ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date))
      ORDER BY start,id LIMIT 250`
    ]);
    const events=rows.map(({payload,...o})=>{
      const e={...payload};
      for(const [source,dest] of [['title_override','title'],['details_override','details'],
        ['venue_override','venue'],['price_override','price'],['category_override','category']])
        if(o[source]!==null&&o[source]!==undefined)e[dest]=o[source];
      if(o.free_override!==null&&o.free_override!==undefined)e.free=Number(o.free_override);
      return e;
    });
    if(seoPage){
      const rendered=renderLanding(seoPage,events);
      res.setHeader('Content-Type','text/html; charset=utf-8');
      res.setHeader('Cache-Control','public, s-maxage=300, stale-while-revalidate=600');
      if(!rendered.indexable)res.setHeader('X-Robots-Tag','noindex, follow');
      return res.status(200).end(req.method==='HEAD'?'':rendered.html);
    }
    for(const item of sponsored){
      events.push({
        id:-9000000000-Number(item.id),title:item.title,start:item.start,end:item.end,
        municipality:item.municipality,venue:item.venue,category:item.category,
        details:item.details,price:item.price,free:item.free,lat:null,lng:null,
        accuracy:'municipality',source_name:'Publicidad · '+item.advertiser,
        source_url:item.source_url,image_url:item.advertiser_draft_id?'/api/paid-event-image?id='+item.id: item.enquiry_id?'/api/media?id='+item.enquiry_id:item.image_url,
        image_alt:item.image_alt,image_status:'promotional',paid_promotion:true
      });
    }
    events.sort((a,b)=>String(a.start).localeCompare(String(b.start)));

    res.setHeader('Cache-Control','public, s-maxage=45, stale-while-revalidate=120');
    return res.status(200).json({events,generated_at:new Date().toISOString(),timezone:'Atlantic/Canary',origin:'postgresql'});
  }catch(e){
    console.error('DParranda public catalog query failed:',e?.name||'Error');
    res.setHeader('Cache-Control','no-store');
    if(seoPage){res.setHeader('X-Robots-Tag','noindex');return res.status(503).end('Agenda temporalmente no disponible');}
    return res.status(503).json({error:'Catálogo PostgreSQL temporalmente no disponible'});
  }
}
