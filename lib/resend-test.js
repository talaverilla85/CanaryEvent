// Resend sandbox test only. No marketing emails or customer notifications.
// All communication with Resend happens server-side; the API key stays in Vercel.
const validEmail=s=>typeof s==='string'&&/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(s.trim());
export function resendTestConfiguration(){
 const key=process.env.RESEND_API_KEY;
 const recipient=process.env.RESEND_TEST_RECIPIENT;
 const keyStatus=!key?'missing':!key.startsWith('re_')?'invalid_format':'configured';
 const recipientStatus=!recipient?'missing':!validEmail(recipient)?'invalid_format':'configured';
 return {
  ready:keyStatus==='configured'&&recipientStatus==='configured',
  api_key_status:keyStatus,
  test_recipient_status:recipientStatus
 };
}
export function resendTestConfigured(){return resendTestConfiguration().ready}
export async function sendResendAdminTest(){
 if(!resendTestConfigured())return {ok:false,error:'Falta configurar RESEND_API_KEY o RESEND_TEST_RECIPIENT en Vercel'};
 const today=new Date().toISOString().slice(0,10);
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),10000);
 try{
  const response=await fetch('https://api.resend.com/emails',{
   method:'POST',signal:controller.signal,
   headers:{
    Authorization:'Bearer '+process.env.RESEND_API_KEY,
    'Content-Type':'application/json',
    // One test email per UTC day. Repeated clicks will not send duplicates.
    'Idempotency-Key':'dparranda-test-email-'+today
   },
   body:JSON.stringify({
    from:'DParranda <onboarding@resend.dev>',
    to:[process.env.RESEND_TEST_RECIPIENT.trim()],
    subject:'DParranda · prueba de notificaciones',
    text:'¡La conexión de DParranda con Resend funciona! Este es un correo de prueba del administrador. No se ha avisado a anunciantes ni se ha generado ningún pago.'
   })
  });
  if(!response.ok){
   console.error('Resend sandbox test failed',response.status);
   return {ok:false,error:response.status===403?
    'Resend limita el remitente de pruebas al correo de tu cuenta. Revisa RESEND_TEST_RECIPIENT y que coincida con el correo registrado en Resend.':
    'Resend ha rechazado el envío (HTTP '+response.status+'). Revisa la clave y la configuración.'};
  }
  const result=await response.json();
  if(typeof result?.id!=='string'||!result.id)return {ok:false,error:'Resend no ha confirmado el identificador del envío'};
  return {ok:true,message:'Resend ha aceptado el correo de prueba. Revisa tu bandeja de entrada.',message_id:result.id};
 }catch(err){
  console.error('Resend sandbox connection error',err?.name||'Error');
  return {ok:false,error:'No se ha podido conectar con Resend'};
 }finally{clearTimeout(timeout)}
}
