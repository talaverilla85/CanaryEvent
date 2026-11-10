// Minimal, non-binding commercial interest. No payment, invoice details, or ad publication.
import { db, json, safeText, sameOrigin, validLocalDate } from '../lib/admin-auth.js';

const PRICES=Object.freeze({local:19,zona:49,insular:99});
const TOWNS=new Set([
 'Agaete','Agüimes','Artenara','Arucas','Firgas','Gáldar','Ingenio',
 'La Aldea de San Nicolás','Las Palmas de Gran Canaria','Mogán','Moya',
 'San Bartolomé de Tirajana','Santa Brígida','Santa Lucía de Tirajana',
 'Santa María de Guía de Gran Canaria','Tejeda','Telde','Teror','Valleseco',
 'Valsequillo de Gran Canaria','Vega de San Mateo'
]);
const emailAddress=v=>{
 const text=safeText(v,180).toLowerCase();
 return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)?text:'';
};
function privacyUrl(){
 try{
  const url=new URL(process.env.DPARRANDA_PRIVACY_URL||'');
  return url.protocol==='https:'&&!url.username&&!url.password?url.href:null;
 }catch{return null}
}
function enabled(){return process.env.DPARRANDA_LEADS_ENABLED==='true'&&
 !!process.env.DATABASE_URL&&!!privacyUrl();}
