// A safe, strictly non-fiscal "prepare for invoicing" queue.
// Records are created only from previously verified Stripe payments.
// Invoices are NOT numbered, issued, downloaded as official PDFs, or emailed here.
import {safeText} from './admin-auth.js';
import {loadInvoiceIssuer,issuerComplete} from './advertising-invoice-issuer.js';
const email=v=>/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(v||'');
const clip=(value,max)=>safeText(value,max);
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=cents=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR'}).format(Number(cents)/100);

export async function prepareInvoiceReview(sql,draftId,session){
 const id=Number(draftId),sessionId=String(session?.id||'');
 const amount=Number(session?.amount_total);
 if(!Number.isSafeInteger(id)||id<1||!/^cs_(test_|live_)[a-zA-Z0-9]+$/.test(sessionId)||
  !Number.isSafeInteger(amount)||amount<1||session?.currency!=='eur'||session?.payment_status!=='paid')
  throw new Error('Solo se puede preparar un documento desde un pago Stripe verificado');
 const customer=session.customer_details||{},address=customer.address||{};
 const taxIds=Array.isArray(customer.tax_ids)?customer.tax_ids:[];
 const taxId=taxIds.find(t=>t&&typeof t.value==='string'&&t.value.length<=40)?.value||'';
 const street=[address.line1,address.line2].filter(v=>typeof v==='string'&&v.trim()).join(', ');
 const row=await sql`INSERT INTO advertising_invoice_reviews
 (draft_id,stripe_checkout_session_id,total_cents,company_name,customer_tax_id,billing_address,
 billing_postal,billing_city,billing_region,billing_country,billing_email)
 SELECT d.id,d.stripe_checkout_session_id,d.price_cents,
 COALESCE(NULLIF(${clip(customer.name,180)},''),NULLIF(e.legal_name,''),a.company),
 COALESCE(NULLIF(${clip(taxId,40)},''),COALESCE(e.tax_id,'')),
 COALESCE(NULLIF(${clip(street,220)},''),COALESCE(e.billing_address,'')),
 COALESCE(NULLIF(${clip(address.postal_code,20)},''),COALESCE(e.billing_postal,'')),
 COALESCE(NULLIF(${clip(address.city,110)},''),COALESCE(e.billing_city,'')),
 COALESCE(NULLIF(${clip(address.state,110)},''),COALESCE(e.billing_region,'')),
 COALESCE(NULLIF(${clip(address.country,90)},''),COALESCE(e.billing_country,'')),
 COALESCE(NULLIF(${clip(customer.email,180)},''),NULLIF(e.billing_email,''),a.email)
 FROM advertiser_campaign_drafts d
 JOIN advertiser_accounts a ON a.id=d.advertiser_id
 LEFT JOIN advertising_enquiries e ON e.id=d.source_lead_id
 WHERE d.id=${id} AND d.payment_status='paid' AND d.stripe_checkout_session_id=${sessionId}
 AND d.price_cents=${amount}
 ON CONFLICT(draft_id) DO NOTHING RETURNING draft_id`;
 return {prepared:row.length>0};
}

export async function listInvoiceReviews(sql){
 const rows=await sql`SELECT r.draft_id,r.total_cents,r.currency,r.company_name,r.customer_tax_id,
  r.billing_address,r.billing_postal,r.billing_city,r.billing_region,r.billing_country,
  r.billing_email,r.review_status,r.internal_note,r.created_at,r.checked_at,
  d.title,d.plan,d.days,d.placement,d.payment_status,d.paid_at,
  to_char(d.actual_starts_at,'YYYY-MM-DD') AS starts_at,
  to_char(d.actual_ends_at,'YYYY-MM-DD') AS ends_at
  FROM advertising_invoice_reviews r JOIN advertiser_campaign_drafts d ON d.id=r.draft_id
  ORDER BY (r.review_status='pending') DESC,r.created_at DESC LIMIT 200`;
 return {invoices:rows,auto_issuance:false,legal_invoice_emission:false,
  message:'Preparación administrativa de facturas. No se envía ni expide documentación fiscal.'};
}

