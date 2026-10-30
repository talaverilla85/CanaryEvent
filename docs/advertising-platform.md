# DParranda — Marketing y publicidad v2

## Formatos
1. **Evento patrocinado:** ficha con la misma estructura visual de los eventos extraídos, que mantiene etiqueta visible «Patrocinado» y procede de `sponsored_events`. Requiere revisión y activación manual; no altera el catálogo extraído.
2. **Banner:** anuncios de `ad_campaigns`, mostrados tras cada cinco tarjetas de eventos. Se rotan las campañas activas según el municipio y las fechas. Con pocas campañas, algunos espacios muestran «Anúnciate aquí».
3. **Campaña combinada:** un mismo registro comercial puede originar un evento y un banner, con la misma creatividad.

## Captación
Página: `/anunciate/`.
Formulario agrupado en contacto, datos fiscales, fechas y duración, evento, texto e imagen 16:9 y consentimiento.
Campos de factura: tipo (empresa/particular), razón social, ID fiscal, dirección completa, código postal, ciudad, provincia, país, correo de facturas, persona de contacto y teléfono.
Datos de evento: nombre, fecha/hora inicio y fin, municipio exacto, recinto, categoría, precio, descripción y URL de compra/reserva.
Campañas: tipo, nombre, fecha de arranque, duración seleccionable 7/14/30/60/90 días, zona de difusión.
Creatividad: imagen JPG/PNG/WebP, convertida en el navegador al mismo recorte 1200×675 (16:9) y limitada a 800 kB. Se guarda una sola vez en `advertising_enquiry_images` y puede reutilizarse para ambos formatos.

### Privacidad y activación
Los datos fiscales se almacenan exclusivamente en la base privada `advertising_enquiries`. No se transmiten a los endpoints públicos de eventos o banners.
**La recepción pública está deliberadamente desactivada** hasta que se complete la configuración de Vercel y se publique un aviso de privacidad con responsable del tratamiento, finalidades, bases, destinatarios, ejercicio de derechos y conservación.
La API requiere `DATABASE_URL`, `DPARRANDA_LEADS_ENABLED=true`, `DPARRANDA_PRIVACY_URL`; de lo contrario informa que no se aceptan solicitudes.
Antes de habilitar se aconseja revisión jurídica, política de conservación, protección antispam adicional y tratamiento seguro de datos de facturación.

## Proceso de administración
- `/admin/` → pestaña Publicidad → nuevas solicitudes, imagen, datos fiscales y contacto.
- «Crear evento» o «Crear banner» crea borradores **desactivados** desde una solicitud. Pueden coexistir los dos formatos sobre la misma creatividad.
- «Aprobar y publicar» activa el evento patrocinado, identificado como publicidad.
- El contador de días se calcula a partir de la fecha de fin, sin tareas programadas por campaña.
- Las campañas de banners guardan sus fechas y siguen el calendario, por lo que el anuncio deja de mostrarse cuando vence.
- El acceso privado requiere contraseñas y sesión segura de administrador configuradas en Vercel. El código desplegado no concede acceso público.

## Pendiente de monetización
- Precios y paquetes, reservas de inventario, pagos y facturas con Stripe.
- Métricas comprobadas de impresiones y clics, límites de frecuencia por visitante, estadísticas de campañas y segmentación por categorías.
- Imagen vertical opcional, carga de varias sesiones y enlace automático entre presupuestos, pagos y facturas.
- Posibilidad de revisar/editar cualquier borrador patrocinado desde el panel antes de activarlo.

No inventar eventos con fechas ficticias: la tarjeta «Anúnciate aquí» se presenta como publicidad y no se cuenta como un evento real.
