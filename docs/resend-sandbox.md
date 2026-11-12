# Resend · pruebas de correos de DParranda antes de contratar dominio

## Estado
Resend Sandbox integrado en el panel de publicidad sin envío a clientes. El sistema no automatiza los correos de revisión aún.

## Vercel Production
Añade dos variables desde Settings → Environment Variables:
- RESEND_API_KEY: la API key que has generado en Resend. Configurar como **Sensitive**, nunca compartirla por chat ni añadirla a GitHub.
- RESEND_TEST_RECIPIENT: el mismo correo electrónico con el que registraste tu cuenta Resend, para las pruebas de sandbox.

Ambas Production. Realiza Redeploy.

## Probar
1. Entrar en https://canaryevent.vercel.app/admin/#publicidad
2. Ver el recuadro «Prueba de notificaciones por correo (Resend)».
3. Pulsar «Enviar correo de prueba» y confirmar.
4. Si Resend confirma un ID, comprobar la bandeja de entrada y spam del email configurado.

Se emplea onboarding@resend.dev solo en la prueba, a la propia cuenta autorizada. Los clics repetidos durante un mismo día comparten una clave de idempotencia para no enviar duplicados.

Sin dominio verificado el proveedor **no deja enviar correos a terceros**. No usar direcciones de anunciantes en RESEND_TEST_RECIPIENT. Tras adquirir un dominio, verificar su DNS en Resend, definir un remitente propio y añadir correo automatizado a cambios solicitados, aprobación editorial y pago confirmado con eventos de Resend y registro de fallos en Neon. No habilitar pagos o publicación reales antes de estar regularizada la actividad fiscal.
