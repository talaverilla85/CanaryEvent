// Aggregate AriMar banner clicks without cookies, identifiers, or tracking pixels.
// Visitors follow the normal external link; this endpoint only records a click.
import {db,sameOrigin} from '../lib/admin-auth.js';

export default async function handler(req,res){
 res.setHeader('Cache-Control','private, no-store');
 res.setHeader('X-Robots-Tag','noindex, noarchive');
 res.setHeader('X-Content-Type-Options','nosniff');
 if(req.method!=='POST')return res.status(405).end();
 if(!sameOrigin(req))return res.status(403).end();
 if(req.body?.id!=='arimar-fundador')return res.status(400).end();
 const sql=db();
 if(!sql)return res.status(503).end();
 try{
  // Only count an enabled, in-date AriMar campaign. One atomic counter per Canary day.
  await sql`INSERT INTO ad_daily_stats(campaign_id,day,clicks)
   SELECT id,(now() AT TIME ZONE 'Atlantic/Canary')::date,1
   FROM ad_campaigns
   WHERE id='arimar-fundador' AND enabled=TRUE
    AND (starts_at IS NULL OR starts_at<=(now() AT TIME ZONE 'Atlantic/Canary')::date)
    AND (ends_at IS NULL OR ends_at>=(now() AT TIME ZONE 'Atlantic/Canary')::date)
   ON CONFLICT(campaign_id,day) DO UPDATE SET clicks=ad_daily_stats.clicks+1`;
  return res.status(204).end();
 }catch(e){
  console.error('DParranda AriMar click counter failed:',e?.name||'Error');
  return res.status(503).end();
 }
}
