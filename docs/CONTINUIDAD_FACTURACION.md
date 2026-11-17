# D’Parranda · Punto de continuación de facturación y devoluciones

**Última revisión:** 17 de noviembre de 2026  
**Estado:** **EN PAUSA — NO ACTIVAR FACTURAS NI REEMBOLSOS REALES**  
**Proyecto:** D’Parranda · [dparranda.es](https://dparranda.es/)  
**Repositorio:** `talaverilla85/CanaryEvent` · rama estable `main`  
**Documento funcional y técnico más completo:** [facturacion-dparranda.md](./facturacion-dparranda.md)

> **Decisión del titular:** D’Parranda facturará a nombre de una **persona física autónoma**, no de AriMar. El titular todavía **no ha regularizado/confirmado el alta censal de esta actividad en el epígrafe IAE correspondiente** y ha decidido POSPONER la puesta en producción de facturas, reembolsos y rectificaciones reales. Esta pausa es intencional; no reactivar por iniciativa del asistente.

## 1. Resumen que debe leer el siguiente asistente

- **Se ha desarrollado la estructura de integración, NO se ha conectado ni validado contra una cuenta real de FacturaDirecta.** No prometer que una factura fiscal se emitirá correctamente hasta completar pruebas verificadas con el proveedor.
- **Pruebas realizadas:** simulaciones locales/CI de código con Stripe y FacturaDirecta falsos. En la última batería antes de esta pausa, GitHub Actions superó **26 pruebas funcionales de Node y 549 pruebas Python**. Son pruebas de contrato/simulación, **no** validación end-to-end del proveedor ni de facturas oficiales.
- **Neon al pausar:** `advertising_invoice_reviews=0`, `advertising_invoice_issuance=0`, `advertising_invoice_adjustments=0`; no se han creado facturas fiscales ni devoluciones reales. La campaña fundadora AriMar permanece activa. Comprobar de nuevo estos contadores al reanudar.
- **Facturación automática aún NO implantada/activada.** El flujo diseñado es supervisado: pago real confirmado → borrador → revisión administrativa → confirmación explícita `EMITIR` → emisión por proveedor y correo con copia. Guardar el perfil fiscal no emite nada.
- **Rectificación/devolución** también supervisada, nunca iniciada por clientes: preparación de solicitud → confirmación administrativa `RECTIFICAR` o `DEVOLVER` → proveedor / Stripe.
- **Tarifas publicitarias** fijadas: 19 € Local, 49 € Zona, 99 € Insular por 30 días; 60 días cuesta el doble. Precios considerados **finales con IGIC general 7 % incluido** para el flujo canario *si* gestor confirma régimen, tributación y localización. No inventar retenciones ni modificar la tributación sin verificación.
- **Stripe** debe mantenerse en modo pruebas y **NO** activar `DPARRANDA_STRIPE_MODE=live` ni `FACTURADIRECTA_FISCAL_SETUP_CONFIRMED=true` hasta validar los requisitos y obtener autorización del titular.

## 2. ¿Cómo probar sin estar de alta en IAE?

### Pruebas que pueden hacerse ya

1. Pruebas unitarias y de integración con respuestas simuladas de Stripe y FacturaDirecta, sin cuentas ni facturas reales.
2. Probar la interfaz del panel, validaciones de NIF/cliente, desglose matemático del 7 %, estados de pago/rectificativas, bloqueo de duplicados y reintentos con base de datos **de pruebas**, no con dinero real.
3. Validar que el sistema rechaza emisión sin proveedor fiscal o sin confirmación de régimen, y que el correo no se envía en modo desactivado.

### FacturaDirecta sí ofrece un sandbox oficial

**Fuente oficial:** [Entorno de pruebas (Sandbox) de FacturaDirecta](https://help.facturadirecta.com/es/articles/15157082-entorno-de-pruebas-sandbox), actualizada el 19/06/2026.

- El sandbox es una **empresa de prueba aislada**: documentos **sin validez legal** y PDFs con marca de agua `Sin validez legal`.
- Los correos de pruebas se redirigen al usuario del sandbox, **no a clientes reales**; VeriFactu usa **el entorno de pruebas** de AEAT.
- **Requisito para crear sandbox:** usuario propietario con **una empresa real configurada previamente en FacturaDirecta**, de domicilio fiscal español, aunque sea de plan gratuito. Desde **Ajustes → API e integraciones → Entorno de pruebas (Sandbox) → Crear nuevo entorno de pruebas**.
- El sandbox tiene su propio **ID de empresa y API key**. No usar claves ni series de producción en pruebas.
- Dado que el titular todavía no tiene preparada su alta de actividad, **no necesita crear ahora esa empresa en el proveedor**. Podrá iniciar las pruebas oficiales una vez pueda configurar la cuenta correctamente.
- **IMPORTANTE:** el código actual exige Stripe `live` para ejecutar el flujo fiscal. Para una prueba real en sandbox habrá que preparar un entorno **aislado y explícitamente seguro** que acepte exclusivamente Stripe `test` + FacturaDirecta `sandbox`. No relajar la protección del entorno de producción ni generar facturas de producción con pagos de prueba.

## 3. Qué está desarrollado y dónde

| Función | Archivo(s) principal(es) | Estado comprobado |
|---|---|---|
| Captura del pago Stripe firmado | `api/stripe-webhook.js`, `lib/stripe-advertising.js` | Código y mocks; faltan pruebas reales de producción |
| Borradores de factura después del pago | `lib/advertising-invoice-reviews.js` | Preparado, no es factura fiscal |
| Datos fiscales del emisor autónomo | `lib/advertising-invoice-issuer.js`, `public/admin/admin.js` | Formulario privado configurado |
| Registro de emisiones | `sql/advertising-invoice-issuance.sql`, `lib/advertising-invoice-issuance.js` | Estados persistentes, pruebas simuladas |
| Conexión con FacturaDirecta | `lib/facturadirecta-invoices.js` | Adaptador sin credenciales conectadas; validar esquema de API con sandbox |
| Rectificativa y sustitución de datos | `lib/advertising-invoice-adjustments.js`, `sql/advertising-invoice-adjustments.sql` | Código y mocks, **sin emisión real** |
| Devolución total/parcial | `lib/advertising-invoice-adjustments.js` y Stripe | Código y mocks, **sin reembolso real** |
| Listado y acciones privadas | `api/admin.js`, `public/admin/index.html`, `public/admin/admin.js` | Requiere sesión administrativa |
| Test unitario de emisión | `tests/test_fiscal_issuance.mjs` | Mock |
| Test unitario de rectificaciones y devolución | `tests/test_invoice_adjustments.mjs` | Mock |
| Otras regresiones fiscales | `tests/test_commercial_workflow.mjs`, `tests/test_invoice_review_queue.py`, `tests/test_self_employed_issuer.py` | Mock / contrato |

La interfaz del panel está en [Administración → Publicidad](https://dparranda.es/admin/#publicidad). Muestra estado del emisor, borradores, botón de comprobación de conexión y solicitudes de rectificación/devolución. **Ningún botón debe generar obligaciones fiscales reales durante esta pausa.**

## 4. Requisitos legales y fiscales ANTES de activar nada

**Pendientes de consultar con el gestor** (no asumir resultado):

- [ ] Confirmar situación censal actual del titular. Si ya está inscrito en el censo por otra actividad, comprobar si corresponde **modificar actividades con modelo 036**, y determinar el **epígrafe de IAE aplicable a la comercialización de publicidad digital**. No confundir alta censal/IAE con pagar cuota de autónomo.
- [ ] Acordar fecha real de comienzo de actividad de D’Parranda **antes de vender y facturar comercialmente**. En 2026 el modelo 037 está suprimido; para declaraciones censales corresponde el 036, según AEAT.
- [ ] Confirmar si se aplica **IGIC régimen general 7 %** o si el titular está bajo REPEP/exención u otro tratamiento. El mero dato «7 %» elegido para la aplicación **no demuestra** la obligación tributaria.
- [ ] Analizar operaciones a anunciantes **fuera de Canarias, empresarios/autónomos de la Península, extranjeros y particulares** antes de automatizar impuestos. El circuito actual bloquea determinados destinatarios no canarios, pero se precisa estudio fiscal del caso.
- [ ] Confirmar identidad fiscal exacta del emisor, NIF/NIE, domicilio fiscal, numeración/serie, obligaciones de registro/VeriFactu según el régimen vigente y si se necesitan menciones especiales en factura.
- [ ] Validar con el gestor criterios de **rectificativas** (motivos R1/R4, y cuándo corresponde anulación) y política contractual de devoluciones, incluyendo campañas ya publicadas.
- [ ] Confirmar necesidades sobre justificantes, conservación fiscal, acceso al historial y envío de copias.

**Referencias oficiales:** [AEAT — inicio/modificación de actividad en modelo 036](https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/guia-practica-cumplimentacion-modelo-censal-036/capitulo-01-cuestiones-generales/plazos-presentacion/declaracion-alta/alta-censo-empresarios-profesionales-retenedores-036.html), [FacturaDirecta — API](https://www.facturadirecta.com/desarrolladores/api/), [FacturaDirecta — rectificativas](https://help.facturadirecta.com/es/articles/15084457-facturas-rectificativas).

## 5. Plan de reanudación, por etapas

**Etapa A — con gestor, todavía sin activar.** Cerrar epígrafe/alta de la actividad y tributación. Anotar en el panel (no en código ni chat) los datos correctos del emisor. No inventar datos.

**Etapa B — FacturaDirecta cuenta y sandbox.** Crear la empresa real en el proveedor conforme al alta. Crear sandbox aislado; comprobar desde él `GET /apiKeyInfo`, impuestos, series, permisos y esquemas reales; crear cliente y factura **de prueba**, rectificativa R4 y sustitución, devolución con rectificativa R1 simulada, y revisar PDFs y correo redirigido. No usar la empresa de producción para ensayar emisiones.

**Etapa C — Stripe pruebas aisladas.** Probar una compra ficticia de cada tarifa, un pago fallido, un reembolso parcial y total; cambios de datos; webhooks repetidos; reintentos tras error de email y tras facturas creadas; evitar duplicidad y verificar que el estado fiscal sigue al pago. Modificar el conmutador de sandbox solo **en el entorno de pruebas**, sin alterar la protección del sitio público.

**Etapa D — validación del código y la fiscalidad.** Contrastar los cuerpos JSON reales con la referencia OpenAPI actual de FacturaDirecta; confirmar contacto, serie, `correctedInvoice`, formato del importe con IGIC incluido y envío del documento al correo correcto. Revisar mecanismos de idempotencia y recuperaciones de errores contra el comportamiento efectivo del proveedor. Corregir diferencias encontradas y pasar CI completo.

**Etapa E — puesta en marcha con autorización.** Configurar secretos **en Vercel**, nunca en repositorio; verificar conectividad y reglas de fiscalidad en entorno apropiado; obtener aprobación expresa para pasar Stripe a `live`; realizar **una única contratación real controlada**, revisar factura, número fiscal, PDF, registros y los dos correos. Si hay anomalías, desactivar emisión y resolver antes de clientes reales.

**Etapa F — automatización futura opcional.** Solo después de que el titular valide las facturas reales: estudiar cambiar revisión manual por emisión/envío automático con registros de auditoría, alertas y excepciones fiscales. **No activar por el simple hecho de pulsar «Guardar datos fiscales».**

## 6. Variables técnicas reservadas (nunca escribir valores en documentos)

- `FACTURADIRECTA_API_KEY` — clave privada de empresa/proveedor.
- `FACTURADIRECTA_COMPANY_ID` — empresa de emisión (distinta del ID sandbox).
- `FACTURADIRECTA_IGIC_SALES_TAX_ID` — código de impuesto conforme al proveedor.
- `FACTURADIRECTA_INVOICE_SERIES` — numeración de facturas ordinarias.
- `FACTURADIRECTA_RECTIFICATION_SERIES` — numeración de rectificativas.
- `FACTURADIRECTA_ACCOUNT_CODE` — cuenta de ingresos configurada.
- `FACTURADIRECTA_FISCAL_SETUP_CONFIRMED` — se deja **desactivada** hasta validación.
- `DPARRANDA_STRIPE_MODE`, `DPARRANDA_STRIPE_PAYMENTS_ENABLED` y claves/webhook Stripe — mantener controlados; no cambiar a `live` sin autorización.
- `RESEND_API_KEY`, `RESEND_FROM_EMAIL` y copia del emisor `hola@dparranda.es` — revisar funcionamiento al emitir correos; el proveedor fiscal es quien debe enviar el PDF oficial.

**Estado de las variables en Vercel:** no se han vuelto a verificar desde este documento. **No asumir que existen o que son correctas**; comprobar nombres y entornos sin mostrar valores secretos.

## 7. Limitaciones conocidas y criterios de aceptación

- Las **pruebas actuales son simuladas**: pasar CI no confirma que FacturaDirecta acepte la forma exacta de cada petición. Validar con su OpenAPI y sandbox.
- No se ha probado la descarga real de PDF oficial ni una rectificación de producción. Las secuencias de devolución pueden necesitar ajuste según las respuestas de estado real de Stripe.
- Deben revisarse comportamientos ante reintentos cuando el proveedor recibe una operación pero el servidor pierde la respuesta: **no crear una segunda factura ni devolver dos veces**.
- No hay motor de rectificación fiscal universal para operaciones fuera de Canarias; **bloquear** y escalar a gestor.
- La app actual **no automatiza** la emisión inmediata tras el pago: requiere revisión/confirmación y pretende proteger al titular en el lanzamiento inicial.
- Una venta real exige trazabilidad: Stripe pago confirmado, factura con ID, serie y fecha, estado enviado y copia al correo previsto. Una devolución debe mostrar importe exacto reembolsado, estado Stripe y rectificativa fiscal enlazada; una corrección de NIF no debe generar devolución.
- Antes del primer uso, comprobar que AriMar sigue activa y que ninguna campaña o registro anterior ha sido modificado indebidamente.

## 8. Cómo retomarlo en cualquier conversación

Copia este mensaje:

> Continuamos la integración de facturación de **D’Parranda**. Lee primero `docs/CONTINUIDAD_FACTURACION.md` y `docs/facturacion-dparranda.md` del repositorio `talaverilla85/CanaryEvent`. El proyecto quedó pausado porque aún no estaba regularizada el alta censal/IAE de la actividad. **No emitas facturas fiscales reales, no reembolses dinero ni actives Stripe live sin mi autorización expresa.** Revisa el estado actual de GitHub, Neon y Vercel; comprueba qué requisitos fiscales y de FacturaDirecta he completado y retoma solo la siguiente etapa pendiente. Prioriza sandbox, pruebas verificadas de API e idempotencia.

---

**Decisión final de esta sesión:** **documentar y PAUSAR** facturación fiscal real y devoluciones. Nada de emitir, reembolsar ni activar automatismos. Se puede seguir desarrollando y probando en entornos simulados/aislados en otro momento.
