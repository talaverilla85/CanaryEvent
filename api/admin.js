import { createHmac, createHash, randomBytes, randomUUID } from 'node:crypto';
// Uploaded WebP creatives can be ~800 KB before base64 encoding; accept the encoded form safely.
export const config={api:{bodyParser:{sizeLimit:'2mb'}}};
import { authenticated, db, isConfigured, json, passwordValid, safeText, sameOrigin, setSession, validLocalDate } from '../lib/admin-auth.js';
import {privacyUrl,missingPrivacyIdentity} from '../lib/privacy.js';
import {resendTestConfiguration,sendResendAdminTest} from '../lib/resend-test.js';
import {ensureAdvertiserWorkspace,workspaceForDraft} from '../lib/advertiser-workspace.js';
import {sendChangesRequestedEmail,advertiserMailStatus} from '../lib/advertiser-mail.js';
import {ensureApprovedPayment,stripePaymentsReady} from '../lib/stripe-advertising.js';
import {schedulePaidDraft} from '../lib/advertiser-publication.js';
import {editPaidCreative,setPaidPublicationEnabled} from '../lib/paid-ad-edit.js';

const statuses = new Set(['unreviewed','approved','needs_review','rejected']);
const kinds = new Set(['house','paid']);
function data(req) {
  if (req.body && typeof req.body === 'object' && !Array.isArray(req.body)) return req.body;
  try { return JSON.parse(req.body || '{}'); } catch { return {}; }
}
function validId(value) {
  const n = Number(value);
  return Number.isSafeInteger(n) && n !== 0 ? n : null;
}
async function attempt(sql, req, correct) {
  const ip = String(req.headers['x-forwarded-for'] || req.socket?.remoteAddress || '').split(',')[0].trim().slice(0,100);
  const fingerprint = createHmac('sha256', process.env.DPARRANDA_SESSION_SECRET).update(ip || 'missing-ip').digest('hex');
  const [row] = await sql`SELECT attempts,window_started_at FROM admin_login_limits WHERE fingerprint=${fingerprint}`;
  const recent = row && Date.now() - new Date(row.window_started_at).getTime() < 15 * 60_000;
  if (recent && row.attempts >= 8) return false;
  if (correct) {
    await sql`DELETE FROM admin_login_limits WHERE fingerprint=${fingerprint}`;
    return true;
  }
  await sql`INSERT INTO admin_login_limits(fingerprint,attempts,window_started_at)
    VALUES(${fingerprint},1,now())
    ON CONFLICT(fingerprint) DO UPDATE SET
      attempts=CASE WHEN admin_login_limits.window_started_at < now()-interval '15 minutes' THEN 1 ELSE admin_login_limits.attempts+1 END,
      window_started_at=CASE WHEN admin_login_limits.window_started_at < now()-interval '15 minutes' THEN now() ELSE admin_login_limits.window_started_at END`;
  return true;
}
async function events(sql, query) {
  const q = safeText(query.q,120);
  const only = String(query.only || 'all');
  const offset = Math.max(0,Math.min(10000,Number.parseInt(query.offset,10) || 0));
  const rows = await sql`
    SELECT p.id,p.payload,o.hidden,o.title_override,o.details_override,
           o.venue_override,o.price_override,o.free_override,o.category_override,
           o.canonical_event_id,o.review_status,
    EXISTS(SELECT 1 FROM published_events r
        LEFT JOIN event_overrides r_override ON r_override.event_id=r.id
        WHERE r.active AND r.id<>p.id AND COALESCE(r_override.hidden,FALSE)=FALSE
        AND r_override.canonical_event_id IS NULL
        AND r.payload->>'municipality'=p.payload->>'municipality'
        AND left(r.payload->>'start',10)=left(p.payload->>'start',10)
        AND regexp_replace(lower(r.payload->>'title'),'[^[:alnum:]]','','g')
             =regexp_replace(lower(p.payload->>'title'),'[^[:alnum:]]','','g')) AS possible_duplicate
    FROM published_events p
    LEFT JOIN event_overrides o ON o.event_id=p.id
    WHERE p.active AND
      (${q}='' OR p.payload->>'title' ILIKE '%'||${q}||'%' OR p.payload->>'municipality' ILIKE '%'||${q}||'%')
    ORDER BY p.payload->>'start' ASC,p.id
    LIMIT 3500`;
  const filtered = rows.filter(r => only==='all' ||
    (only==='duplicates' ? (r.possible_duplicate && !r.hidden && !r.canonical_event_id) :
     only==='hidden' ? (r.hidden===true) :
     only==='review' ? (!r.hidden && !r.canonical_event_id &&
       (r.review_status==='needs_review'||r.review_status==='unreviewed'||r.possible_duplicate)) : true));
  return {events:filtered.slice(offset,offset+60),has_more:filtered.length>offset+60,offset,next_offset:offset+60};
}
async function saveEvent(sql, body) {
  const id=validId(body.id);
  if(id===null)throw new Error('Identificador de evento inválido');
  const [old]=await sql`SELECT id,payload FROM published_events WHERE id=${id} AND active`;
  if(!old)throw new Error('Evento no encontrado');
  const canonical = body.canonical_event_id===null || body.canonical_event_id==='' || body.canonical_event_id===undefined ? null : validId(body.canonical_event_id);
  if(canonical!==null){
    if(canonical===id)throw new Error('No puedes fusionar una ficha consigo misma');
    const [target]=await sql`SELECT payload FROM published_events WHERE id=${canonical} AND active`;
    if(!target)throw new Error('No se encuentra la ficha principal');
    if(target.payload.municipality!==old.payload.municipality ||
       String(target.payload.start).slice(0,10)!==String(old.payload.start).slice(0,10))
      throw new Error('Las dos fichas deben corresponder al mismo municipio y día');
  }
  const review=statuses.has(body.review_status)?body.review_status:'needs_review';
  const title=safeText(body.title_override,220)||null;
  const details=safeText(body.details_override,3000)||null;
  const venue=safeText(body.venue_override,220)||null;
  const price=safeText(body.price_override,100)||null;
  const category=safeText(body.category_override,80)||null;
  const free=(body.free_override===null||body.free_override===''||body.free_override===undefined)?null:Number(body.free_override);
  if(free!==null && ![0,1].includes(free))throw new Error('Gratuidad inválida');
  const hidden=body.hidden===true;
  await sql`INSERT INTO event_overrides
    (event_id,hidden,title_override,details_override,venue_override,price_override,
     free_override,category_override,canonical_event_id,review_status,updated_at)
    VALUES(${id},${hidden},${title},${details},${venue},${price},${free},${category},${canonical},${review},now())
    ON CONFLICT(event_id) DO UPDATE SET
      hidden=excluded.hidden,title_override=excluded.title_override,
      details_override=excluded.details_override,venue_override=excluded.venue_override,
      price_override=excluded.price_override,free_override=excluded.free_override,
      category_override=excluded.category_override,canonical_event_id=excluded.canonical_event_id,
      review_status=excluded.review_status,updated_at=now()`;
  return {id,updated:true};
}
// Reversible moderation: keep the original imported event and all manual
// corrections. Subsequent source syncs must not republish a hidden duplicate.
async function setEventVisibility(sql, body) {
  const id=validId(body.id);
  if(id===null)throw new Error('Identificador de evento inválido');
  if(typeof body.hidden!=='boolean')throw new Error('Indica si quieres ocultar o restaurar la ficha');
  const [row]=await sql`SELECT id FROM published_events WHERE id=${id} AND active`;
  if(!row)throw new Error('Evento no encontrado');
  await sql`INSERT INTO event_overrides(event_id,hidden,updated_at)
    VALUES(${id},${body.hidden},now())
    ON CONFLICT(event_id) DO UPDATE SET
      hidden=excluded.hidden,updated_at=now()`;
  return {id,hidden:body.hidden,updated:true};
}
function adminImageData(value) {
  if(value===undefined||value===null||value==='')return null;
  if(typeof value!=='string'||value.length>1150000)
    throw new Error('Imagen inválida: utiliza un archivo JPG, PNG o WebP de hasta 800 KB optimizados');
  const match=/^data:image\/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)$/.exec(value);
  if(!match)throw new Error('Imagen inválida: formato no permitido');
  const mime='image/'+match[1],base64=match[2],bytes=Buffer.from(base64,'base64');
  if(bytes.length<1000||bytes.length>800000||Number(value.length)>1150000)
    throw new Error('Imagen inválida: tamaño fuera del límite');
  const valid=mime==='image/jpeg'?bytes.subarray(0,3).toString('hex')==='ffd8ff':
    mime==='image/png'?bytes.subarray(0,8).toString('hex')==='89504e470d0a1a0a':
    bytes.toString('ascii',0,4)==='RIFF'&&bytes.toString('ascii',8,12)==='WEBP';
  if(!valid)throw new Error('Imagen inválida: comprueba el archivo');
  return {mime,base64};
}
// Dimensions are checked by the browser before encoding; the server also
// validates file signatures and size to reject unexpected file contents.
async function adminAdImage(sql,res,id){
  if(typeof id!=='string'||! /^[a-zA-Z0-9_-]{2,90}$/.test(id))return json(res,404,{error:'Imagen no encontrada'});
  const [asset]=await sql`SELECT mime_type,image_data FROM ad_campaign_images WHERE ad_id=${id}`;
  if(!asset)return json(res,404,{error:'Imagen no encontrada'});
  const bytes=typeof asset.image_data==='string'?
    Buffer.from(asset.image_data.replace(/^\\x/,''),'hex'):Buffer.from(asset.image_data);
  res.setHeader('Content-Type',asset.mime_type);
  res.setHeader('Content-Disposition','inline');
  res.setHeader('Cache-Control','private, no-store');
  return res.status(200).end(bytes);
}
async function saveAd(sql, body) {
  const id=typeof body.id==='string' && /^[a-zA-Z0-9_-]{2,90}$/.test(body.id) ? body.id : 'anuncio-'+randomUUID();
  const advertiser=safeText(body.advertiser,100), headline=safeText(body.headline,160);
  if(!advertiser || !headline)throw new Error('Indica anunciante y titular');
  const url=safeText(body.button_url,800);
  try { if(new URL(url).protocol!=='https:')throw new Error(); }
  catch { throw new Error('El enlace del anuncio debe comenzar por https://'); }
  const image=safeText(body.image,400);
  if(image && !/^\/sponsors\/[a-z0-9._/-]+\.(webp|png|jpeg|jpg)$/i.test(image))
    throw new Error('Por ahora, la imagen debe existir en /sponsors/ del proyecto');
  const starts=body.starts_at||null, ends=body.ends_at||null;
  if(!starts||!ends||!validLocalDate(starts)||!validLocalDate(ends)||starts>ends)
    throw new Error('Indica una fecha de inicio y una duración de 1 a 60 días');
  const duration=Math.round((Date.parse(ends+'T00:00:00Z')-Date.parse(starts+'T00:00:00Z'))/86400000)+1;
  if(duration<1||duration>60)throw new Error('La campaña no puede superar 60 días. Puedes renovarla después.');
  const asset=adminImageData(body.image_data);
  if(asset && (Number(body.image_width)!==1200||Number(body.image_height)!==675))
    throw new Error('La imagen debe prepararse en formato horizontal 1200 × 675');

  const kind=kinds.has(body.kind)?body.kind:'house';
  // An existing contracted advertiser campaign cannot be converted into a free house ad.
  const [original]=await sql`SELECT kind FROM ad_campaigns WHERE id=${id}`;
  if(original&&original.kind!==kind)
    throw new Error('No puedes cambiar una campaña comercial por una propia ni a la inversa');
  const municipalities=Array.isArray(body.municipalities)?
    [...new Set(body.municipalities.filter(x=>typeof x==='string').map(x=>safeText(x,75)).filter(Boolean))].slice(0,25):[];
  const enabled=body.enabled===true,permanent=false;
  const description=safeText(body.description,400), location=safeText(body.location,120);
  const buttonText=safeText(body.button_text,70)||'Descubrir',imageAlt=safeText(body.image_alt,160);
  const disclosure='Publicidad';
  await sql`INSERT INTO ad_campaigns
    (id,enabled,advertiser,kind,permanent,starts_at,ends_at,municipalities,headline,
     description,location,button_text,button_url,image,image_alt,disclosure,updated_at)
    VALUES (${id},${enabled},${advertiser},${kind},${permanent},${starts},${ends},
            ${JSON.stringify(municipalities)}::jsonb,${headline},${description},${location},
            ${buttonText},${url},${image},${imageAlt},${disclosure},now())
    ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled,advertiser=excluded.advertiser,
      kind=excluded.kind,permanent=excluded.permanent,starts_at=excluded.starts_at,
      ends_at=excluded.ends_at,municipalities=excluded.municipalities,
      headline=excluded.headline,description=excluded.description,location=excluded.location,
      button_text=excluded.button_text,button_url=excluded.button_url,image=excluded.image,
      image_alt=excluded.image_alt,disclosure=excluded.disclosure,updated_at=now()`;
  if(asset){
    await sql`INSERT INTO ad_campaign_images(ad_id,mime_type,width,height,image_data,updated_at)
      VALUES(${id},${asset.mime},1200,675,decode(${asset.base64},'base64'),now())
      ON CONFLICT(ad_id) DO UPDATE SET mime_type=excluded.mime_type,
        width=excluded.width,height=excluded.height,image_data=excluded.image_data,
        updated_at=excluded.updated_at`;
  }
  return {id,updated:true,has_uploaded_image:!!asset};
}
async function setHouseCampaignEnabled(sql,body){
 const id=typeof body?.id==='string'&&/^[a-zA-Z0-9_-]{2,90}$/.test(body.id)?body.id:null;
 if(!id||typeof body.enabled!=='boolean')throw new Error('Campaña propia inválida');
 const [old]=await sql`SELECT kind,permanent,starts_at,ends_at FROM ad_campaigns WHERE id=${id}`;
 if(!old||old.kind!=='house')throw new Error('Solo puedes activar o pausar publicidad propia');
 if(body.enabled===true&&!old.permanent){
  if(!old.starts_at||!old.ends_at)throw new Error('Indica las fechas para activar la campaña');
  const [expired]=await sql`SELECT ${old.ends_at}::date<((now() AT TIME ZONE 'Atlantic/Canary')::date) AS expired`;
  if(expired?.expired)throw new Error('La campaña ha terminado: edita las fechas antes de activarla');
 }
 await sql`UPDATE ad_campaigns SET enabled=${body.enabled},updated_at=now()
  WHERE id=${id} AND kind='house'`;
 return {id,enabled:body.enabled};
}
function leadId(value){const n=Number(value);return Number.isSafeInteger(n)&&n>0?n:null}
async function listLeads(sql){
 const rows=await sql`SELECT id,company,contact_name,email,telephone,legal_name,tax_id,
   billing_type,billing_address,billing_postal,billing_city,billing_region,billing_country,
   billing_email,format,municipality,event_municipality,campaign_name,campaign_start,campaign_days,
   event_title,event_start,event_end,event_venue,category,event_price,action_url,message,
   banner_text,creative_alt,image_name,dates_text,status,review_status,review_note,
   payment_status,created_at,
   EXISTS(SELECT 1 FROM advertising_enquiry_images i WHERE i.enquiry_id=advertising_enquiries.id) AS has_image,
   EXISTS(SELECT 1 FROM advertiser_campaign_drafts d WHERE d.source_lead_id=advertising_enquiries.id) AS has_linked_draft
   FROM advertising_enquiries ORDER BY created_at DESC LIMIT 200`;
 return {leads:rows};
}
async function listPromotions(sql){
 const rows=await sql`SELECT id,enquiry_id,enabled,review_status,advertiser,title,start,
    "end",municipality,venue,category,details,price,source_url,campaign_starts_at,
    campaign_ends_at,image_alt,updated_at
   FROM sponsored_events ORDER BY created_at DESC LIMIT 120`;
 return {promotions:rows};
}
async function leadImage(sql,res,id){
 const [entry]=await sql`SELECT mime_type,image_data FROM advertising_enquiry_images WHERE enquiry_id=${id}`;
 if(!entry)return json(res,404,{error:'Imagen no encontrada'});
 const bytes=typeof entry.image_data==='string'
   ?Buffer.from(entry.image_data.replace(/^\\x/,''),'hex'):Buffer.from(entry.image_data);
 res.setHeader('Content-Type',entry.mime_type);
 res.setHeader('Content-Disposition','inline');
 res.setHeader('Cache-Control','private, no-store');
 return res.status(200).end(bytes);
}
async function promoteLead(sql,body){
 const id=leadId(body.id),placement=String(body.placement||'');
 if(!id||!['event','banner'].includes(placement))throw new Error('Solicitud o formato inválido');
 const [lead]=await sql`SELECT * FROM advertising_enquiries WHERE id=${id}`;
 if(!lead)throw new Error('Solicitud no encontrada');
 if(placement==='event'){
  if(!lead.event_title||!lead.event_start||!lead.event_municipality||!lead.event_venue)
     throw new Error('La propuesta necesita los datos completos del evento');
  const [already]=await sql`SELECT id FROM sponsored_events WHERE enquiry_id=${id} ORDER BY id LIMIT 1`;
  if(already)return {created:false,id:Number(already.id),placement};
  const [created]=await sql`INSERT INTO sponsored_events
   (enquiry_id,enabled,review_status,advertiser,title,start,"end",municipality,venue,
     category,details,price,source_url,image_alt,campaign_starts_at,campaign_ends_at)
    VALUES (${id},FALSE,'draft',${lead.company},${lead.event_title},${lead.event_start},
      ${lead.event_end},${lead.event_municipality},${lead.event_venue},
      ${lead.category||'ocio'},${lead.message||''},${lead.event_price||''},${lead.action_url},
      ${lead.creative_alt||''},${lead.campaign_start},(${lead.campaign_start}::date+${Number(lead.campaign_days)-1})::date)
    RETURNING id`;
  return {created:true,id:Number(created.id),placement,status:'draft'};
 }
 const adId='promo-'+id;
 const town=String(lead.municipality||'').trim();
 const municipalities=/toda gran canaria/i.test(town)?[]:town.split(',').map(x=>x.trim()).filter(Boolean);
 const [already]=await sql`SELECT id FROM ad_campaigns WHERE id=${adId}`;
 if(already)return {created:false,id:adId,placement};
 await sql`INSERT INTO ad_campaigns
  (id,enquiry_id,enabled,advertiser,kind,permanent,starts_at,ends_at,municipalities,
   headline,description,location,button_text,button_url,image,image_alt,disclosure)
  VALUES(${adId},${id},FALSE,${lead.company},'paid',FALSE,
    ${lead.campaign_start},(${lead.campaign_start}::date+${Number(lead.campaign_days)-1})::date,
    ${JSON.stringify(municipalities)}::jsonb,${lead.campaign_name},${lead.banner_text||lead.message.slice(0,220)},
    ${lead.municipality},'Más información',${lead.action_url},'',${lead.creative_alt||''},'Publicidad')`;
 return {created:true,id:adId,placement,status:'paused'};
}
async function changePromotion(sql,body){
 const id=leadId(body.id);if(!id)throw new Error('Identificador inválido');
 const approved=body.approved===true,enabled=body.enabled===true;
 const [old]=await sql`SELECT id FROM sponsored_events WHERE id=${id}`;
 if(!old)throw new Error('Promoción no encontrada');
 await sql`UPDATE sponsored_events SET review_status=${approved?'approved':'draft'},
    enabled=${approved&&enabled},updated_at=now() WHERE id=${id}`;
 return {id,approved,enabled:approved&&enabled};
}
async function changeLead(sql,body){
 const id=leadId(body.id),status=String(body.status||'');
 if(!id||!['new','contacted','closed'].includes(status))throw new Error('Estado inválido');
 const [updated]=await sql`UPDATE advertising_enquiries SET status=${status} WHERE id=${id} RETURNING id`;
 if(!updated)throw new Error('Solicitud no encontrada');
 return {id,status};
}


