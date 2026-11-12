// Public only for approved and paid sponsored events within contracted date range.
import {db} from '../lib/admin-auth.js';
export default async function handler(req,res){
 res.setHeader('X-Content-Type-Options','nosniff');
 if(req.method!=='GET')return res.status(405).end();
 const id=Number(req.query?.id);if(!Number.isSafeInteger(id)||id<1)return res.status(404).end();
 const sql=db();if(!sql)return res.status(503).end();
 try{
  const [img]=await sql`SELECT i.mime_type,i.image_data
   FROM sponsored_events s
   JOIN advertiser_campaign_drafts d ON d.id=s.advertiser_draft_id
   JOIN advertiser_campaign_draft_images i ON i.draft_id=d.id
   WHERE s.id=${id} AND s.enabled=TRUE AND s.review_status='approved'
    AND d.status='active' AND d.payment_status='paid'
    AND s.campaign_starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date)
    AND s.campaign_ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)`;
  if(!img)return res.status(404).end();
  const bytes=typeof img.image_data==='string'?Buffer.from(img.image_data.replace(/^\\x/,''),'hex'):Buffer.from(img.image_data);
  res.setHeader('Content-Type',img.mime_type);res.setHeader('Cache-Control','public,max-age=120,s-maxage=120');
  return res.status(200).end(bytes);
 }catch(err){console.error('DParranda sponsored image read failed',err?.name||'Error');return res.status(503).end()}
}