// A review request uses the same privacy/legal intake as a simple enquiry.
// No separate proposal switch: once requests are enabled, a simulated ad can be submitted.
const proposalEnabled=()=>enabled();
function creative(value){
 if(typeof value!=='string'||value.length>900000||!/^data:image\/webp;base64,[A-Za-z0-9+/=]+$/.test(value))return null;
 const b=Buffer.from(value.slice(value.indexOf(',')+1),'base64');
 return b.length>=800&&b.length<=620000&&b.toString('ascii',0,4)==='RIFF'&&
 b.toString('ascii',8,12)==='WEBP'?b.toString('base64'):null;
}
function todayCanary(){
 const pieces=new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
 const parts=Object.fromEntries(pieces.filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
 return parts.year+'-'+parts.month+'-'+parts.day;
}
const asUrl=v=>{
 try{const url=new URL(safeText(v,850));return url.protocol==='https:'&&!url.username&&!url.password?url.href:''}
 catch{return ''}
};
export default async function handler(req,res){
 res.setHeader('X-Robots-Tag','noindex,noarchive');
 if(req.method==='GET')return json(res,200,{
  enabled:enabled(),privacy_url:privacyUrl(),payment_enabled:false,
  informational_only:true,proposal_enabled:proposalEnabled()
 });
 if(req.method!=='POST')return json(res,405,{error:'Método no permitido'});
 if(!enabled())return json(res,503,{error:'El registro de interesados aún no está disponible'});
 if(!sameOrigin(req))return json(res,403,{error:'Solicitud no autorizada'});
 try{
  const input=req.body&&typeof req.body==='object'&&!Array.isArray(req.body)?req.body:{};
  // A hidden honeypot deters unsophisticated automated spam.
  if(input.website)return json(res,202,{received:true});
  const proposal=input.proposal===true;
  if(proposal&&!proposalEnabled())return json(res,503,{error:'La presentación de propuestas aún está cerrada'});
  const draft=input.campaign&&typeof input.campaign==='object'&&!Array.isArray(input.campaign)?input.campaign:{};
  const company=safeText(input.company,120),contact=safeText(input.contact,100);
  const email=emailAddress(input.email),phone=safeText(input.telephone,35);
  const plan=safeText(draft.plan,20),kind=safeText(draft.kind,20),days=Number(draft.days);
  const places=Array.isArray(draft.municipalities)?draft.municipalities:[];
  const area=[...new Set(places)];
  const start=safeText(draft.start,10),title=safeText(draft.title,160);
  const link=asUrl(draft.destination);
  const description=safeText(draft.description,350);
  const image=proposal?creative(draft.image_data):null;
  const eventDate=safeText(draft.eventDate,25);
  const eventTown=safeText(draft.eventTown,90),eventVenue=safeText(draft.eventVenue,200);
  const amount=PRICES[plan]*(days/30);
  const chosen=(plan==='insular'?'Toda Gran Canaria':area.join(', '));
  if(!company||!contact||!email||phone.length>35||input.consent!==true||
     !Object.hasOwn(PRICES,plan)||!['banner','evento'].includes(kind)||
     ![30,60].includes(days)||!title||!link||
     places.length>4||area.some(t=>typeof t!=='string'||!TOWNS.has(t))||
     (plan==='local'&&area.length!==1)||
     (plan==='zona'&&(area.length<1||area.length>4))||
     (plan==='insular'&&area.length!==0)||
     (start!==''&&(!validLocalDate(start)||start<todayCanary()))||
     (proposal&&(!start||description.length<12||!image||
       (kind==='evento'&&(!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(eventDate)||!TOWNS.has(eventTown)||!eventVenue)))))
    return json(res,400,{error:'Revisa el contacto y la campaña seleccionada'});
  const sql=db();
  if(!sql)return json(res,503,{error:'El registro de interesados no está disponible'});
  const [limits]=await sql`SELECT
   count(*) FILTER (WHERE lower(email)=${email} AND created_at>now()-interval '1 day')::int AS email_count,
   count(*) FILTER (WHERE created_at>now()-interval '1 hour')::int AS hourly_count
   FROM advertising_enquiries WHERE created_at>now()-interval '1 day'`;
  if(limits.email_count>=2||limits.hourly_count>=80)
   return json(res,429,{error:'Hemos recibido demasiadas solicitudes. Inténtalo más tarde'});
  // INTERES_INICIAL is an explicit tag for the separate Telegram monitor.
  // Existing admin leads and full billing proposals remain compatible.
  const label=plan==='local'?'Local':plan==='zona'?'Zona':'Insular';
  const details='INTERES_INICIAL|'+plan+'|'+amount+'|'+days+'|'+kind;
  const summary='Interés comercial sin compromiso. '+label+' · '+days+
   ' días · '+amount+' € · '+chosen+' · '+(kind==='banner'?'Banner':'Evento patrocinado')+
   '. Campaña: '+title;
  if(proposal){
   // One atomic query: both the application and its verified image are stored.
   const [row]=await sql`WITH new_proposal AS (
     INSERT INTO advertising_enquiries
      (company,contact_name,email,telephone,municipality,format,dates_text,message,
       campaign_name,campaign_start,campaign_days,event_title,event_start,event_venue,
       event_municipality,action_url,banner_text,creative_alt,privacy_accepted_at,status,review_status)
     VALUES (${company},${contact},${email},${phone},${chosen},${kind==='banner'?'banner':'event'},
       ${details},${summary+' · Texto: '+description},${title},${start},${days},
       ${kind==='evento'?title:null},${kind==='evento'?eventDate:null},
       ${kind==='evento'?eventVenue:null},${kind==='evento'?eventTown:null},${link},
       ${description},${title},now(),'new','submitted')
     RETURNING id
    ) INSERT INTO advertising_enquiry_images(enquiry_id,mime_type,width,height,image_data)
      SELECT id,'image/webp',1000,563,decode(${image},'base64') FROM new_proposal
      RETURNING enquiry_id`;
   return json(res,201,{received:true,request_id:Number(row.enquiry_id),
     proposal:true,payment_required:false});
  }
  const [saved]=await sql`INSERT INTO advertising_enquiries
   (company,contact_name,email,telephone,municipality,format,dates_text,message,
    campaign_name,campaign_start,campaign_days,event_title,event_start,event_venue,
    event_municipality,action_url,privacy_accepted_at,status)
   VALUES (${company},${contact},${email},${phone},${chosen},${kind==='banner'?'banner':'event'},
    ${details},${summary},${title},${start||null},${days},
    ${kind==='evento'?title:null},${kind==='evento'?safeText(draft.eventDate,25):null},
    ${kind==='evento'?safeText(draft.eventVenue,200):null},
    ${kind==='evento'?safeText(draft.eventTown,90):null},${link},now(),'new')
   RETURNING id`;
  return json(res,201,{received:true,request_id:Number(saved.id),payment_required:false});
 }catch(err){
  console.error('DParranda interest registration error:',err?.name||'Error');
  return json(res,503,{error:'No se ha podido registrar el interés. Prueba de nuevo'});
 }
}
