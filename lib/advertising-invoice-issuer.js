// Emisor persona física para borradores administrativos. Sin emisión fiscal.
import {safeText} from './admin-auth.js';
const validEmail=value=>/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(value);
const taxIdPattern=/^(?:[0-9]{8}[A-Z]|[XYZ][0-9]{7}[A-Z])$/;
const defaults=()=>({
 issuer_type:'individual',legal_name:'',tax_id:'',billing_address:'',
 billing_postal:'',billing_city:'',billing_region:'',billing_country:'España',
 copy_email:'hola@dparranda.es',igic_general_rate_percent:7
});
export function issuerComplete(issuer){
 return !!(issuer&&issuer.legal_name&&issuer.tax_id&&issuer.billing_address&&
 issuer.billing_postal&&issuer.billing_city&&issuer.billing_region&&issuer.billing_country&&
 validEmail(issuer.copy_email));
}
export async function loadInvoiceIssuer(sql){
 const [issuer]=await sql`SELECT issuer_type,legal_name,tax_id,billing_address,
  billing_postal,billing_city,billing_region,billing_country,copy_email,igic_general_rate_percent,updated_at
  FROM advertising_invoice_issuer WHERE id=1`;
 const profile=issuer||defaults();
 return {issuer:{...profile,issuer_type:'individual'},data_complete:issuerComplete(profile),
  fiscal_issuance_enabled:false,tax_treatment:'pending',igic_general_rate_percent:7,prices_include_igic:true,
  message:'D’Parranda facturará a nombre de la persona física. La emisión legal y el IGIC requieren configuración fiscal.'};
}
export async function saveInvoiceIssuer(sql,body){
 if(body?.issuer_type&&body.issuer_type!=='individual')
  throw Error('D’Parranda está configurada para facturar como autónomo, no como sociedad.');
 const profile={
  legal_name:safeText(body?.legal_name,180),
  tax_id:safeText(body?.tax_id,24).toUpperCase().replace(/[\s-]/g,''),
  billing_address:safeText(body?.billing_address,220),
  billing_postal:safeText(body?.billing_postal,20),
  billing_city:safeText(body?.billing_city,110),
  billing_region:safeText(body?.billing_region,110),
  billing_country:safeText(body?.billing_country,90)||'España',
  copy_email:safeText(body?.copy_email,180).toLowerCase()
 };
 if(profile.tax_id&&!taxIdPattern.test(profile.tax_id))
  throw Error('Revisa el formato del NIF o NIE español. No se ha guardado.');
 if(profile.copy_email&&!validEmail(profile.copy_email))
  throw Error('Indica un correo válido para tu futura copia de factura.');
 const [updated]=await sql`INSERT INTO advertising_invoice_issuer
  (id,issuer_type,legal_name,tax_id,billing_address,billing_postal,billing_city,
   billing_region,billing_country,copy_email,updated_at)
  VALUES (1,'individual',${profile.legal_name},${profile.tax_id},${profile.billing_address},
   ${profile.billing_postal},${profile.billing_city},${profile.billing_region},
   ${profile.billing_country},${profile.copy_email},now())
  ON CONFLICT (id) DO UPDATE SET
   issuer_type='individual',legal_name=excluded.legal_name,tax_id=excluded.tax_id,
   billing_address=excluded.billing_address,billing_postal=excluded.billing_postal,
   billing_city=excluded.billing_city,billing_region=excluded.billing_region,
   billing_country=excluded.billing_country,copy_email=excluded.copy_email,
   updated_at=now()
  RETURNING issuer_type,legal_name,tax_id,billing_address,billing_postal,billing_city,
   billing_region,billing_country,copy_email,igic_general_rate_percent,updated_at`;
 return {saved:true,issuer:updated,data_complete:issuerComplete(updated),
  fiscal_issuance_enabled:false,emails_sent:false,
  message:'Datos del autónomo guardados de forma privada. No se ha emitido ni enviado ninguna factura.'};
}
