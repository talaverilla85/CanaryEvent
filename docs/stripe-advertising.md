# D’Parranda · Stripe para campañas de anunciantes (fase de pruebas)

## Tarifa y duración
Los planes duran **30 o 60 días**, como ya funciona en la web. El servidor calcula el precio sin fiarse del navegador:
- Local: 19 € / 30 días; 38 € / 60 días.
- Zona: 49 € / 30 días; 98 € / 60 días.
- Insular: 99 € / 30 días; 198 € / 60 días.
Son pagos **únicos**, no suscripciones ni renovaciones automáticas. Hasta 60 días máximo por contratación.

## Puesta en marcha
1. Ejecutar `sql/stripe_advertising.sql` en la **misma base Neon** de D’Parranda. Debe hacerse ANTES del despliegue de la API nueva.
2. En las variables de entorno **del proyecto Vercel de CanaryEvent** configurar, solo en pruebas:
   - `DPARRANDA_STRIPE_MODE=test`
   - `DPARRANDA_STRIPE_PAYMENTS_ENABLED=true`
   - `STRIPE_SECRET_KEY=sk_test_...` (clave secreta; nunca publicarla ni incluirla en GitHub).
   - `STRIPE_WEBHOOK_SECRET=whsec_...` (firma del webhook de este endpoint).
3. En Stripe **modo pruebas**, crear un destino de webhook HTTPS:
   `https://canaryevent.vercel.app/api/stripe-webhook`
   Eventos: `checkout.session.completed` y `checkout.session.async_payment_succeeded`.
4. Desplegar la rama cuando se hayan revisado y fusionado los cambios. Comprobar que sigue activo el envío de prueba de Resend, con `RESEND_TEST_RECIPIENT`. Sin dominio validado, Resend solo puede mandar a ese destinatario.
5. Realizar el circuito completo usando únicamente tarjetas de test de Stripe. Confirmar estado en Stripe y en Neon: `pending_payment` pasa a `paid_review`, `payment_status='paid'`, con fecha `paid_at`.

**Importante**: En esta fase, el pago confirma la contratación pero NO publica automáticamente el anuncio. Se conserva el estado `paid_review` hasta que la publicación programada y sus límites de inventario estén habilitados. Nunca se debe publicar por un redirect del navegador.

El enlace se genera únicamente desde administración tras aprobar creatividad. Cada enlace Stripe es de un solo uso (máximo una sesión completada). El admin puede reintentar el correo sin crear otro enlace. El anunciante autenticado también lo ve en su área privada.

Si `STRIPE_SECRET_KEY` o `STRIPE_WEBHOOK_SECRET` no están configuradas, el anuncio se aprueba editorialmente pero el pago queda bloqueado. La vista de administración permite reintentar el envío tras configurarlas.

Para activar pagos reales en el futuro se requerirá clave `sk_live_`, webhook real y `DPARRANDA_STRIPE_MODE=live`. No cambiarlo antes de tener verificadas las condiciones legales/fiscales, el dominio y el circuito de publicación.
