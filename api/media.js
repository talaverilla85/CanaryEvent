import { db } from '../lib/admin-auth.js';
export default async function handler(req,res){
 if(req.method!=='GET'){res.status(405).end();return}
 res.setHeader('X-Content-Type-Options','nosniff');
 const id=Number(req.query?.id);
 if(!Number.isSafeInteger(id)||id<1)return res.status(404).end();
 const sql=db();if(!sql)return res.status(503).end();
 try{
  const [item]=await sql`SELECT i.mime_type,i.image_data
    FROM advertising_enquiry_images i WHERE i.enquiry_id=${id}
    AND (
      EXISTS(SELECT 1 FROM sponsored_events e
        WHERE e.enquiry_id=i.enquiry_id AND e.enabled=TRUE AND e.review_status='approved'
        AND (e.campaign_starts_at IS NULL OR e.campaign_starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date))
        AND (e.campaign_ends_at IS NULL OR e.campaign_ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)))
      OR EXISTS(SELECT 1 FROM ad_campaigns a
        WHERE a.enquiry_id=i.enquiry_id AND a.enabled=TRUE
        AND (a.starts_at IS NULL OR a.starts_at<=((now() AT TIME ZONE 'Atlantic/Canary')::date))
        AND (a.ends_at IS NULL OR a.ends_at>=((now() AT TIME ZONE 'Atlantic/Canary')::date)))
    )`;
  if(!item)return res.status(404).end();
  const bytes=typeof item.image_data==='string'?Buffer.from(item.image_data.replace(/^\\x/,''),'hex'):Buffer.from(item.image_data);
  res.setHeader('Content-Type',item.mime_type);
  res.setHeader('Cache-Control','public, max-age=120, s-maxage=120');
  res.setHeader('X-Content-Type-Options','nosniff');
  res.status(200).end(bytes);
 }catch(e){console.error('DParranda media read error:',e?.name||'Error');res.status(503).end()}
}