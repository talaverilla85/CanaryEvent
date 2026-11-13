// Public creative served only while its banner is actually visible.
import {db} from '../lib/admin-auth.js';
export default async function handler(req,res){
 res.setHeader('X-Content-Type-Options','nosniff');
 if(req.method!=='GET')return res.status(405).end();
 const id=String(req.query?.id||'');
 if(!/^dp-ad-[1-9]\d{0,12}$/.test(id))return res.status(404).end();
 const sql=db();if(!sql)return res.status(503).end();
 try{
  const [img]=await sql`SELECT i.mime_type,i.image_data
   FROM ad_campaigns a
   JOIN advertiser_campaign_drafts d ON d.published_ad_id=a.id
   JOIN advertiser_campaign_draft_images i ON i.draft_id=d.id
   WHERE a.id=${id} AND a.enabled=TRUE AND d.status='active' AND d.payment_status='paid' AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=d.id::text)
    AND a.starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date)
    AND a.ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)`;
  if(!img)return res.status(404).end();
  const bytes=typeof img.image_data==='string'?Buffer.from(img.image_data.replace(/^\\x/,''),'hex'):Buffer.from(img.image_data);
  res.setHeader('Content-Type',img.mime_type);res.setHeader('Cache-Control','public,max-age=120,s-maxage=120');
  return res.status(200).end(bytes);
 }catch(err){console.error('DParranda sponsored banner read failed',err?.name||'Error');return res.status(503).end()}
}
