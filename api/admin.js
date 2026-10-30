import { createHmac, randomUUID } from 'node:crypto';
import { authenticated, db, isConfigured, json, passwordValid, safeText, sameOrigin, setSession, validLocalDate } from '../lib/admin-auth.js';

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
    EXISTS(SELECT 1 FROM published_events r WHERE r.active AND r.id<>p.id
        AND r.payload->>'municipality'=p.payload->>'municipality'
        AND left(r.payload->>'start',10)=left(p.payload->>'start',10)
        AND regexp_replace(lower(r.payload->>'title'),'[^[:alnum:]]','','g')
             =regexp_replace(lower(p.payload->>'title'),'[^[:alnum:]]','','g')) AS possible_duplicate
    FROM published_events p
    LEFT JOIN event_overrides o ON o.event_id=p.id
    WHERE p.active AND
      (${q}='' OR p.payload->>'title' ILIKE '%'||${q}||'%' OR p.payload->>'municipality' ILIKE '%'||${q}||'%')
    ORDER BY p.payload->>'start' ASC,p.id
    LIMIT 100 OFFSET ${offset}`;
  const filtered = rows.filter(r => only==='all' || (only==='duplicates' ? r.possible_duplicate : only==='review' ? (r.review_status==='needs_review'||r.review_status==='unreviewed'||r.possible_duplicate) : true));
  return {events:filtered.slice(0,60),has_more:rows.length===100,offset,next_offset:offset+100};
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
  if(!validLocalDate(starts)||!validLocalDate(ends)||starts&&ends&&starts>ends)
    throw new Error('Fechas inválidas');
  const kind=kinds.has(body.kind)?body.kind:'paid';
  const municipalities=Array.isArray(body.municipalities)?
    [...new Set(body.municipalities.filter(x=>typeof x==='string').map(x=>safeText(x,75)).filter(Boolean))].slice(0,25):[];
  const enabled=body.enabled===true,permanent=body.permanent===true;
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
  return {id,updated:true};
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
        municipalities,headline,description,location,button_text,button_url,image,image_alt,
        disclosure FROM ad_campaigns ORDER BY updated_at DESC,id LIMIT 250`;
      return json(res,200,{ads:rows});
    }
    if(req.method==='POST'&&op==='event')return json(res,200,await saveEvent(sql,data(req)));
    if(req.method==='POST'&&op==='ad')return json(res,200,await saveAd(sql,data(req)));
    return json(res,404,{error:'Operación desconocida'});
  }catch(err){
    if(err instanceof Error && /inválid|Indica |debe |No se encuentra|No puedes|no encontrado|Fechas/.test(err.message))
      return json(res,400,{error:err.message});
    console.error('DParranda admin request failed:',err?.name||'Error');
    return json(res,500,{error:'No se pudo completar la operación'});
  }
}