function parsedId(value){
 const id=Number(value);
 if(!Number.isSafeInteger(id)||id<1)throw new Error('Documento no válido');
 return id;
}
export async function updateInvoiceReview(sql,body){
 const id=parsedId(body?.id),action=body?.action;
 if(!['save','check'].includes(action))throw new Error('Acción no permitida');
 const fields={
  company:clip(body.company_name,180),tax:clip(body.customer_tax_id,40),
  address:clip(body.billing_address,220),postal:clip(body.billing_postal,20),
  city:clip(body.billing_city,110),region:clip(body.billing_region,110),
  country:clip(body.billing_country,90),mail:clip(body.billing_email,180),
  note:clip(body.internal_note,700)
 };
 if(!fields.company||!email(fields.mail))throw new Error('Indica la razón social y un correo de facturación válido');
 if(action==='check'&&(!fields.tax||!fields.address||!fields.postal||!fields.city||!fields.country))
  throw new Error('Para revisar, completa NIF/CIF y domicilio fiscal del cliente');
 const checked=action==='check';
 const [updated]=await sql`UPDATE advertising_invoice_reviews SET
  company_name=${fields.company},customer_tax_id=${fields.tax},billing_address=${fields.address},
  billing_postal=${fields.postal},billing_city=${fields.city},
  billing_region=${fields.region},billing_country=${fields.country},billing_email=${fields.mail},
  internal_note=${fields.note},review_status=${checked?'checked':'pending'},
  checked_at=${checked?new Date():null},updated_at=now()
  WHERE draft_id=${id} RETURNING draft_id,review_status`;
 if(!updated)throw new Error('Documento pendiente no encontrado');
 return {saved:true,id,review_status:updated.review_status,issued:false,sent:false,
  message:checked?'Datos revisados. Aún no es una factura emitida; falta configurar la emisión fiscal.':
   'Borrador actualizado. No se ha enviado al cliente.'};
}
export async function invoiceReviewPreview(sql,idInput){
 const id=parsedId(idInput);
 const [r]=await sql`SELECT r.*,d.title,d.plan,d.days,d.placement,d.payment_status,d.paid_at,
  to_char(d.actual_starts_at,'DD/MM/YYYY') AS starts_at,
  to_char(d.actual_ends_at,'DD/MM/YYYY') AS ends_at
  FROM advertising_invoice_reviews r JOIN advertiser_campaign_drafts d ON d.id=r.draft_id
  WHERE r.draft_id=${id}`;
 if(!r)return null;
 const {issuer}=await loadInvoiceIssuer(sql);
 const issuerReady=issuerComplete(issuer);
 const v=x=>escapeHtml(x||'—');
 const desc='Publicidad '+({local:'local',zona:'por zona',insular:'insular'}[r.plan]||'')+
  ' · '+r.days+' días · '+(r.placement==='evento'?'Evento patrocinado':'Banner');
 // No official invoice series, tax rate or invoice date is invented.
 return `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="robots" content="noindex,nofollow">
 <title>Vista previa para revisión · D’Parranda</title>
 <style>body{margin:0;background:#edf3f5;color:#173244;font:14px/1.6 Arial,sans-serif}
 article{max-width:760px;margin:30px auto;background:white;padding:36px 42px;box-shadow:0 6px 28px #17324420}
 h1{margin:0;color:#0d6473;font-size:27px}h2{font-size:17px;margin:26px 0 6px}
 .warning{padding:14px 18px;background:#fff0d2;border:2px solid #de9c31;color:#7b4400;font-weight:700}
 .muted{color:#617988}.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px}
 table{width:100%;border-collapse:collapse;margin-top:18px}td,th{padding:10px;text-align:left;border-bottom:1px solid #dde8ea}
 .amount{text-align:right;font-size:21px;font-weight:bold}.note{margin-top:25px;font-size:12px}
 @media print{body{background:white}article{box-shadow:none;margin:0;padding:16px}.warning{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
 </style></head><body><article>
 <div class="warning">BORRADOR INTERNO · NO ES FACTURA · SIN VALIDEZ FISCAL · NO ENVIAR</div>
 <h1 style="margin-top:22px">D’Parranda</h1><p class="muted">Vista previa del pago verificado para preparar la futura factura.</p>
 <div class="cols">
 <section><h2>Emisor · autónomo</h2><p>${issuerReady?'':'<strong>DATOS DEL EMISOR INCOMPLETOS</strong><br>'}<strong>${v(issuer.legal_name)}</strong><br>
 NIF/NIE: ${v(issuer.tax_id)}<br>
 ${v(issuer.billing_address)}<br>
 ${v(issuer.billing_postal)} ${v(issuer.billing_city)}<br>
 ${v(issuer.billing_region)} ${v(issuer.billing_country)}</p></section>
 <section><h2>Destinatario</h2><p><strong>${v(r.company_name)}</strong><br>
 NIF/CIF: ${v(r.customer_tax_id)}<br>${v(r.billing_address)}<br>
 ${v(r.billing_postal)} ${v(r.billing_city)}<br>${v(r.billing_region)} ${v(r.billing_country)}<br>
 ${v(r.billing_email)}</p></section></div>
 <h2>Detalle del servicio</h2><table><thead><tr><th>Concepto</th><th>Total cobrado</th></tr></thead>
 <tbody><tr><td>${v(desc)}<br><span class="muted">${v(r.title)} · ${v(r.starts_at)} – ${v(r.ends_at)}</span></td>
 <td>${v(money(r.total_cents))}</td></tr></tbody></table>
 <p class="amount">Cobrado por Stripe: ${v(money(r.total_cents))}</p>
 <p class="note"><strong>Impuestos e IGIC:</strong> pendiente de determinar según la situación fiscal del emisor y destinatario.
 Este documento no contiene número de factura, desglose tributario ni código fiscal. No acredita la emisión de factura.</p>
 </article></body></html>`;
}
