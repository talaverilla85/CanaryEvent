// Private per-advertiser workspace. No paid checkout or publication here.
import {createHmac,createHash,timingSafeEqual} from 'node:crypto';
import {db,json,sameOrigin,safeText,validLocalDate} from '../lib/admin-auth.js';
import {privacyUrl as legalPrivacyUrl} from '../lib/privacy.js';
import {advertiserPortalReady} from '../lib/advertiser-workspace.js';
import {parseEmailAccessToken} from '../lib/advertiser-mail.js';
import {stripePaymentsReady} from '../lib/stripe-advertising.js';
const PLANS={local:1900,zona:4900,insular:9900};
const TOWNS=new Set(['Agaete','Agüimes','Artenara','Arucas','Firgas','Gáldar','Ingenio','La Aldea de San Nicolás','Las Palmas de Gran Canaria','Mogán','Moya','San Bartolomé de Tirajana','Santa Brígida','Santa Lucía de Tirajana','Santa María de Guía de Gran Canaria','Tejeda','Telde','Teror','Valleseco','Valsequillo de Gran Canaria','Vega de San Mateo']);
const AGE=30*24*60*60;
function privacy(){return legalPrivacyUrl()}
function ready(){return advertiserPortalReady()&&!!privacy()}
function mac(x){return createHmac('sha256',process.env.DPARRANDA_SESSION_SECRET).update(x).digest('base64url')}
function setCookie(res,x){res.setHeader('Set-Cookie','dp_advertiser='+x+'; HttpOnly; Secure; SameSite=Strict; Path=/api/advertiser; Max-Age='+(x?AGE:0))}
function decoded(req){
 const m=String(req.headers.cookie||'').match(/(?:^|;\s*)dp_advertiser=([^;]+)/),t=(m?.[1]||'').split('.');
 if(t.length!==2||t[0].length>500||!/^[A-Za-z0-9_-]+$/.test(t[0]))return null;
 const expected=mac(t[0]);
 if(t[1].length!==expected.length||!timingSafeEqual(Buffer.from(t[1]),Buffer.from(expected)))return null;
 try{const p=JSON.parse(Buffer.from(t[0],'base64url').toString('utf8'));
 return Number.isSafeInteger(p.id)&&p.id>0&&Number.isInteger(p.v)&&p.v>0&&typeof p.exp==='number'&&p.exp>Date.now()&&p.exp<Date.now()+AGE*1000+60000?p:null}catch{return null}
}
async function viewer(sql,req){
 const s=decoded(req);if(!s)return null;
 const [a]=await sql`SELECT id,company,contact_name,email,access_version FROM advertiser_accounts WHERE id=${s.id} AND access_version=${s.v} AND active=TRUE`;
 return a||null;
}
function today(){const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date()).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));return p.year+'-'+p.month+'-'+p.day}
function link(x){try{const u=new URL(safeText(x,850));return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}}
function img(x){
 if(typeof x!=='string'||x.length>1150000||!/^data:image\/webp;base64,[A-Za-z0-9+/=]+$/.test(x))return null;
 const b=Buffer.from(x.split(',')[1],'base64');
 return b.length>=800&&b.length<=800000&&b.toString('ascii',0,4)==='RIFF'&&b.toString('ascii',8,12)==='WEBP'?b.toString('base64'):null;
}
function clean(x){
 const plan=safeText(x.plan,20),days=Number(x.days),placement=safeText(x.placement,20),towns=Array.isArray(x.municipalities)?x.municipalities:[];
 const municipalities=[...new Set(towns)],advertiser=safeText(x.advertiser,120),title=safeText(x.title,160),description=safeText(x.description,350);
 const destination=link(x.destination),start=safeText(x.campaign_start,10),imageAlt=safeText(x.image_alt,160);
 const eventStart=safeText(x.event_start,25),eventTown=safeText(x.event_town,90),eventVenue=safeText(x.event_venue,200);
 const image=x.image_data?img(x.image_data):null;
 if(!Object.hasOwn(PLANS,plan)||![30,60].includes(days)||!['banner','evento'].includes(placement)||!advertiser||!title||description.length<12||!destination||
 towns.length!==municipalities.length||towns.length>4||municipalities.some(t=>typeof t!=='string'||!TOWNS.has(t))||
 (plan==='local'&&municipalities.length!==1)||(plan==='zona'&&(municipalities.length<1||municipalities.length>4))||(plan==='insular'&&municipalities.length!==0)||
 (start&&(!validLocalDate(start)||start<today()))||(x.image_data&&!image)||
 (placement==='evento'&&(!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(eventStart)||!TOWNS.has(eventTown)||!eventVenue||
     eventStart.slice(0,10)<today()||(start&&eventStart.slice(0,10)<start))))return null;
 return {plan,days,placement,municipalities,advertiser,title,description,destination,start,imageAlt,
 eventStart:placement==='evento'?eventStart:null,eventTown:placement==='evento'?eventTown:null,
 eventVenue:placement==='evento'?eventVenue:null,price:PLANS[plan]*(days/30),image};
}
const positive=x=>{const n=Number(x);return Number.isSafeInteger(n)&&n>0?n:null};
export default async function handler(req,res){
 res.setHeader('X-Robots-Tag','noindex,noarchive');
 if(!['GET','POST'].includes(req.method))return json(res,405,{error:'Método no permitido'});
 const op=String(req.query?.op||'session');
 if(req.method==='GET'&&op==='config')return json(res,200,{enabled:ready(),payment_enabled:stripePaymentsReady(),privacy_url:privacy()});
 if(!ready())return json(res,503,{error:'El área de anunciantes está pendiente de activación'});
 if(req.method==='POST'&&!sameOrigin(req))return json(res,403,{error:'Origen no autorizado'});
 const sql=db();
 try{
 if(req.method==='POST'&&op==='exchange'){
  const t=safeText(req.body?.token,180);
  const fromEmail=parseEmailAccessToken(t);
  let a=null;
  if(fromEmail){
   [a]=await sql`SELECT id,access_version FROM advertiser_accounts WHERE id=${fromEmail.id} AND access_version=${fromEmail.version} AND active=TRUE`;
  }else if(/^[0-9a-f]{64}$/i.test(t)){
   const hash=createHash('sha256').update(t.toLowerCase()).digest('hex');
   [a]=await sql`SELECT id,access_version FROM advertiser_accounts WHERE token_hash=${hash} AND active=TRUE`;
  }
  if(!a)return json(res,401,{error:'Enlace no válido, caducado o revocado'});
  const payload=Buffer.from(JSON.stringify({id:Number(a.id),v:a.access_version,exp:Date.now()+AGE*1000})).toString('base64url');
  setCookie(res,payload+'.'+mac(payload));return json(res,200,{authenticated:true});
 }
 if(req.method==='POST'&&op==='logout'){setCookie(res,'');return json(res,200,{authenticated:false})}
 const a=await viewer(sql,req);
 if(req.method==='GET'&&op==='session')return json(res,200,{authenticated:!!a,account:a?{company:a.company,contact_name:a.contact_name,email:a.email}:null,payment_enabled:stripePaymentsReady()});
 if(!a)return json(res,401,{error:'Acceso de anunciante no autorizado'});
 if(req.method==='GET'&&op==='campaigns'){
  const rows=await sql`SELECT d.*,
  CASE WHEN d.published_event_id IS NOT NULL THEN
    (SELECT s.enabled FROM sponsored_events s WHERE s.id=d.published_event_id AND s.advertiser_draft_id=d.id)
  WHEN d.published_ad_id IS NOT NULL THEN
    (SELECT ac.enabled FROM ad_campaigns ac WHERE ac.id=d.published_ad_id)
  ELSE NULL END AS published_enabled,
  EXISTS(SELECT 1 FROM advertiser_campaign_draft_images i WHERE i.draft_id=d.id) AS has_image
  FROM advertiser_campaign_drafts d WHERE d.advertiser_id=${a.id}
   AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=d.id::text)
  ORDER BY d.created_at DESC LIMIT 100`;
  return json(res,200,{campaigns:rows.map(d=>({id:Number(d.id),plan:d.plan,days:d.days,price_cents:d.price_cents,municipalities:d.municipalities,
  placement:d.placement,advertiser:d.advertiser,title:d.title,description:d.description,destination:d.destination,image_alt:d.image_alt,
  campaign_start:d.campaign_start,event_start:d.event_start,event_town:d.event_town,event_venue:d.event_venue,
  status:d.status,payment_status:d.payment_status,published_enabled:d.published_enabled,
  payment_url:d.status==='pending_payment'&&d.payment_status==='pending'&&/^https:\/\/buy\.stripe\.com\//.test(d.stripe_payment_url||'')?d.stripe_payment_url:null,
  actual_starts_at:d.actual_starts_at,actual_ends_at:d.actual_ends_at,
  review_note:d.review_note,has_image:d.has_image,stats_available:false,created_at:d.created_at,updated_at:d.updated_at})),payment_enabled:stripePaymentsReady()});
 }
 if(req.method==='GET'&&op==='artwork'){
  const id=positive(req.query?.id);if(!id)return json(res,404,{error:'No encontrado'});
  const [r]=await sql`SELECT i.mime_type,i.image_data FROM advertiser_campaign_draft_images i JOIN advertiser_campaign_drafts d ON d.id=i.draft_id WHERE d.id=${id} AND d.advertiser_id=${a.id} AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=d.id::text)`;
  if(!r)return json(res,404,{error:'Imagen no encontrada'});
  const bytes=typeof r.image_data==='string'?Buffer.from(r.image_data.replace(/^\\x/,''),'hex'):Buffer.from(r.image_data);
  res.setHeader('Content-Type',r.mime_type);res.setHeader('Content-Disposition','inline');
  res.setHeader('Cache-Control','private, no-store');res.setHeader('X-Content-Type-Options','nosniff');
  return res.status(200).end(bytes);
 }
 if(req.method==='POST'&&op==='submit'){
  const id=positive(req.body?.id);
  if(!id)return json(res,400,{error:'Selecciona un borrador válido'});
  const [draft]=await sql`SELECT d.id,d.status,d.campaign_start,
    EXISTS(SELECT 1 FROM advertiser_campaign_draft_images i WHERE i.draft_id=d.id) AS has_image
    FROM advertiser_campaign_drafts d WHERE d.id=${id} AND d.advertiser_id=${a.id} AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=d.id::text)`;
  if(!draft)return json(res,404,{error:'Anuncio no encontrado'});
  if(!['draft','changes_requested'].includes(draft.status))
    return json(res,409,{error:'La campaña ya está en revisión o no admite modificaciones'});
  if(!draft.has_image)return json(res,400,{error:'Añade una imagen antes de solicitar la revisión'});
  if(!draft.campaign_start)return json(res,400,{error:'Indica cuándo quieres comenzar la campaña'});
  const [done]=await sql`UPDATE advertiser_campaign_drafts SET status='submitted',
     review_note=NULL,updated_at=now()
     WHERE id=${id} AND advertiser_id=${a.id} AND status IN ('draft','changes_requested')
      AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=advertiser_campaign_drafts.id::text)
     RETURNING id`;
  return done?json(res,200,{submitted:true,id:Number(done.id),payment_enabled:false})
    :json(res,409,{error:'La campaña ha cambiado de estado'});
 }
 if(req.method==='POST'&&op==='save'){
  if(req.body?.consent!==true)return json(res,400,{error:'Debes aceptar el aviso de privacidad'});
  const x=clean(req.body||{});if(!x)return json(res,400,{error:'Revisa los datos de la campaña'});
  const idIn=req.body?.id?positive(req.body.id):null;
  if(req.body?.id&&!idIn)return json(res,400,{error:'Borrador no válido'});
  let id=idIn;
  if(id){
   const [r]=await sql`UPDATE advertiser_campaign_drafts SET plan=${x.plan},days=${x.days},price_cents=${x.price},
    municipalities=${JSON.stringify(x.municipalities)}::jsonb,placement=${x.placement},advertiser=${x.advertiser},title=${x.title},
    description=${x.description},destination=${x.destination},image_alt=${x.imageAlt},campaign_start=${x.start||null},
    event_start=${x.eventStart},event_town=${x.eventTown},event_venue=${x.eventVenue},status='draft',updated_at=now()
    WHERE id=${id} AND advertiser_id=${a.id} AND status IN ('draft','changes_requested')
      AND NOT EXISTS(SELECT 1 FROM advertising_archives ar WHERE ar.source='draft' AND ar.record_id=advertiser_campaign_drafts.id::text)
     RETURNING id`;
   if(!r)return json(res,409,{error:'Este anuncio ya no puede editarse'});
  }else{
   const [cnt]=await sql`SELECT count(*)::int AS count FROM advertiser_campaign_drafts WHERE advertiser_id=${a.id}`;
   if(cnt.count>=50)return json(res,429,{error:'Límite de borradores alcanzado'});
   const [r]=await sql`INSERT INTO advertiser_campaign_drafts
    (advertiser_id,plan,days,price_cents,municipalities,placement,advertiser,title,description,destination,image_alt,campaign_start,event_start,event_town,event_venue)
    VALUES(${a.id},${x.plan},${x.days},${x.price},${JSON.stringify(x.municipalities)}::jsonb,${x.placement},
    ${x.advertiser},${x.title},${x.description},${x.destination},${x.imageAlt},${x.start||null},${x.eventStart},${x.eventTown},${x.eventVenue}) RETURNING id`;
   id=Number(r.id);
  }
  if(x.image)await sql`INSERT INTO advertiser_campaign_draft_images(draft_id,mime_type,width,height,image_data) VALUES(${id},'image/webp',1200,675,decode(${x.image},'base64'))
   ON CONFLICT(draft_id) DO UPDATE SET image_data=excluded.image_data,
    width=excluded.width,height=excluded.height,mime_type=excluded.mime_type,updated_at=now()`;
  return json(res,200,{saved:true,id:Number(id),status:'draft',payment_enabled:false});
 }
 return json(res,404,{error:'Operación desconocida'});
 }catch(err){console.error('Private advertiser workspace:',err?.name||'Error');return json(res,503,{error:'No se pudo completar la operación'})}
}
