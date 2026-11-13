// Transactional advertiser notifications. Without a verified domain,
// only emails to the exact Resend sandbox test recipient are permitted.
import {createHmac,timingSafeEqual} from 'node:crypto';
import {advertiserPortalReady} from './advertiser-workspace.js';

const SECRET=()=>process.env.DPARRANDA_SESSION_SECRET||'';
const EMAIL=/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;
const SENDER=()=>String(process.env.RESEND_FROM_EMAIL||'').trim();
const esc=s=>String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const active=()=>!!(advertiserPortalReady()&&process.env.RESEND_CUSTOMER_EMAILS_ENABLED==='true'&&
 process.env.RESEND_API_KEY?.startsWith('re_')&&EMAIL.test(SENDER())&&
 !/@resend\.dev$/i.test(SENDER()));
const sandboxRecipient=()=>String(process.env.RESEND_TEST_RECIPIENT||'').trim().toLowerCase();
const sandboxAllowed=to=>!!(advertiserPortalReady()&&
 process.env.RESEND_API_KEY?.startsWith('re_')&&EMAIL.test(sandboxRecipient())&&
 String(to||'').trim().toLowerCase()===sandboxRecipient());
const canSendTo=to=>active()||sandboxAllowed(to);
export function advertiserMailStatus(){
 return {enabled:active(),domain_pending:!active(),sandbox_test_only:!active()};
}
const digest=payload=>createHmac('sha256',SECRET()).update('dparranda-advertiser-email-v1:'+payload).digest('hex');
export function createEmailAccessToken(account){
 if(!advertiserPortalReady()||!Number.isSafeInteger(Number(account?.id))||
 !Number.isSafeInteger(Number(account?.access_version)))return null;
 const until=Math.floor(Date.now()/1000)+30*24*60*60;
 const payload=[Number(account.id),Number(account.access_version),until].join('.');
 return 'mail.'+payload+'.'+digest(payload);
}
export function parseEmailAccessToken(token){
 if(!advertiserPortalReady()||typeof token!=='string')return null;
 const match=/^mail\.([1-9]\d{0,14})\.([1-9]\d{0,9})\.(\d{10})\.([0-9a-f]{64})$/.exec(token);
 if(!match)return null;
 const id=Number(match[1]),version=Number(match[2]),expires=Number(match[3]);
 if(!Number.isSafeInteger(id)||!Number.isSafeInteger(version)||
 expires<=Math.floor(Date.now()/1000)||expires>Math.floor(Date.now()/1000)+30*24*60*60+60)return null;
 const payload=[id,version,expires].join('.');
 const expected=digest(payload);
 if(!timingSafeEqual(Buffer.from(expected,'hex'),Buffer.from(match[4],'hex')))return null;
 return {id,version};
}
function accessLink(account){
 const token=createEmailAccessToken(account);
 return token?'https://dparranda.es/anunciantes/#acceso='+token:null;
}
async function dispatch({to,subject,html,text,idempotencyKey}){
 if(!EMAIL.test(String(to||'')))return {status:'invalid_recipient'};
 if(!canSendTo(to))return {status:'pending_domain'};
 const sender=active()?SENDER():'onboarding@resend.dev';
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),9000);
 try{
  const r=await fetch('https://api.resend.com/emails',{method:'POST',signal:controller.signal,
   headers:{'Authorization':'Bearer '+process.env.RESEND_API_KEY,
    'Content-Type':'application/json','Idempotency-Key':idempotencyKey.slice(0,220)},
   body:JSON.stringify({from:'DParranda <'+sender+'>',to:[to],
    subject,html,text})});
  if(!r.ok){console.error('DParranda transactional email rejected',r.status);return {status:'failed'}}
  const answer=await r.json();
  return typeof answer?.id==='string'&&answer.id?{status:'sent'}:{status:'failed'};
 }catch(e){console.error('DParranda transactional email unavailable',e?.name||'Error');return {status:'failed'}}
 finally{clearTimeout(timeout)}
}
function layout(title,body,url,cta,foot='Este correo se ha enviado porque se ha solicitado gestionar una campaña publicitaria de DParranda. No se ha realizado ningún cobro ni se ha publicado el anuncio.'){
 const safe=esc(url);
 return '<!doctype html><html lang="es"><body style="background:#f4f9fb;margin:0;padding:28px 12px;font-family:Arial,Helvetica,sans-serif;color:#204157">'+
 '<div style="max-width:550px;margin:auto;background:white;border:1px solid #dae7e9;border-radius:16px;padding:30px">'+
 '<div style="font-size:25px;font-weight:800;color:#10364d">DParranda</div>'+
 '<p style="color:#087d86;font-size:12px;letter-spacing:1px;font-weight:700">PUBLICIDAD</p>'+
 '<h1 style="font-size:24px;line-height:1.3">'+esc(title)+'</h1>'+
 body+'<p style="margin-top:28px"><a href="'+safe+'" style="display:inline-block;border-radius:9px;background:#087d86;color:white;padding:13px 18px;text-decoration:none;font-weight:700">'+esc(cta)+'</a></p>'+
 '<p style="font-size:12px;color:#597384;overflow-wrap:anywhere">Si el botón no se abre, copia este enlace: '+safe+'</p>'+
 '<p style="font-size:12px;color:#718690;border-top:1px solid #e0e9ec;padding-top:14px">'+esc(foot)+'</p>'+
 '</div></body></html>';
}
export async function sendWelcomeEmail(info){
 if(!info?.account?.active)return {status:'inactive'};
 if(!canSendTo(info.account.email))return {status:'pending_domain'};
 const url=accessLink(info.account);
 if(!url)return {status:'failed'};
 const greeting='Hola '+(info.account.contact_name||info.account.company)+',';
 const title=info.draft.title||info.account.company;
 const subject='Bienvenido a DParranda · solicitud #'+info.leadId;
 const body='<p>'+esc(greeting)+'</p><p>Hemos recibido la solicitud de publicidad de <strong>'+esc(info.account.company)+'</strong> para el anuncio <strong>'+esc(title)+'</strong>.</p>'+
 '<p>Ya tienes un espacio privado donde puedes ver tu anuncio, seguir su revisión y realizar modificaciones si te las solicitamos.</p>'+
 '<p><strong>Estado actual:</strong> pendiente de revisión. No tienes que pagar nada todavía.</p>';
 const text=[greeting,'Hemos recibido tu solicitud de publicidad en DParranda.',
  'Anuncio: '+title,'Estado: pendiente de revisión. Sin pago.',
  'Acceso personal (válido 30 días): '+url].join('\n\n');
 return dispatch({to:info.account.email,subject,
  html:layout('Tu anuncio ya tiene su propio espacio',body,url,'Ver mi anuncio'),
  text,idempotencyKey:'dparranda-welcome-lead-'+info.leadId});
}
export async function sendChangesRequestedEmail(info,note,revisionKey){
 if(!info?.account?.active||!String(note||'').trim())return {status:'inactive'};
 if(!canSendTo(info.account.email))return {status:'pending_domain'};
 const url=accessLink(info.account);
 if(!url)return {status:'failed'};
 const title=info.draft?.title||info.account.company;
 const subject='DParranda · cambios solicitados en '+title;
 const body='<p>Hola '+esc(info.account.contact_name||info.account.company)+',</p>'+
 '<p>Hemos revisado tu anuncio <strong>'+esc(title)+'</strong> y necesitamos que realices algunos cambios antes de aprobarlo.</p>'+
 '<p style="padding:13px 16px;background:#f0f8f8;border-left:3px solid #087d86"><strong>Observaciones:</strong> '+esc(note)+'</p>'+
 '<p>Accede a tu área privada, abre el anuncio, corrige lo indicado y pulsa <strong>Enviar para revisión</strong>. No necesitas empezar una solicitud nueva.</p>';
 const text=['DParranda · revisión de tu anuncio',title,'Cambios solicitados: '+note,
  'Entra, corrige y vuelve a enviar para revisión: '+url].join('\n\n');
 return dispatch({to:info.account.email,subject,
  html:layout('Hay cambios pendientes en tu anuncio',body,url,'Revisar y corregir mi anuncio'),
  text,idempotencyKey:'dparranda-changes-'+info.draft.id+'-'+String(revisionKey||'').replace(/[^a-zA-Z0-9_-]/g,'').slice(0,100)});
}

