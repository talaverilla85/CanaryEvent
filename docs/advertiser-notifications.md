# Correos de anunciantes · flujo preparado

## Comportamiento
- Solicitud real del simulador: se guarda la propuesta con su imagen, se crea una cuenta privada de anunciante y un borrador asociado, y se prepara el correo de bienvenida.
- Pedir cambios desde la administración: se guardan las observaciones en el borrador, se intenta notificar al anunciante por Resend con acceso privado firmado y botón «Revisar y corregir mi anuncio».
- En el área privada se muestran las observaciones y el anuncio original; el cliente puede editar y volver a enviar la MISMA campaña para revisión.
- Los enlaces de los correos están firmados con DPARRANDA_SESSION_SECRET y una versión de acceso revocable. Validez 30 días, renovable mediante un nuevo enlace cuando se habilite el servicio completo.
- Las solicitudes previas se pueden seguir revisando. Para una solicitud anterior, «Pedir cambios» crea el espacio privado si corresponde.
- El formulario indica «Bienvenida enviada» únicamente si Resend acepta el envío.

## Antes de contratar dominio
La integración emplea RESEND_API_KEY y RESEND_TEST_RECIPIENT que ya están en Vercel. Si la solicitud utiliza **exactamente ese correo**, el usuario recibe correos de bienvenida y revisión desde onboarding@resend.dev. No se envía ningún correo a una dirección diferente. No se reciben pagos ni se publican campañas.

## Tras verificar el dominio
1. Verificar dominio y registros DNS en Resend.
2. Añadir RESEND_FROM_EMAIL, por ejemplo publicidad@DOMINIO_VERIFICADO.
3. Añadir RESEND_CUSTOMER_EMAILS_ENABLED=true en Production y redeploy.
4. Probar con un anunciante autorizado; solo entonces comenzar la captación pública.
5. Completar política de privacidad y fiscalidad para la operativa comercial.

El estado de revisión cambia incluso si el correo falla; el administrador recibe el estado de envío en el mensaje de resultado y nunca debe interpretar «cambios registrados» como «correo entregado». Es recomendable incorporar una cola persistente de notificaciones y reintentos (outbox) antes de lanzarlo comercialmente.
