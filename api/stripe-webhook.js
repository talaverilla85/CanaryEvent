// Stripe sends signed Checkout completion events here; never trust browser redirects.
import {createHmac,timingSafeEqual} from 'node:crypto';
import {db} from '../lib/admin-auth.js';
import {expectedAmount,stripePaymentsReady,stripeMode} from '../lib/stripe-advertising.js';
import {workspaceForDraft} from '../lib/advertiser-workspace.js';
import {sendPaymentConfirmedEmail} from '../lib/advertiser-mail.js';
import {schedulePaidDraft} from '../lib/advertiser-publication.js';

export const config={api:{bodyParser:false}};

function verifySignature(raw,header,secret){
 if(typeof header!=='string'||raw.length>1048576)return false;
 const pairs=Object.fromEntries(header.split(',').map(p=>p.trim().split('=')));
 const timestamp=Number(pairs.t);
 if(!Number.isSafeInteger(timestamp)||Math.abs(Date.now()/1000-timestamp)>300)return false;
 const expected=createHmac('sha256',secret).update(String(timestamp)+'.'+raw.toString('utf8')).digest('hex');
 return header.split(',').some(part=>{
  const [k,v]=part.trim().split('=');
  if(k!=='v1'||!v||!/^[0-9a-f]{64}$/.test(v))return false;
  return timingSafeEqual(Buffer.from(expected,'hex'),Buffer.from(v,'hex'));
 });
}
async function readRaw(req){
 const chunks=[];let size=0;
 for await(const part of req){
  const b=Buffer.from(part);size+=b.length;
  if(size>1048576)throw Error('Payload demasiado grande');
  chunks.push(b);
 }
 return Buffer.concat(chunks);
}
export default async function handler(req,res){
 res.setHeader('Cache-Control','no-store');
 if(req.method!=='POST')return res.status(405).json({error:'Método no permitido'});
 if(!stripePaymentsReady())return res.status(503).json({error:'Pasarela no configurada'});
 let raw;
 try{raw=await readRaw(req)}catch{return res.status(413).json({error:'Payload inválido'})}
 if(!verifySignature(raw,req.headers['stripe-signature'],process.env.STRIPE_WEBHOOK_SECRET))
  return res.status(400).json({error:'Firma Stripe inválida'});
 let event;
 try{event=JSON.parse(raw.toString('utf8'))}
 catch{return res.status(400).json({error:'JSON inválido'})}
 if(!['checkout.session.completed','checkout.session.async_payment_succeeded'].includes(event.type))
  return res.status(200).json({received:true});
 const s=event.data?.object;
 const linkId=typeof s?.payment_link==='string'?s.payment_link:s?.payment_link?.id;
 if(event.livemode!==(stripeMode()==='live')||
   s?.mode!=='payment'||s?.payment_status!=='paid'||
   !/^plink_[A-Za-z0-9]+$/.test(linkId||'')||s.currency!=='eur'||
   !Number.isSafeInteger(s.amount_total)||s.amount_total<=0)
  return res.status(200).json({received:true,ignored:true});
 try{
  const sql=db();
  const [d]=await sql`SELECT id,plan,days,price_cents,status,payment_status
   FROM advertiser_campaign_drafts WHERE stripe_payment_link_id=${linkId}`;
  if(!d||expectedAmount(d.plan,d.days)!==Number(d.price_cents)||
     Number(d.price_cents)!==s.amount_total||
     !['pending_payment','paid_review','approved_for_payment','approved','active'].includes(d.status))
   return res.status(200).json({received:true,ignored:true});
  const [updated]=await sql`UPDATE advertiser_campaign_drafts SET
   payment_status='paid',status='paid_review',paid_at=now(),
   stripe_checkout_session_id=${s.id},updated_at=now()
   WHERE id=${d.id} AND stripe_payment_link_id=${linkId}
    AND payment_status='pending' AND status IN ('pending_payment','approved_for_payment')
   RETURNING id,source_lead_id`;
  if(updated?.source_lead_id)
   await sql`UPDATE advertising_enquiries SET payment_status='paid' WHERE id=${updated.source_lead_id}`;
  // Confirmed payments must be scheduled server-side without an admin click.
  // If publication fails, return 503 so Stripe retries this signed event.
  // Retried events must also schedule a previously recorded paid_review/approved draft.
  const confirmedId=updated?.id || (d.payment_status==='paid'&&
   ['paid_review','approved'].includes(d.status)?d.id:null);
  if(confirmedId){
   await schedulePaidDraft(sql,Number(confirmedId));
  }
  if(updated){
   try{
    const info=await workspaceForDraft(sql,Number(updated.id));
    if(info)await sendPaymentConfirmedEmail(info,String(event.id));
   }catch(err){console.error('DParranda payment confirmation email failed',err?.name||'Error')}
  }
  return res.status(200).json({received:true});
 }catch(e){
  console.error('DParranda Stripe webhook persistence failed',e?.name||'Error');
  return res.status(503).json({error:'Confirmación pendiente de reintento'});
 }
}
