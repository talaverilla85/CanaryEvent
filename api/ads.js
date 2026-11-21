import { db,sameOrigin } from '../lib/admin-auth.js';
// Only AriMar clicks are counted during the organic launch, without personal identifiers.
async function recordArimarClick(req,res){
 res.setHeader('Cache-Control','private, no-store');
 res.setHeader('X-Robots-Tag','noindex, noarchive');
 if(!sameOrigin(req))return res.status(403).end();
 if(req.body?.id!=='arimar-fundador')return res.status(400).end();
 const sql=db();
 if(!sql)return res.status(503).end();
 try{
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
export default async function handler(req,res) {
  res.setHeader('X-Content-Type-Options','nosniff');
  if(req.method==='POST'&&req.query?.op==='click')return recordArimarClick(req,res);
  if(req.method!=='GET'){res.status(405).end();return;}
  const sql=db();
  if(!sql){res.status(503).json({error:'Base de datos no configurada'});return;}
  try {
    const ads=await sql`SELECT id,enabled,advertiser,kind,permanent,
     to_char(starts_at,'YYYY-MM-DD') AS starts_at,
     to_char(ends_at,'YYYY-MM-DD') AS ends_at,
     municipalities,headline,description,location,button_text,button_url,image,image_alt,disclosure,enquiry_id,
     EXISTS(SELECT 1 FROM ad_campaign_images ai WHERE ai.ad_id=ad_campaigns.id) AS has_uploaded_image
     FROM ad_campaigns WHERE enabled=TRUE AND NOT EXISTS(SELECT 1 FROM advertiser_campaign_drafts test_draft WHERE test_draft.published_ad_id=ad_campaigns.id AND test_draft.stripe_checkout_session_id LIKE 'cs_test_%') AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.record_id=ad_campaigns.id AND ar.source IN ('house','published'))
       AND (starts_at IS NULL OR starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date))
       AND (ends_at IS NULL OR ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date))
     ORDER BY updated_at DESC,id LIMIT 100`;
    for(const ad of ads){
      if(ad.id.startsWith('dp-ad-'))ad.image='/api/paid-banner-image?id='+encodeURIComponent(ad.id);
      else if(ad.has_uploaded_image)ad.image='/api/ad-image?id='+encodeURIComponent(ad.id);
      else if(ad.enquiry_id)ad.image='/api/media?id='+ad.enquiry_id;
      delete ad.has_uploaded_image;
    }
    res.setHeader('Cache-Control','public, s-maxage=45, stale-while-revalidate=120');
    return res.status(200).json({schema_version:1,placement:{name:'explore_feed',after_mobile:5,after_tablet:5,after_desktop:5},ads});
  }catch(e){
    console.error('DParranda public ads query failed:',e?.name||'Error');
    res.setHeader('Cache-Control','no-store');
    return res.status(503).json({error:'Publicidad temporalmente no disponible'});
  }
}