function invitedId(value){
 const number=Number(value);
 return Number.isSafeInteger(number)&&number>0?number:null;
}
async function advertiserAccounts(sql){
 const accounts=await sql`SELECT a.id,a.lead_id,a.company,a.contact_name,a.email,a.active,a.created_at,a.updated_at,
   (SELECT count(*)::int FROM advertiser_campaign_drafts d WHERE d.advertiser_id=a.id) AS campaigns
   FROM advertiser_accounts a ORDER BY a.created_at DESC LIMIT 150`;
 return {accounts};
}
async function advertiserInvite(sql,body,req){
 const leadId=invitedId(body.lead_id);
 if(!leadId)throw new Error('Selecciona una solicitud de empresa válida');
 const [lead]=await sql`SELECT company,contact_name,email,dates_text,municipality,format,
 campaign_name,campaign_start,campaign_days,banner_text,action_url,creative_alt,
 event_start,event_venue,event_municipality,review_status,review_note
 FROM advertising_enquiries WHERE id=${leadId}`;
 if(!lead)throw new Error('Solicitud no encontrada');
 if(!lead.company||!lead.email)throw new Error('La solicitud necesita empresa y correo');
 const [existing]=await sql`SELECT id FROM advertiser_accounts WHERE lead_id=${leadId}`;
 if(existing&&body.rotate!==true)throw new Error('Este anunciante ya tiene acceso. Confirma que quieres regenerar su enlace.');
 const raw=randomBytes(32).toString('hex');
 const digest=createHash('sha256').update(raw).digest('hex');
 let accountId;
 if(existing){
  const [changed]=await sql`UPDATE advertiser_accounts SET token_hash=${digest},
   access_version=access_version+1,active=TRUE,updated_at=now()
   WHERE id=${existing.id} RETURNING id`;
  accountId=Number(changed.id);
 }else{
  const [created]=await sql`INSERT INTO advertiser_accounts
   (lead_id,company,contact_name,email,token_hash)
   VALUES(${leadId},${lead.company},${lead.contact_name||''},${lead.email},${digest})
   RETURNING id`;
  accountId=Number(created.id);
 }
 // Public preview proposals are carried into the advertiser workspace
 // when the admin shares an invitation. The original enquiry remains audited.
 const parts=String(lead.dates_text||'').split('|');
 if(['submitted','changes_requested','approved_for_payment'].includes(lead.review_status)&&
    parts[0]==='INTERES_INICIAL'&&['local','zona','insular'].includes(parts[1])&&
    ['30','60'].includes(parts[3])&&['banner','evento'].includes(parts[4])){
  const plan=parts[1],days=Number(parts[3]),placement=parts[4];
  const limit=plan==='local'?1:plan==='zona'?4:0;
  const towns=plan==='insular'?[]:String(lead.municipality||'')
     .split(',').map(x=>x.trim()).filter(Boolean).slice(0,limit);
  const prices={local:1900,zona:4900,insular:9900};
  const [previous]=await sql`SELECT id FROM advertiser_campaign_drafts WHERE source_lead_id=${leadId}`;
  if(!previous){
   const state=lead.review_status;
   const description=safeText(lead.banner_text||'',350)||'Propuesta de publicidad enviada para revisión';
   const [created]=await sql`INSERT INTO advertiser_campaign_drafts
    (advertiser_id,source_lead_id,plan,days,price_cents,municipalities,placement,
     advertiser,title,description,destination,campaign_start,event_start,event_town,
     event_venue,image_alt,review_note,status)
    VALUES (${accountId},${leadId},${plan},${days},${prices[plan]*(days/30)},
     ${JSON.stringify(towns)}::jsonb,${placement},${lead.company},
     ${lead.campaign_name||lead.company},${description},${lead.action_url},
     ${lead.campaign_start},${placement==='evento'?lead.event_start:null},
     ${placement==='evento'?lead.event_municipality:null},
     ${placement==='evento'?lead.event_venue:null},
     ${lead.creative_alt||''},${lead.review_note||null},${state}) RETURNING id`;
   await sql`INSERT INTO advertiser_campaign_draft_images(draft_id,mime_type,width,height,image_data)
    SELECT ${created.id},mime_type,width,height,image_data FROM advertising_enquiry_images
    WHERE enquiry_id=${leadId} ON CONFLICT(draft_id) DO NOTHING`;
  }
 }
 // Server only returns this sensitive link once: never persist its raw token.
 const origin=String(req.headers.origin||'');
 return {created:true,account_id:accountId,
  invitation_url:origin+'/anunciantes/#acceso='+raw,
  message:'Copia el enlace y envíalo tú por correo. El enlace anterior queda invalidado si se ha regenerado.'};
}
async function advertiserChangeAccess(sql,body){
 const id=invitedId(body.id);
 if(!id||typeof body.active!=='boolean')throw new Error('Acceso o estado inválido');
 const [updated]=await sql`UPDATE advertiser_accounts SET active=${body.active},
 access_version=access_version+1,updated_at=now() WHERE id=${id}
 RETURNING id,active`;
 if(!updated)throw new Error('Anunciante no encontrado');
 return {id:Number(updated.id),active:updated.active};
}
async function advertiserDrafts(sql){
 const drafts=await sql`SELECT d.id,d.advertiser_id,a.company AS account_company,a.contact_name AS account_contact,a.email AS account_email,d.plan,d.days,d.price_cents,
 d.municipalities,d.placement,d.advertiser,d.title,d.description,d.destination,d.image_alt,d.status,d.payment_status,
 d.campaign_start,d.event_start,d.event_town,d.event_venue,d.actual_starts_at,d.actual_ends_at,d.review_note,d.source_lead_id,
 d.updated_at,d.stripe_payment_url,d.paid_at,d.published_ad_id,d.published_event_id,
 CASE WHEN d.published_event_id IS NOT NULL THEN
   (SELECT s.enabled FROM sponsored_events s WHERE s.id=d.published_event_id AND s.advertiser_draft_id=d.id)
  WHEN d.published_ad_id IS NOT NULL THEN
   (SELECT ac.enabled FROM ad_campaigns ac WHERE ac.id=d.published_ad_id)
  ELSE NULL END AS published_enabled,EXISTS(SELECT 1 FROM advertiser_campaign_draft_images i WHERE i.draft_id=d.id) AS has_image
 FROM advertiser_campaign_drafts d JOIN advertiser_accounts a ON a.id=d.advertiser_id
 ORDER BY d.updated_at DESC LIMIT 150`;
 return {drafts};
}
async function advertiserDraftImage(sql,res,id){
 const [img]=await sql`SELECT mime_type,image_data FROM advertiser_campaign_draft_images WHERE draft_id=${id}`;
 if(!img)return json(res,404,{error:'Imagen no encontrada'});
 const bytes=typeof img.image_data==='string'
  ?Buffer.from(img.image_data.replace(/^\\x/,''),'hex'):Buffer.from(img.image_data);
 res.setHeader('Content-Type',img.mime_type);
 res.setHeader('Content-Disposition','inline');
 res.setHeader('Cache-Control','private, no-store');
 res.setHeader('X-Content-Type-Options','nosniff');
 return res.status(200).end(bytes);
}
async function notifyChangesSafely(workspace,note,revision){
 if(!workspace||!workspace.account?.active)return 'unavailable';
 try{
  const result=await sendChangesRequestedEmail(workspace,note,revision);
  return result.status;
 }catch(e){
  console.error('DParranda revision email failed:',e?.name||'Error');
  return 'failed';
 }
}
function changesMessage(status){
 if(status==='sent')return 'Cambios guardados. Resend ha aceptado el correo al anunciante.';
 if(status==='pending_domain')return 'Cambios guardados. El email al anunciante queda pendiente hasta verificar el dominio. Solo recibe correos la dirección de pruebas de Resend.';
 if(status==='failed')return 'Cambios guardados, pero falló el correo. Revisa Resend antes de dar por avisado al cliente.';
 return 'Cambios guardados. Aún no hay un correo automático disponible para esta solicitud.';
}
async function safelyPreparePayment(sql,id){
 try{return await ensureApprovedPayment(sql,id)}
 catch(e){console.error('DParranda Stripe payment link failed',e?.name||'Error');return {status:'failed',email_status:'failed'}}
}
function paymentMessage(p){
 if(p.status==='not_configured')return 'Anuncio aprobado. Stripe queda pendiente de configuración en Vercel.';
 if(p.status==='failed')return 'Anuncio aprobado, pero Stripe no pudo generar el enlace. Puedes reintentarlo.';
 if(p.status==='already_paid')return 'Pago confirmado anteriormente.';
 if(p.status==='unavailable')return 'Anuncio aprobado. Necesita área de anunciante antes de cobrar.';
 if(p.email_status==='sent')return 'Enlace Stripe generado y correo de aprobación aceptado por Resend.';
 if(p.email_status==='pending_domain')return 'Enlace de pago generado. Resend solo puede escribir al correo de pruebas hasta verificar el dominio.';
 return 'Enlace Stripe creado, pero el correo no se ha confirmado. Puedes reenviarlo.';
}
async function reviewEnquiry(sql,body){
 const id=invitedId(body.id),decision=String(body.status||''),note=safeText(body.note,500);
 if(!id||!['changes_requested','approved_for_payment','rejected'].includes(decision))
  throw new Error('Revisión no válida');
 if(decision==='changes_requested'&&!note)throw new Error('Indica qué cambios debe realizar el anunciante');
 const [lead]=await sql`SELECT id,review_status,
   EXISTS(SELECT 1 FROM advertising_enquiry_images i WHERE i.enquiry_id=advertising_enquiries.id) AS has_image,
   EXISTS(SELECT 1 FROM advertiser_campaign_drafts d WHERE d.source_lead_id=advertising_enquiries.id) AS has_linked_draft
   FROM advertising_enquiries WHERE id=${id}`;
 if(!lead||lead.review_status==='interest')throw new Error('No es una propuesta de publicación');
 if(lead.has_linked_draft)throw new Error('Revisa la versión actualizada de la campaña, no su solicitud original');
 if(!['submitted','changes_requested'].includes(lead.review_status))
  throw new Error('Esta propuesta no admite cambios de estado');
 if(decision==='approved_for_payment'&&!lead.has_image)
  throw new Error('El anunciante debe adjuntar una imagen antes de aprobar la propuesta');
 const [changed]=await sql`UPDATE advertising_enquiries SET review_status=${decision},
  review_note=${note},status='contacted' WHERE id=${id}
  RETURNING id,review_status`;
 let emailStatus='not_requested';
 if(decision==='changes_requested'){
  try{
   const workspace=await ensureAdvertiserWorkspace(sql,id);
   emailStatus=await notifyChangesSafely(workspace,note,'lead-'+id+'-'+Date.now());
  }catch(e){
   console.error('DParranda revision workspace failed:',e?.name||'Error');
   emailStatus='failed';
  }
 }
 let payment=null;
 if(decision==='approved_for_payment'){
  try{
   const workspace=await ensureAdvertiserWorkspace(sql,id);
   if(workspace?.draft?.id){
    await sql`UPDATE advertiser_campaign_drafts SET status='approved_for_payment',updated_at=now()
     WHERE id=${workspace.draft.id} AND status IN ('submitted','changes_requested')`;
    payment=await safelyPreparePayment(sql,workspace.draft.id);
   }else payment={status:'unavailable'};
  }catch(e){console.error('DParranda payment workspace failed',e?.name||'Error');payment={status:'failed'}}
 }
 return {id:Number(changed.id),status:changed.review_status,
  notification_status:payment?.email_status||emailStatus,payment_enabled:payment?.status==='ready',message:decision==='approved_for_payment'
   ?paymentMessage(payment||{status:'failed'})
   :decision==='changes_requested'?changesMessage(emailStatus):'Solicitud rechazada. No se ha enviado ningún correo automático.'};
}
async function advertiserReview(sql,body){
 const id=invitedId(body.id),decision=String(body.status||''),note=safeText(body.note,500);
 if(!id||!['changes_requested','rejected','approved_for_payment'].includes(decision))
   throw new Error('Estado de revisión inválido');
 if(decision==='changes_requested'&&!note)
   throw new Error('Explica al anunciante qué debe corregir');
 const [draft]=await sql`SELECT d.status,d.payment_status,
  EXISTS(SELECT 1 FROM advertiser_campaign_draft_images i WHERE i.draft_id=d.id) AS has_image
  FROM advertiser_campaign_drafts d WHERE id=${id}`;
 if(!draft)throw new Error('Anuncio no encontrado');
 if(!['submitted','changes_requested'].includes(draft.status))
  throw new Error('Esta propuesta no está pendiente de revisión');
 if(decision==='approved_for_payment'&&!draft.has_image)
  throw new Error('La creatividad debe incluir una imagen antes de aprobar el contenido');
 if(draft.payment_status==='paid'||draft.payment_status==='refunded')
  throw new Error('Los pagos confirmados requieren un procedimiento específico');
 const [updated]=await sql`UPDATE advertiser_campaign_drafts SET status=${decision},
  review_note=${note||null},updated_at=now()
  WHERE id=${id} AND status IN ('submitted','changes_requested') RETURNING id,status,updated_at`;
 if(!updated)throw new Error('La propuesta ha cambiado de estado');
 let emailStatus='not_requested';
 if(decision==='changes_requested'){
  try{
   const workspace=await workspaceForDraft(sql,id);
   emailStatus=await notifyChangesSafely(workspace,note,updated.updated_at?.toISOString?.()||String(updated.updated_at));
  }catch(e){
   console.error('DParranda review notification failed:',e?.name||'Error');
   emailStatus='failed';
  }
 }
 const payment=decision==='approved_for_payment'?await safelyPreparePayment(sql,id):null;
 return {id:Number(updated.id),status:updated.status,
  notification_status:payment?.email_status||emailStatus,payment_enabled:payment?.status==='ready',
  message:decision==='approved_for_payment'
   ?paymentMessage(payment||{status:'failed'})
   :decision==='changes_requested'?changesMessage(emailStatus):'Anuncio rechazado. No se ha enviado ningún correo automático.'};
}


