import { db } from '../lib/admin-auth.js';
export default async function handler(req,res) {
  res.setHeader('X-Content-Type-Options','nosniff');
  if(req.method!=='GET'){res.status(405).end();return;}
  const sql=db();
  if(!sql){res.status(503).json({error:'Base de datos no configurada'});return;}
  try {
    const ads=await sql`SELECT id,enabled,advertiser,kind,permanent,
     to_char(starts_at,'YYYY-MM-DD') AS starts_at,
     to_char(ends_at,'YYYY-MM-DD') AS ends_at,
     municipalities,headline,description,location,button_text,button_url,image,image_alt,disclosure,enquiry_id,
     EXISTS(SELECT 1 FROM ad_campaign_images ai WHERE ai.ad_id=ad_campaigns.id) AS has_uploaded_image
     FROM ad_campaigns WHERE enabled=TRUE
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
