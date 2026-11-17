# D’Parranda · Facturación del autónomo

> **PAUSADO — 17/11/2026.** El titular todavía no ha formalizado/confirmado el alta censal de la actividad publicitaria. **NO emitir facturas oficiales, NO activar pagos reales, NO tramitar devoluciones reales.** La integración se ha preparado en código pero todavía no se ha validado contra FacturaDirecta real. El plan de pruebas aisladas, los requisitos fiscales, los archivos y el mensaje para continuar están en **[CONTINUIDAD_FACTURACION.md](./CONTINUIDAD_FACTURACION.md)**.
>
> Las pruebas de integración disponibles han utilizado respuestas simuladas de las API. FacturaDirecta permite crear facturas de prueba sin validez fiscal en su sandbox, siempre que se cree primero una empresa real de FacturaDirecta y desde ella el entorno de pruebas. [Ayuda oficial: Sandbox](https://help.facturadirecta.com/es/articles/15157082-entorno-de-pruebas-sandbox).

## Estado del despliegue

La aplicación guarda el perfil del emisor, recopila datos del comprador en Stripe y crea una ficha pendiente de revisar tras un pago confirmado.

**Guardar los datos fiscales NO emite facturas.** La emisión oficial depende de un proveedor fiscal configurado y de que se haya confirmado un **pago real**. En la primera fase se exige revisión y una confirmación manual explícita antes de enviar nada. La automatización total de la emisión no está activada.

## Requisitos antes de emitir

1. La actividad económica del titular debe estar censalmente dada de alta y el gestor debe confirmar que corresponde repercutir **IGIC general 7 %**. Si se aplica REPEP, otro régimen o reglas de localización especiales, no activar este flujo.
2. El titular guarda sus datos personales, NIF/NIE, domicilio fiscal, correo de copia y marca el reconocimiento de régimen general en **Panel → Publicidad → Datos fiscales del autónomo**.
3. Se crea/configura una empresa emisor **autónomo** en [FacturaDirecta](https://www.facturadirecta.com/), con Canarias/IGIC, el impuesto correcto de ventas, serie de facturación, cuenta contable y configuración fiscal/VeriFactu conforme al régimen aplicable.
4. En Vercel, en **Environment Variables** del proyecto correspondiente, configurar las siguientes variables **en el entorno Production**:

   - `FACTURADIRECTA_API_KEY`: clave privada con los scopes mínimos `contacts:read`, `contacts:write`, `invoices:write` (y `invoices:read` para consulta).
   - `FACTURADIRECTA_COMPANY_ID`: identificador de la empresa autónomo en FacturaDirecta.
   - `FACTURADIRECTA_IGIC_SALES_TAX_ID`: ID **de su catálogo de impuestos de ventas** para IGIC general 7 %.
   - `FACTURADIRECTA_INVOICE_SERIES`: serie creada en FacturaDirecta para la facturación de D’Parranda.
   - `FACTURADIRECTA_RECTIFICATION_SERIES`: serie específica de rectificativas en FacturaDirecta, por ejemplo `RDP-##-`. El código incluye `main.correctedInvoice` para enlazarlas con la factura original.
   - `FACTURADIRECTA_ACCOUNT_CODE`: cuenta contable de ingresos por publicidad configurada en FacturaDirecta.
   - `FACTURADIRECTA_FISCAL_SETUP_CONFIRMED=true`: activar solo tras verificar la configuración y los permisos en FacturaDirecta.
   - `DPARRANDA_STRIPE_MODE=live` junto con claves y webhook Stripe **de producción**. No alterar hasta realizar las comprobaciones de la pasarela.

   **No introducir claves ni NIF en GitHub ni en el chat.** Tras modificar variables de producción, desplegar de nuevo y comprobar el estado en el panel.

5. Primer ensayo de una venta real controlada: el cliente abona el importe definitivo por Stripe, la pasarela crea el borrador, la administración verifica el destinatario y pulsa **«Emitir y enviar factura»** escribiendo `EMITIR` para confirmar. El proveedor asigna la numeración fiscal y envía el PDF al cliente y copia al correo configurado (inicialmente `hola@dparranda.es`).

## Bloqueos de seguridad

- Nunca se emiten facturas desde pagos de prueba `cs_test_*`.
- Nunca se emiten dos documentos para el mismo pago Stripe aunque se reintente el webhook o se haga doble clic.
- Nunca se emiten sin verificar y marcar como revisados los datos fiscales del destinatario.
- El circuito general del 7 % solo permite automáticamente destinatarios con domicilio fiscal en **Canarias** (códigos postales 35xxx/38xxx). Otros casos se bloquean para revisión del tratamiento fiscal.
- Las facturas definitivas no se modifican desde el panel de D’Parranda: cualquier rectificación se tramita mediante el sistema de facturación.
- Si falla el correo tras la emisión, el sistema conserva el ID fiscal y solo reintenta **el envío**, no crea otra factura.
- El proveedor FacturaDirecta administra la facturación, numeración, PDF y registro fiscal/VeriFactu según su propia configuración. No atribuir cumplimiento legal a un PDF local de vista previa.
- Nunca activar emisión automática de todas las campañas a partir del mero acto de guardar el perfil.

Referencia técnica: [API de FacturaDirecta](https://www.facturadirecta.com/desarrolladores/api/).

## Activación futura de envío sin supervisión

Una vez auditada una factura real emitida y enviada correctamente, diseñar un ajuste explícito de activación/desactivación de la modalidad automática, con registro de auditoría, verificación de estado de Stripe, reglas fiscales por destinatario y reintentos idempotentes. **Actualmente no disponible ni habilitado.**

## Rectificaciones y devoluciones — administración de incidencias

Tras emitir **y enviar** una factura original verificada, aparece en el panel **Publicidad → Documentos pendientes de revisión → Rectificación / devolución**. Esta gestión se controla desde D’Parranda, pero las escrituras fiscales se realizan en FacturaDirecta y los movimientos de dinero en Stripe.

### Rectificación de datos fiscales

1. Elegir **Cambiar datos fiscales (sin devolución de dinero)**, introducir la razón social, NIF, domicilio y correo correctos, además de un motivo detallado.
2. Pulsar **Preparar solicitud**: no mueve dinero ni emite factura. Sólo registra la operación pendiente.
3. El administrador revisa la solicitud en **Rectificaciones y devoluciones**. Con FacturaDirecta configurado, confirma escribiendo `RECTIFICAR`.
4. FacturaDirecta crea mediante `POST /invoices` una rectificativa negativa **R4** con `main.correctedInvoice` apuntando a la factura original, y una nueva factura positiva con los datos correctos.
5. Se solicita al proveedor que envíe los dos PDFs al destinatario y copia al correo del emisor configurado. Los documentos llevan numeración fiscal del proveedor, no se alteran en D’Parranda.
6. Se conserva el histórico completo, los IDs de ambas facturas y sus estados. **Stripe no recibe ninguna solicitud de devolución**.

Para evitar usos fiscales incorrectos, si ya se había devuelto dinero de esa factura no se puede sustituir automáticamente; y si el nuevo destinatario está fuera de Canarias o tiene un NIF asociado a otra identidad, el flujo se bloquea para revisar el caso.

### Devolución total o parcial

1. Elegir **Devolver el saldo restante completo** o **Devolver una parte del pago**, importe y justificación. No se puede solicitar más que el total realmente pagado menos devoluciones anteriores.
2. Registrar la solicitud sin movimientos. El administrador confirma una segunda vez escribiendo `DEVOLVER`.
3. El servidor consulta la sesión de Checkout en Stripe (**en modo live**) y verifica la moneda EUR, el importe originalmente cobrado y el PaymentIntent. El navegador nunca puede imponer un identificador de cobro ni un importe arbitrario fuera del límite.
4. El servidor ejecuta **POST /v1/refunds** con una clave de idempotencia específica para la solicitud. Si Stripe devuelve `pending`, queda **pendiente** y **no se crea ninguna rectificativa todavía**.
5. Cuando el reembolso aparece como `succeeded` (tras pulsar **Consultar Stripe y continuar** si estaba pendiente), FacturaDirecta genera una rectificativa negativa **R1**, vinculada a la factura previa y por el **importe exacto devuelto**, con serie fiscal independiente.
6. Se solicita el envío de la rectificativa al cliente y copia al emisor. Una devolución completa confirmada pausa la publicidad y marca la contratación como cancelada. Una devolución parcial mantiene la campaña, salvo que el administrador la pause aparte.

Si Stripe falla, no se emite rectificativa de reembolso. Si Stripe ya devolvió el dinero y después falla FacturaDirecta, la operación queda **Requiere revisión y reintento**, guardando el ID del reembolso. Al reanudar **no se solicita un segundo reembolso**. Si se emitió la rectificativa, los reintentos guardan el ID y no generan una segunda.

### Verificación técnica antes del primer uso real

- **Sandbox oficial de FacturaDirecta:** requiere una empresa real previamente creada en FacturaDirecta con domicilio fiscal en España y acceso de propietario. Desde esta empresa real crear el sandbox en Ajustes → API e integraciones. Utilizar su identificador y claves **separados** de producción, con serie ordinaria, serie rectificativa, taxId de ventas IGIC, cuenta de ingresos y plantilla. En sandbox los PDFs llevan marca «Sin validez legal», los correos se redirigen al usuario de pruebas y VeriFactu apunta a pruebas. **No emitir facturas fiscales reales como ensayo.**
- Crear una **API key propia de D’Parranda** con permisos de lectura y escritura de `contacts` e `invoices`, y configurar las variables en Vercel (nunca en el repositorio ni en correos).
- Pulsar **Comprobar conexión con FacturaDirecta** en el panel: realiza únicamente `GET /apiKeyInfo`, sin crear ningún documento.
- Verificar un pago real supervisado. **No convertir una operación de prueba en una factura real**.
- Probar primero una rectificación de datos y una devolución parcial en sandbox con Stripe de pruebas, revisando que no se dupliquen facturas ni movimientos antes de usar el modo real. Como el circuito de operaciones reales requiere Stripe live, las pruebas funcionales integradas usan respuestas simuladas, no un pago de pruebas enviado a facturación real.
- Esta implementación es **supervisada**: el cliente no puede solicitar ni ejecutar devoluciones por su cuenta. No existe política de devoluciones automáticas ni habilitación al guardar el NIF.
- El programa de facturación y el asesor fiscal deben validar el supuesto concreto de rectificativa y el código R1/R4, así como el tratamiento IGIC de ventas a clientes fuera de Canarias.

Referencias oficiales de la integración:
- [FacturaDirecta — Facturas de venta API](https://www.facturadirecta.com/desarrolladores/api/referencia/invoices/)
- [FacturaDirecta — Rectificativas API](https://www.facturadirecta.com/desarrolladores/api/guias/corrective-invoices/)
- [Stripe — Reembolsos](https://docs.stripe.com/refunds)

**No se ha emitido ninguna factura ni ejecutado ningún reembolso real durante esta preparación.**
