import { db, json, safeText, sameOrigin, validLocalDate } from '../lib/admin-auth.js';
const TYPES=new Set(['event','banner','combined','other']);
const CATS=new Set(['musica','familia','gastronomia','cultura','deporte','naturaleza','ocio','otros']);
const enabled=()=>process.env.DPARRANDA_LEADS_ENABLED==='true'&&!!process.env.DATABASE_URL&&!!process.env.DPARRANDA_PRIVACY_URL;
const email=x=>{const v=safeText(x,180).toLowerCase();return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)?v:''};
const url=x=>{try{const u=new URL(safeText(x,850));return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}};
function imageCheck(input){
 if(typeof input!=='string'||!/^data:image\/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+$/.test(input)||input.length>1150000)return null;
 const comma=input.indexOf(','),mime=input.slice(5,comma-7),b64=input.slice(comma+1),bin=Buffer.from(b64,'base64');
 if(bin.length<1000||bin.length>800000)return null;
 const ok=mime==='image/jpeg'?bin.subarray(0,3).toString('hex')==='ffd8ff':
  mime==='image/png'?bin.subarray(0,8).toString('hex')==='89504e470d0a1a0a':
  mime==='image/webp'&&bin.toString('ascii',0,4)==='RIFF'&&bin.toString('ascii',8,12)==='WEBP';
 return ok?{mime,b64}:null;
}
export default async function handler(req,res){
 res.setHeader('X-Robots-Tag','noindex,noarchive');
 if(req.method==='GET')return json(res,200,{enabled:enabled(),privacy_url:enabled()?process.env.DPARRANDA_PRIVACY_URL:null,image_max_kb:800,creative_ratio:'16:9'});
 if(req.method!=='POST')return json(res,405,{error:'Método no permitido'});
 if(!enabled())return json(res,503,{error:'La recepción de solicitudes está pendiente de activar con el aviso de privacidad'});
 if(!sameOrigin(req))return json(res,403,{error:'Solicitud no autorizada'});
 try{
  const x=req.body && typeof req.body==='object' && !Array.isArray(req.body) ? req.body : {};
  if(x.website)return json(res,200,{received:true});
  const company=safeText(x.company,120),contact=safeText(x.contact,100),mail=email(x.email),phone=safeText(x.telephone,35);
  const billingType=safeText(x.billing_type,20),legal=safeText(x.legal_name,180),tax=safeText(x.tax_id,35);
  const address=safeText(x.billing_address,220),postal=safeText(x.billing_postal,20),city=safeText(x.billing_city,110);
  const province=safeText(x.billing_region,110),country=safeText(x.billing_country,90),invoiceEmail=email(x.billing_email);
  const format=safeText(x.format,20),municipality=safeText(x.municipality,180);
  const campaign=safeText(x.campaign_name,180),start=safeText(x.campaign_start,10),days=Number(x.campaign_days);
  const eventTitle=safeText(x.event_title,200),eventStart=safeText(x.event_start,25),eventEnd=safeText(x.event_end,25);
  const eventMunicipality=safeText(x.event_municipality,90),venue=safeText(x.event_venue,230),category=safeText(x.category,50),price=safeText(x.event_price,110);
  const description=safeText(x.message,2500),banner=safeText(x.banner_text,240);
  const link=url(x.action_url),alt=safeText(x.creative_alt,180),notes=safeText(x.notes,900);
  const fileName=safeText(x.image_name,160),image=imageCheck(x.image_data);
  if(!company||!contact||!mail||!phone||!['individual','company'].includes(billingType)||
     !legal||!tax||!address||!postal||!city||!province||!country||!invoiceEmail||
     !TYPES.has(format)||!municipality||!campaign||!validLocalDate(start)||start===''||
     !Number.isInteger(days)||days<1||days>90||!link||description.length<15||!alt||!image||
     Number(x.image_width)!==1200||Number(x.image_height)!==675||x.consent!==true)
     return json(res,400,{error:'Comprueba los datos de contacto, facturación, campaña e imagen'});
  if(['event','combined'].includes(format)&&(
    !eventTitle||!eventMunicipality||!venue||!CATS.has(category)||!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(eventStart)||
    (eventEnd && (!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(eventEnd)||eventEnd<eventStart))))
    return json(res,400,{error:'El evento necesita título, fecha, recinto y categoría válidos'});
  const sql=db();
  const [previous]=await sql`SELECT count(*)::int AS count FROM advertising_enquiries
    WHERE lower(email)=${mail} AND created_at>now()-interval '30 minutes'`;
  if(previous.count>=2)return json(res,429,{error:'Ya hemos recibido varias solicitudes. Prueba más tarde'});
  // Single SQL statement: invoice/contact details and artwork are inserted atomically.
  const [saved]=await sql`WITH lead AS (
    INSERT INTO advertising_enquiries
    (company,contact_name,email,municipality,format,dates_text,message,
     billing_type,legal_name,tax_id,billing_address,billing_postal,billing_city,billing_region,billing_country,
     billing_email,telephone,campaign_name,campaign_start,campaign_days,category,event_start,event_end,
     event_venue,event_price,event_title,event_municipality,action_url,banner_text,creative_alt,image_name,privacy_accepted_at)
    VALUES (${company},${contact},${mail},${municipality},${format},${notes},${description},
      ${billingType},${legal},${tax},${address},${postal},${city},${province},${country},
      ${invoiceEmail},${phone},${campaign},${start},${days},${category},${eventStart},${eventEnd},
      ${venue},${price},${eventTitle},${eventMunicipality},${link},${banner},${alt},${fileName},now())
    RETURNING id
  ) INSERT INTO advertising_enquiry_images(enquiry_id,mime_type,width,height,image_data)
    SELECT lead.id,${image.mime},1200,675,decode(${image.b64},'base64') FROM lead
    RETURNING enquiry_id`;
  return json(res,201,{received:true,request_id:Number(saved.enquiry_id)});
 }catch(e){
  console.error('Advertising enquiry persistence failed:',e?.name||'Error');
  return json(res,503,{error:'No podemos registrar la solicitud en este momento'});
 }
}