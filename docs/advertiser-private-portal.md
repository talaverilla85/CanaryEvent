# DParranda · Área privada de anunciantes (prelanzamiento)

## Qué se ha construido
- Una URL **privada por empresa** creada desde su solicitud en `/admin/#publicidad`. La invitación contiene un token aleatorio de 256 bits en el fragmento `#acceso=...`; no se transmite al hosting en la primera visita. En el servidor se almacena **solo su SHA-256**, no el token original.
- El enlace lo **copia el administrador y lo manda por correo manualmente**. No se han integrado envíos de email, registro libre, ni cuentas abiertas.
- El anunciante visita `/anunciantes/`, intercambia el enlace por una sesión `HttpOnly; Secure; SameSite=Strict` de 30 días y puede volver a usar su enlace original para revalidarse. La URL en el navegador se limpia al entrar.
- Las cuentas pueden revocarse y los enlaces regenerarse. Se incrementa `access_version` para invalidar sesiones anteriores.
- El anunciante guarda y modifica borradores de campañas: cobertura Local/Zona/Insular, 30/60 días, fecha solicitada, formato banner/evento, municipios, texto, destino y una imagen horizontal optimizada 1200x675. Un anunciante solo ve sus propios datos.
- El panel muestra estados del anuncio y, **si una campaña llega a estar activa**, fechas reales de publicación y días restantes. Las estadísticas de visitas y clics no se inventan: permanecen como función futura.
- El panel de administración lista las cuentas y los anuncios creados, permite pedir correcciones y rechazar. **No se puede aprobar sin pago verificado**.
- El área privada no necesita un dominio diferente ni un sitio nuevo; reutiliza el proyecto Vercel y Neon actuales.

## Estado de lanzamiento
**El nuevo portal no está abierto al público**, ni está operativo el pago. Para habilitar la recepción de borradores en Vercel debe existir:
- `DATABASE_URL` conectada a Neon.
- `DPARRANDA_SESSION_SECRET` segura, la misma que utiliza el panel.
- `DPARRANDA_PRIVACY_URL` apuntando a un aviso de privacidad real y revisado.
- `DPARRANDA_ADVERTISER_PORTAL_ENABLED=true` únicamente cuando lo anterior esté configurado y `sql/advertising_v2.sql` se haya ejecutado.

La página pública de interés de anunciantes mantiene su flujo independiente y el acceso privado solo se distribuye de forma manual a interesados seleccionados.

## Fase Stripe, pendiente por decisión comercial/fiscal
Cuando la actividad esté regularizada, la solución de pago debe añadir:
1. Datos fiscales y de facturación completos, IGIC y reglas de precio, devoluciones, términos comerciales e inventario por zonas.
2. Checkout de Stripe creado por **el servidor** con la tarifa calculada desde base de datos. No confiar en precio, importe ni fecha enviados por el navegador.
3. Guardar un identificador de pedido único y la sesión de pago; confirmar únicamente eventos de webhook de Stripe verificados con firma. Eventos repetidos deben ser idempotentes.
4. Cambiar a `paid_review` solo tras verificar que el importe, moneda, pedido, titular y transacción están pagados. Nunca por mera redirección de éxito.
5. Avisar al administrador en Telegram de nuevo anuncio pagado; permitir aprobar, rechazar o solicitar cambios. El anuncio **no se publica sin aprobación manual**.
6. Tras aprobar, crear o enlazar el banner/evento patrocinado y activar el cómputo de 30/60 días **desde la fecha real convenida de publicación**, no desde el pago ni el envío a revisión.
7. Implementar comprobantes/facturación, tratamiento de rechazos, reembolsos y renovaciones. Si se rechaza un anuncio pagado, definir y aplicar una política de corrección/reembolso adecuada.
8. Para métricas, usar recuentos reales de impresiones y clics y visualizar solo datos verificados (nunca cifras de muestra como si fueran reales).

## Seguridad
- La invitación es una **credencial**: quien posea el enlace puede acceder. Si se reenvía o se filtra, regenerarla desde administración.
- Evitar compartir capturas con el enlace, pegarlo en sistemas externos o enviar enlaces con analítica incorporada.
- Todos los datos e imágenes quedan en Neon, en tablas privadas, sin exponer credenciales en el frontend.
- Mantener `noindex`, `noarchive`, `no-referrer`, aislamiento por anunciante y el flujo de aprobación humana.