export async function sendPaymentApprovedEmail(info,paymentUrl,cents,plan,days,linkId){
 if(!info?.account?.active)return {status:'inactive'};
 if(!canSendTo(info.account.email))return {status:'pending_domain'};
 if(!/^https:\/\/buy\.stripe\.com\//.test(String(paymentUrl||'')))return {status:'failed'};
 const labels={local:'Local',zona:'Zona',insular:'Insular'};
 const amount=(cents/100).toLocaleString('es-ES',{minimumFractionDigits:2})+' €';
 const title=info.draft?.title||info.account.company;
 const body='<p>Hola '+esc(info.account.contact_name||info.account.company)+',</p>'+
 '<p>¡Buenas noticias! Hemos aprobado tu anuncio <strong>'+esc(title)+'</strong> para su contratación en DParranda.</p>'+
 '<p><strong>Plan:</strong> Publicidad '+esc(labels[plan]||plan)+'<br><strong>Duración:</strong> '+esc(days)+' días (máximo 60 días por campaña)<br>'+
 '<strong>Importe total:</strong> '+esc(amount)+'</p>'+
 '<p>Completa el pago de forma segura mediante Stripe. El anuncio <strong>no se publicará hasta verificar el pago</strong>.</p>';
 const text=['DParranda · anuncio aprobado','Anuncio: '+title,'Plan: '+(labels[plan]||plan),
  'Duración: '+days+' días','Importe total: '+amount,
  'Realiza el pago con Stripe: '+paymentUrl,'El anuncio no se publica hasta verificar el pago.'].join('\n\n');
 return dispatch({to:info.account.email,subject:'DParranda · anuncio aprobado · pago de '+amount,
  html:layout('Tu anuncio ha sido aprobado',body,paymentUrl,'Pagar '+amount),
  text,idempotencyKey:'dparranda-approved-'+info.draft.id+'-'+linkId});
}
export async function sendPaymentConfirmedEmail(info,eventId){
 if(!info?.account?.active)return {status:'inactive'};
 if(!canSendTo(info.account.email))return {status:'pending_domain'};
 const url=accessLink(info.account);
 if(!url)return {status:'failed'};
 const title=info.draft?.title||info.account.company;
 const body='<p>Hola '+esc(info.account.contact_name||info.account.company)+',</p>'+
 '<p>Stripe ha confirmado el pago de tu campaña <strong>'+esc(title)+'</strong>.</p>'+
 '<p>Tu contratación está registrada y queda pendiente de su publicación según la fecha acordada. Puedes comprobar su estado en tu área privada.</p>';
 return dispatch({to:info.account.email,
  subject:'DParranda · pago confirmado · '+title,
  html:layout('Hemos recibido tu pago',body,url,'Ver estado de mi anuncio',
   'Este correo confirma el pago de tu campaña. El periodo publicitario no comienza antes de su activación.'),
  text:['Pago confirmado en DParranda','Anuncio: '+title,
   'Tu campaña está pendiente de publicación.','Consultar estado: '+url].join('\n\n'),
  idempotencyKey:'dparranda-payment-confirmed-'+String(eventId).slice(0,100)});
}
