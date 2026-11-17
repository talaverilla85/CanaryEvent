# D’Parranda · Facturación del autónomo

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
