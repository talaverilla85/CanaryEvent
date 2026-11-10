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


## Flujo editorial actualizado y mesa de operaciones (noviembre 2026)

El administrador tiene un **resumen superior con cuatro contadores** (interesados, pendientes de revisión, activos, finalizados), una **tabla única** con empresa, solicitud, estado, pago, días, tipo, cobertura, precio, vista previa e historial. Se puede buscar, filtrar por estado y exportar un CSV con protección frente a fórmulas de Excel. Los registros antiguos y las herramientas manuales quedan bajo un desplegable de «Herramientas avanzadas».

### Entrada desde el simulador público

1. El visitante prepara el anuncio en \`/anunciate/\` y ve la simulación con eventos reales.
2. Si solo quiere consultar, usa «Me interesa esta campaña» (sin transferencia de imagen).
3. Desde el simulador, el visitante pulsa «Solicitar contratación y revisión del anuncio». La propuesta completa se envía a la mesa del administrador **sin cobrar ni publicar**. El formulario utiliza la recepción legal de solicitudes (DPARRANDA_LEADS_ENABLED, DATABASE_URL y DPARRANDA_PRIVACY_URL); ya no se necesita una bandera adicional para el envío de la creatividad. Si no hay aviso de privacidad o no está activada la recepción, el envío sigue cerrado.
4. La propuesta completa (datos de contacto, plan y duración, zona, título, descripción, destino, fecha solicitada e imagen WebP optimizada) se guarda en tablas privadas \`advertising_enquiries\` y \`advertising_enquiry_images\` mediante una única instrucción SQL; estado editorial \`submitted\`; **sin pago**.
5. En la tabla, el administrador elige «Ver anuncio» para revisar el material original y todos los datos.

### Circuito de correcciones

- La decisión «Pedir cambios» solicita un motivo obligatorio y fija \`changes_requested\`.
- Desde la misma solicitud, el administrador genera/copia el acceso individual para enviarlo manualmente al anunciante. Al crear esa invitación, la propuesta y su creatividad se importan a \`advertiser_campaign_drafts\` (vinculadas mediante \`source_lead_id\`). La tabla deja de duplicar la solicitud antigua cuando existe la versión del portal.
- El anunciante modifica su borrador y usa «Enviar para revisión». Una imagen y una fecha de inicio son necesarias; el estado pasa de \`draft\` o \`changes_requested\` a \`submitted\`.
- La nueva versión vuelve a aparecer en la misma tabla para una revisión humana. Puede repetirse el ciclo.

### Aprobación editorial y pagos (separados)

- «Aprobar contenido» lleva la campaña a \`approved_for_payment\`, después de exigir una imagen verificada. Esto **no es una confirmación de cobro** y **no activa publicidad**.
- La columna de pagos muestra «No verificado» mientras no exista una transacción real confirmada.
- La generación del enlace de Stripe, el envío comercial del enlace, el webhook idempotente, las facturas y la activación automática del anuncio **aún no están desarrollados**. Se implementarán tras regularizar la actividad, validar la pasarela y definir los datos fiscales.
- En la fase de pago real, solo el webhook del proveedor, tras comprobar importe, moneda, identidad de la campaña y autenticidad de la operación, podrá marcar \`payment_status='paid'\`. La publicación y el cómputo de días deben operar sobre la campaña que el administrador aprobó, nunca sobre un borrador posterior sin revisar.
- La política comercial de cambios y reembolsos para anuncios aprobados/pagados debe decidirse antes de aceptar el primer cobro.

El código de la tabla y la presentación de propuestas no cambia los valores de Vercel por sí mismo. No hay promesa de despliegue funcional hasta que Vercel complete una publicación correcta, la migración SQL se ejecute y se habiliten las respectivas variables.
