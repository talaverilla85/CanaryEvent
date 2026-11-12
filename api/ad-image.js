// Public images for admin-managed promotional campaigns.
// Never expose a stored creative unless its campaign is currently visible.
import {db} from '../lib/admin-auth.js';

export default async function handler(req,res){
 res.setHeader('X-Content-Type-Options','nosniff');
 if(req.method!=='GET')return res.status(405).end();
 const id=String(req.query?.id||'');
 if(!/^[a-zA-Z0-9_-]{2,90}$/.test(id))return res.status(404).end();
 const sql=db();if(!sql)return res.status(503).end();
 try{
  const [item]=await sql`SELECT img.mime_type,img.image_data
   FROM ad_campaign_images img JOIN ad_campaigns ad ON ad.id=img.ad_id
   WHERE img.ad_id=${id} AND ad.enabled=TRUE
    AND (ad.starts_at IS NULL OR ad.starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date))
    AND (ad.ends_at IS NULL OR ad.ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date))
    AND (ad.kind='house' OR EXISTS (
      SELECT 1 FROM advertiser_campaign_drafts d
      WHERE d.published_ad_id=ad.id AND d.status='active' AND d.payment_status='paid'
    ))`;
  if(!item)return res.status(404).end();
  const bytes=typeof item.image_data==='string'?
   Buffer.from(item.image_data.replace(/^\\x/,''),'hex'):Buffer.from(item.image_data);
  res.setHeader('Content-Type',item.mime_type);
  res.setHeader('Cache-Control','public,max-age=120,s-maxage=120');
  return res.status(200).end(bytes);
 }catch(err){
  console.error('DParranda ad image failed',err?.name||'Error');
  return res.status(503).end();
 }
}