// Admin-authenticated test: saves the exact simulated creative without
// requiring public lead collection, fake consent, or Stripe configuration.
async function saveAdvertisingTestProposal(sql,body){
 const d=body?.campaign;
 if(!d||typeof d!=='object'||Array.isArray(d))throw new Error('Campaña de prueba inválida');
 const tariffs={local:19,zona:49,insular:99};
 const plan=safeText(d.plan,20),days=Number(d.days),kind=safeText(d.kind,20);
 const company=safeText(d.advertiser,120),title=safeText(d.title,160);
 const description=safeText(d.description,350),destination=safeText(d.destination,850);
 const campaignStart=safeText(d.start,10);
 const towns=Array.isArray(d.municipalities)?d.municipalities:[];
 const municipalities=[...new Set(towns)];
 const startDate=safeText(d.eventDate,25),venue=safeText(d.eventVenue,200),eventTown=safeText(d.eventTown,90);
 const image=typeof d.image_data==='string'?d.image_data:'';
 const validImage=/^data:image\/webp;base64,[A-Za-z0-9+/=]+$/.test(image)&&image.length<900000;
 const bytes=validImage?Buffer.from(image.slice(image.indexOf(',')+1),'base64'):null;
 let validURL=false;
 try{const u=new URL(destination);validURL=u.protocol==='https:'&&!u.username&&!u.password}catch{}
 if(!Object.hasOwn(tariffs,plan)||![30,60].includes(days)||!['banner','evento'].includes(kind)||
   !company||!title||description.length<12||!validURL||!validLocalDate(campaignStart)||
   !campaignStart||municipalities.length!==towns.length||
   (plan==='local'&&municipalities.length!==1)||
   (plan==='zona'&&(municipalities.length<1||municipalities.length>4))||
   (plan==='insular'&&municipalities.length!==0)||
   (kind==='evento'&&(!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(startDate)||!eventTown||!venue))||
   !bytes||bytes.length<800||bytes.length>620000||
   bytes.toString('ascii',0,4)!=='RIFF'||bytes.toString('ascii',8,12)!=='WEBP')
   throw new Error('Completa la campaña y adjunta una imagen WebP válida para enviarla de prueba');
 const amount=tariffs[plan]*(days/30);
 const zone=plan==='insular'?'Toda Gran Canaria':municipalities.join(', ');
 const details='PRUEBA_ADMIN|'+plan+'|'+amount+'|'+days+'|'+kind;
 const [quota]=await sql`SELECT count(*)::int AS count FROM advertising_enquiries
    WHERE dates_text LIKE 'PRUEBA_ADMIN|%' AND created_at>now()-interval '1 hour'`;
 if(quota.count>=12)throw new Error('Ya se han enviado demasiadas pruebas en una hora');
 const encoded=bytes.toString('base64');
 const [result]=await sql`WITH lead AS (
    INSERT INTO advertising_enquiries(company,contact_name,email,telephone,municipality,format,
     dates_text,message,campaign_name,campaign_start,campaign_days,event_title,event_start,
     event_venue,event_municipality,action_url,banner_text,creative_alt,
     status,review_status,payment_status)
    VALUES (${company},'Simulación del administrador','prueba@ejemplo.invalid','',${zone},
     ${kind==='banner'?'banner':'event'},${details},
     'PRUEBA DEL ADMINISTRADOR: no es una contratación ni se ha enviado ningún aviso al anunciante.',
     ${title},${campaignStart},${days},${kind==='evento'?title:null},
     ${kind==='evento'?startDate:null},${kind==='evento'?venue:null},
     ${kind==='evento'?eventTown:null},${destination},${description},${title},
     'new','submitted','unavailable')
    RETURNING id
   ) INSERT INTO advertising_enquiry_images(enquiry_id,mime_type,width,height,image_data)
   SELECT id,'image/webp',1000,563,decode(${encoded},'base64') FROM lead RETURNING enquiry_id`;
 return {received:true,request_id:Number(result.enquiry_id),test:true,
  message:'Campaña de prueba recibida en el panel, pendiente de revisión. Sin pago ni publicación.'};
}
export default async function handler(req,res){
  res.setHeader('Cache-Control','private, no-store, max-age=0');
  if(!['GET','POST'].includes(req.method))return json(res,405,{error:'Método no permitido'});
  const query=req.query||{};
  const op=String(query.op||'session');
  if(!isConfigured())return json(res,503,{configured:false,error:'Panel pendiente de activar: conexión o credenciales de administración no configuradas'});
  const sql=db();
  try {
    if(req.method==='POST' && !sameOrigin(req))return json(res,403,{error:'Origen de solicitud no autorizado'});
    if(req.method==='POST' && op==='login'){
      const pass=data(req).password;
      const correct=passwordValid(pass);
      const allowed=await attempt(sql,req,correct);
      if(!allowed)return json(res,429,{error:'Demasiados intentos. Inténtalo más tarde'});
      if(!correct)return json(res,401,{error:'Contraseña incorrecta'});
      setSession(res,true);
      return json(res,200,{authenticated:true});
    }
    if(req.method==='POST' && op==='logout'){
      setSession(res,false);return json(res,200,{authenticated:false});
    }
    if(op==='session')return json(res,200,{authenticated:authenticated(req),configured:true});
    if(!authenticated(req))return json(res,401,{error:'Acceso reservado al administrador'});
    if(req.method==='GET'&&op==='resend-test-config')
      return json(res,200,{...resendTestConfiguration(),sandbox_only:true,customer_emails_enabled:false});
    if(req.method==='POST'&&op==='resend-send-test'){
      const result=await sendResendAdminTest();
      return json(res,result.ok?200:503,result);
    }

    if(req.method==='POST'&&op==='advertising-test-proposal')
      return json(res,201,await saveAdvertisingTestProposal(sql,data(req)));
    if(req.method==='GET'&&op==='advertising-intake-config'){
      const privacy=!!privacyUrl();
      const leads=process.env.DPARRANDA_LEADS_ENABLED==='true';
      return json(res,200,{receiving_proposals:leads&&privacy&&!!process.env.DATABASE_URL,
       admin_test_enabled:true,leads_enabled:leads,privacy_configured:privacy,
       missing_legal_fields:missingPrivacyIdentity(),
       privacy_url:privacy?privacyUrl():null,database_configured:!!process.env.DATABASE_URL,
       advertising_mail:advertiserMailStatus(),accepting_payments:stripePaymentsReady()});
    }
    if(req.method==='GET'&&op==='advertiser-accounts')return json(res,200,await advertiserAccounts(sql));
    if(req.method==='GET'&&op==='advertiser-drafts')return json(res,200,await advertiserDrafts(sql));
    if(req.method==='GET'&&op==='advertiser-draft-image'){
      const id=invitedId(query.id);
      return id?advertiserDraftImage(sql,res,id):json(res,404,{error:'Imagen no encontrada'});
    }
    if(req.method==='POST'&&op==='advertiser-invite')return json(res,200,await advertiserInvite(sql,data(req),req));
    if(req.method==='POST'&&op==='advertiser-access')return json(res,200,await advertiserChangeAccess(sql,data(req)));
    if(req.method==='POST'&&op==='advertiser-review')return json(res,200,await advertiserReview(sql,data(req)));
    if(req.method==='POST'&&op==='paid-ad-status')
      return json(res,200,await setPaidPublicationEnabled(sql,data(req)));
    if(req.method==='POST'&&op==='edit-paid-creative')
      return json(res,200,await editPaidCreative(sql,data(req),adminImageData));
    if(req.method==='POST'&&op==='schedule-paid-draft'){
      const id=invitedId(data(req).id);
      if(!id)return json(res,400,{error:'Anuncio inválido'});
      return json(res,200,await schedulePaidDraft(sql,id));
    }
     if(req.method==='POST'&&op==='send-approved-payment'){
      const id=invitedId(data(req).id);
      if(!id)return json(res,400,{error:'Anuncio no válido'});
      const payment=await safelyPreparePayment(sql,id);
      return json(res,200,{...payment,message:paymentMessage(payment)});
     }
    if(req.method==='POST'&&op==='enquiry-review')return json(res,200,await reviewEnquiry(sql,data(req)));
    if(req.method==='GET'&&op==='leads')return json(res,200,await listLeads(sql));
    if(req.method==='GET'&&op==='promotions')return json(res,200,await listPromotions(sql));
    if(req.method==='GET'&&op==='leadimage'){
      const id=leadId(query.id);return id?await leadImage(sql,res,id):json(res,404,{error:'Imagen no encontrada'});
    }
    if(req.method==='GET'&&op==='adimage')return adminAdImage(sql,res,String(query.id||''));
    if(req.method==='POST'&&op==='promote')return json(res,200,await promoteLead(sql,data(req)));
    if(req.method==='POST'&&op==='promotion-status')return json(res,200,await changePromotion(sql,data(req)));
    if(req.method==='POST'&&op==='lead-status')return json(res,200,await changeLead(sql,data(req)));
    if(req.method==='GET'&&op==='stats'){
      const [s]=await sql`SELECT
        (SELECT count(*)::int FROM published_events WHERE active) AS events,
        (SELECT count(*)::int FROM event_overrides WHERE hidden) AS hidden,
        (SELECT count(*)::int FROM event_overrides WHERE review_status='needs_review') AS reviews,
        (SELECT count(*)::int FROM ad_campaigns WHERE enabled) AS active_ads,
        (SELECT count(*)::int FROM ad_campaigns) AS ads`;
      return json(res,200,s);
    }
    if(req.method==='GET'&&op==='events')return json(res,200,await events(sql,query));
    if(req.method==='GET'&&op==='ads'){
      const rows=await sql`SELECT id,enabled,advertiser,kind,permanent,starts_at,ends_at,
        municipalities,headline,description,location,button_text,button_url,image,image_alt,enquiry_id,
        disclosure, EXISTS(SELECT 1 FROM ad_campaign_images ai WHERE ai.ad_id=ad_campaigns.id)
        AS has_uploaded_image FROM ad_campaigns ORDER BY updated_at DESC,id LIMIT 250`;
      return json(res,200,{ads:rows});
    }
    if(req.method==='POST'&&op==='event')return json(res,200,await saveEvent(sql,data(req)));
    if(req.method==='POST'&&op==='visibility')return json(res,200,await setEventVisibility(sql,data(req)));
    if(req.method==='POST'&&op==='ad')return json(res,200,await saveAd(sql,data(req)));
    if(req.method==='POST'&&op==='house-ad-status')return json(res,200,await setHouseCampaignEnabled(sql,data(req)));
    return json(res,404,{error:'Operación desconocida'});
  }catch(err){
    if(err instanceof Error && /inválid|Indica |debe |No se encuentra|No puedes|no encontrado|Fechas/.test(err.message))
      return json(res,400,{error:err.message});
    console.error('DParranda admin request failed:',err?.name||'Error');
    return json(res,500,{error:'No se pudo completar la operación'});
  }
}
