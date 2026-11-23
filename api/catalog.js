import { db } from '../lib/admin-auth.js';
import { pageForKey, renderLanding, renderIntentSitemap } from '../lib/seo-pages.js';
import { parseEventId, eventPageRemoved, renderEventPage, renderEventSitemap } from '../lib/event-seo.js';
export default async function handler(req,res) {
  const pageKey = typeof req.query?.page === 'string' ? req.query.page : '';
  const seoPage = pageForKey(pageKey);
  const eventIdRaw = typeof req.query?.eventId === 'string' ? req.query.eventId : '';
  const eventId = eventIdRaw ? parseEventId(eventIdRaw) : null;
  const eventSitemap = req.query?.eventSitemap === '1';
  const intentSitemap = req.query?.intentSitemap === '1';
  const eventRoute = Boolean(eventIdRaw);
  const seoRoute = Boolean(seoPage || eventRoute || eventSitemap || intentSitemap);
  res.setHeader('X-Content-Type-Options','nosniff');
  if((pageKey && !seoPage)||(eventRoute && eventId===null)){
    res.setHeader('X-Robots-Tag','noindex');res.status(404).end('Página no encontrada');return;
  }
  if(req.method!=='GET' && !(seoRoute && req.method==='HEAD')){
    res.status(405).end();return;
  }
  const sql=db();
  if(!sql){
    if(seoRoute){res.setHeader('X-Robots-Tag','noindex');res.setHeader('Cache-Control','no-store');res.status(503).end('Agenda temporalmente no disponible');return;}
    res.status(503).json({error:'Base de datos no configurada'});return;
  }
  try {
    // Stable URLs for current events; expired or withdrawn events return 410 Gone.
    // The rows remain in PostgreSQL for history/dedup; public requests stay read-only.
    if(eventRoute){
      const [record]=await sql`SELECT p.id,p.payload,p.active,
        o.hidden,o.canonical_event_id,o.title_override,o.details_override,
        o.venue_override,o.price_override,o.free_override,o.category_override
        FROM published_events p LEFT JOIN event_overrides o ON o.event_id=p.id
        WHERE p.id=${eventId} LIMIT 1`;
      if(!record||record.hidden){
        res.setHeader('X-Robots-Tag','noindex');
        return res.status(404).end('Evento no disponible');
      }
      if(record.canonical_event_id !== null && record.canonical_event_id !== undefined &&
        Number(record.canonical_event_id)!==eventId){
        res.setHeader('Location','/evento/'+encodeURIComponent(String(record.canonical_event_id)));
        res.setHeader('Cache-Control','public, s-maxage=3600');
        return res.status(308).end();
      }
      const event={...record.payload,id:Number(record.id)};
      if(eventPageRemoved(event,record.active)){
        res.setHeader('X-Robots-Tag','noindex');
        res.setHeader('Cache-Control','no-store');
        res.setHeader('Content-Type','text/html; charset=utf-8');
        const gone='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="robots" content="noindex"><title>Evento finalizado | D’Parranda</title></head><body><main><h1>Este evento ya no está disponible</h1><p>Descubre los planes actuales en D’Parranda.</p><a href="/que-hacer-en-gran-canaria">Ver planes próximos</a></main></body></html>';
        return res.status(410).end(req.method==='HEAD'?'':gone);
      }
      for(const [override,field] of [
        ['title_override','title'],['details_override','details'],['venue_override','venue'],
        ['price_override','price'],['category_override','category']
      ]) if(record[override]!==null&&record[override]!==undefined)event[field]=record[override];
      if(record.free_override!==null&&record.free_override!==undefined)event.free=Number(record.free_override);
      const result=renderEventPage(event,{active:record.active});
      res.setHeader('Content-Type','text/html; charset=utf-8');
      res.setHeader('Cache-Control','public, s-maxage=120, stale-while-revalidate=300');
      if(!result.indexable)res.setHeader('X-Robots-Tag','noindex, follow');
      return res.status(200).end(req.method==='HEAD'?'':result.html);
    }
    if(eventSitemap){
      const rows=await sql`SELECT p.id,p.payload,o.title_override,o.details_override,o.venue_override
        FROM published_events p LEFT JOIN event_overrides o ON o.event_id=p.id
        WHERE p.active AND COALESCE(o.hidden,FALSE)=FALSE AND o.canonical_event_id IS NULL
        ORDER BY p.id LIMIT 3500`;
      const events=rows.map(row=>({
        ...row.payload,id:Number(row.id),
        title:row.title_override??row.payload.title,
        details:row.details_override??row.payload.details,
        venue:row.venue_override??row.payload.venue
      }));
      const xml=renderEventSitemap(events);
      res.setHeader('Content-Type','application/xml; charset=utf-8');
      res.setHeader('Cache-Control','public, s-maxage=300, stale-while-revalidate=600');
      return res.status(200).end(req.method==='HEAD'?'':xml);
    }
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
    if(intentSitemap){
      const xml=renderIntentSitemap(events);
      res.setHeader('Content-Type','application/xml; charset=utf-8');
      res.setHeader('Cache-Control','public, s-maxage=300, stale-while-revalidate=600');
      return res.status(200).end(req.method==='HEAD'?'':xml);
    }
    if(seoPage){
      // The Christmas landing may carry the same active, explicitly
      // labelled AriMar banner as the home feed, not a promoted event.
      // Never show a disabled/expired campaign; keep SEO page read-only.
      let christmasAd=null;
      if(seoPage.kind==='christmas'){
        const [candidate]=await sql`SELECT id,enabled,advertiser,headline,description,
          location,button_text,button_url,image,image_alt
          FROM ad_campaigns WHERE id='arimar-fundador' AND enabled=TRUE
          AND (starts_at IS NULL OR starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date))
          AND (ends_at IS NULL OR ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date))
          LIMIT 1`;
        christmasAd=candidate||null;
      }
      const rendered=renderLanding(seoPage,events,{sponsor:christmasAd});
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
    if(seoRoute){res.setHeader('X-Robots-Tag','noindex');return res.status(503).end('Agenda temporalmente no disponible');}
    return res.status(503).json({error:'Catálogo PostgreSQL temporalmente no disponible'});
  }
}
