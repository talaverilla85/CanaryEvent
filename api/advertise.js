import { db, json, safeText, sameOrigin } from '../lib/admin-auth.js';
const TYPES=new Set(['event','banner','combined','other']);
function enabled(){return process.env.DPARRANDA_LEADS_ENABLED==='true'&&!!process.env.DATABASE_URL&&!!process.env.DPARRANDA_PRIVACY_URL;}
function payload(req){return req.body&&typeof req.body==='object'?req.body:{};}
export default async function handler(req,res){
 res.setHeader('X-Robots-Tag','noindex,noarchive');
 if(req.method==='GET')return json(res,200,{enabled:enabled(),privacy_url:enabled()?process.env.DPARRANDA_PRIVACY_URL:null});
 if(req.method!=='POST')return json(res,405,{error:'Método no permitido'});
 if(!enabled())return json(res,503,{error:'Las solicitudes online todavía no están activadas. Puedes consultar los formatos y volver a intentarlo más adelante.'});
 if(!sameOrigin(req))return json(res,403,{error:'Solicitud no autorizada'});
 try{
  const x=payload(req);
  if(x.website)return json(res,200,{received:true});
  const company=safeText(x.company,120),contact=safeText(x.contact,100),email=safeText(x.email,180).toLowerCase();
  const municipality=safeText(x.municipality,100),format=safeText(x.format,20);
  const dates=safeText(x.dates,100),message=safeText(x.message,1500);
  if(!company||!contact||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||!TYPES.has(format)||message.length<15||x.consent!==true)
    return json(res,400,{error:'Comprueba los datos y acepta el aviso de privacidad'});
  const sql=db();
  const [n]=await sql`SELECT count(*)::int AS c FROM advertising_enquiries
    WHERE lower(email)=${email} AND created_at>now()-interval '30 minutes'`;
  if(n.c>=2)return json(res,429,{error:'Has enviado varias consultas recientemente. Prueba más tarde.'});
  await sql`INSERT INTO advertising_enquiries(company,contact_name,email,municipality,format,dates_text,message)
    VALUES(${company},${contact},${email},${municipality},${format},${dates},${message})`;
  return json(res,201,{received:true});
 }catch(e){console.error('Advertising enquiry database unavailable:',e?.name||'Error');return json(res,503,{error:'No podemos registrar solicitudes en este momento.'});}
}