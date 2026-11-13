// Creates secure advertiser workspaces from validated campaign proposals.
// No access token is exposed to public requests or stored in plaintext.
import {createHash,randomBytes} from 'node:crypto';
import {safeText} from './admin-auth.js';
const PRICES={local:1900,zona:4900,insular:9900};
export function advertiserPortalReady(){
 return !!process.env.DATABASE_URL&&!!process.env.DPARRANDA_SESSION_SECRET&&
 process.env.DPARRANDA_SESSION_SECRET.length>=32&&
 (process.env.DPARRANDA_ADVERTISER_PORTAL_ENABLED==='true'||process.env.DPARRANDA_LEADS_ENABLED==='true');
}
export async function ensureAdvertiserWorkspace(sql,leadId){
 const [lead]=await sql`SELECT id,company,contact_name,email,municipality,dates_text,
 campaign_name,campaign_start,campaign_days,banner_text,action_url,creative_alt,
 event_start,event_venue,event_municipality,review_status,review_note
 FROM advertising_enquiries WHERE id=${leadId}`;
 if(!lead||!lead.company||!lead.email||!['submitted','changes_requested','approved_for_payment'].includes(lead.review_status))
  return null;
 const parts=String(lead.dates_text||'').split('|');
 if(parts[0]!=='INTERES_INICIAL'||!Object.hasOwn(PRICES,parts[1])||
 !['30','60'].includes(parts[3])||!['banner','evento'].includes(parts[4]))return null;
 const [plan,days,placement]=[parts[1],Number(parts[3]),parts[4]];
 const dummyHash=createHash('sha256').update(randomBytes(32)).digest('hex');
 const [account]=await sql`INSERT INTO advertiser_accounts
 (lead_id,company,contact_name,email,token_hash)
 VALUES(${leadId},${safeText(lead.company,120)},${safeText(lead.contact_name,100)},${lead.email},${dummyHash})
 ON CONFLICT(lead_id) DO UPDATE SET updated_at=advertiser_accounts.updated_at
 RETURNING id,email,company,contact_name,access_version,active`;
 if(!account||!account.active)return null;
 const limit=plan==='local'?1:plan==='zona'?4:0;
 const towns=plan==='insular'?[]:String(lead.municipality||'').split(',').map(x=>x.trim()).filter(Boolean).slice(0,limit);
 const [draft]=await sql`INSERT INTO advertiser_campaign_drafts
 (advertiser_id,source_lead_id,plan,days,price_cents,municipalities,placement,
 advertiser,title,description,destination,campaign_start,event_start,event_town,event_venue,
 image_alt,review_note,status)
 VALUES(${account.id},${leadId},${plan},${days},${PRICES[plan]*(days/30)},
 ${JSON.stringify(towns)}::jsonb,${placement},${lead.company},
 ${lead.campaign_name||lead.company},
 ${safeText(lead.banner_text||'',350)||'Propuesta de publicidad enviada para revisión'},
 ${lead.action_url},${lead.campaign_start},
 ${placement==='evento'?lead.event_start:null},
 ${placement==='evento'?lead.event_municipality:null},
 ${placement==='evento'?lead.event_venue:null},
 ${lead.creative_alt||''},${lead.review_note||null},${lead.review_status})
 ON CONFLICT(source_lead_id) DO UPDATE SET updated_at=advertiser_campaign_drafts.updated_at
 RETURNING id,title,status`;
 await sql`INSERT INTO advertiser_campaign_draft_images(draft_id,mime_type,width,height,image_data)
 SELECT ${draft.id},mime_type,width,height,image_data FROM advertising_enquiry_images
 WHERE enquiry_id=${leadId} ON CONFLICT(draft_id) DO NOTHING`;
 return {account:{id:Number(account.id),email:account.email,company:account.company,
  contact_name:account.contact_name,access_version:account.access_version,active:account.active},
  draft:{id:Number(draft.id),title:draft.title,status:draft.status},leadId:Number(leadId)};
}

export async function workspaceForDraft(sql,draftId){
 const [row]=await sql`SELECT a.id AS account_id,a.company,a.contact_name,a.email,
  a.access_version,a.active,d.id AS draft_id,d.title,d.status,d.placement,d.source_lead_id
  FROM advertiser_campaign_drafts d JOIN advertiser_accounts a ON a.id=d.advertiser_id
  WHERE d.id=${draftId}`;
 if(!row)return null;
 return {account:{id:Number(row.account_id),company:row.company,contact_name:row.contact_name,
   email:row.email,access_version:row.access_version,active:row.active},
  draft:{id:Number(row.draft_id),title:row.title,status:row.status,placement:row.placement},
  leadId:Number(row.source_lead_id)||null};
}
