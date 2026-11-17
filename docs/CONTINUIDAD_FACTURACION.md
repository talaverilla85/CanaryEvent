# D’Parranda · Punto de continuación de facturación y devoluciones

**Última revisión:** 17 de noviembre de 2026  
**Estado:** **EN PAUSA — NO ACTIVAR FACTURAS NI REEMBOLSOS REALES**  
**Proyecto:** D’Parranda · [dparranda.es](https://dparranda.es/)  
**Repositorio:** `talaverilla85/CanaryEvent` · rama estable `main`  
**Documento funcional y técnico más completo:** [facturacion-dparranda.md](./facturacion-dparranda.md)

> **Decisión del titular:** D’Parranda facturará a nombre de una **persona física autónoma**, no de AriMar. El titular todavía **no ha regularizado/confirmado el alta censal de esta actividad en el epígrafe IAE correspondiente** y ha decidido POSPONER la puesta en producción de facturas, reembolsos y rectificaciones reales. Esta pausa es intencional; no reactivar por iniciativa del asistente.

## Simulador de facturación sin alta en el IAE (17/11/2026)

En el **panel privado de D’Parranda → Publicidad → Simulador seguro de facturación** hay cuatro escenarios accesibles con tarifas de 19/49/99 € y duraciones de 30/60 días: (1) factura de muestra, (2) rectificación de datos con cancelación contable y sustitución, (3) devolución total, (4) devolución parcial. Todos muestran el desglose **orientativo** del IGIC 7 % incluido, los pasos y documentos simulados con marcas de `SIM-` y «SIN VALIDEZ FISCAL».

Este demo es **estrictamente local y de solo lectura**, usando el cálculo y las estructuras del código existente pero sin acceder a la base de datos ni llamar a Stripe o FacturaDirecta. No crea archivos fiscales ni reembolsos reales; tampoco demuestra que el proveedor acepte las peticiones. El acceso requiere la sesión de administrador. El código está en `lib/advertising-invoice-simulator.js` y sus pruebas en `tests/test_invoice_sandbox_demo.mjs`.

**Importante: diferenciar dos tipos de pruebas:**
- **Demostración interna de D’Parranda**, ahora disponible: verifica cálculos y lógica de muestra, y no requiere cuenta en FacturaDirecta ni alta IAE.
- **Sandbox oficial de FacturaDirecta**, pendiente: solo es posible tras disponer de cuenta y una empresa previamente creada en ese proveedor. Los documentos tendrán marca «Sin validez legal», pueden ensayarse envíos redirigidos y procedimientos reales de la API sin afectar a datos productivos. Ver [instrucciones oficiales](https://help.facturadirecta.com/es/articles/15157082-entorno-de-pruebas-sandbox).

No usar el simulador como prueba legal/fiscal ni habilitar Stripe live o una empresa emisora real por haberlo ejecutado.

## Actualización: Stripe test + FacturaDirecta Sandbox (17/11/2026)

**La pausa se aplica a cobros, reembolsos y facturas de producción; se permiten pruebas ficticias dentro de los sandbox.** Se ha preparado la integración real de las API con la MISMA lógica de revisión y emisión, pero usando dos modos segregados. El modo sandbox está preparado en código; no se ha completado aún una llamada autenticada a la cuenta del titular, porque faltan las credenciales privadas que debe introducir él mismo en Vercel.

### Configurar la etapa de pruebas en Vercel

Guardar las siguientes claves **en los secretos de servidor del proyecto**, nunca en GitHub ni en chat:
- `DPARRANDA_BILLING_MODE=sandbox` — habilita la rama de facturación ficticia.
- `DPARRANDA_STRIPE_MODE=test` y `DPARRANDA_STRIPE_PAYMENTS_ENABLED=true`.
- `STRIPE_SECRET_KEY` — valor `sk_test_...` de Stripe.
- `STRIPE_WEBHOOK_SECRET` — `whsec_...` del endpoint de pruebas de `/api/stripe-webhook`.
- `FACTURADIRECTA_SANDBOX_API_KEY` — API key del entorno de pruebas de FacturaDirecta.
- `FACTURADIRECTA_SANDBOX_COMPANY_ID` — ID `com_...` de la empresa sandbox, no empresa real.
- `FACTURADIRECTA_SANDBOX_ENABLED=true` — permiso para crear facturas de prueba tras verificar que la empresa tiene `sandbox === true`.
- Solo si existen varias series/impuestos de ventas: `FACTURADIRECTA_SANDBOX_IGIC_SALES_TAX_ID`, `FACTURADIRECTA_SANDBOX_INVOICE_SERIES`, `FACTURADIRECTA_SANDBOX_RECTIFICATION_SERIES`.
- Si el código por defecto no existe: `FACTURADIRECTA_SANDBOX_ACCOUNT_CODE` con la cuenta contable de ingresos válida en el sandbox (por defecto `700000`).

La API verifica primero `GET /settings/company` con el ID de empresa, y bloquea si el proveedor no confirma `content.company.sandbox === true`. También verifica un impuesto de ventas IGIC al 7 %, y series de factura completa y rectificativa. No acepta empresa o API key idéntica a la configurada para producción.

### Prueba integral real, siempre sin validez fiscal

En administración: **Publicidad → FacturaDirecta Sandbox → Verificar**. A continuación simular el ciclo como anunciante, con datos ficticios: solicitar anuncio, revisión, aprobar, recibir enlace Stripe TEST, pagar con tarjeta de pruebas, dejar que el webhook firmado cree `advertising_invoice_reviews`, revisar datos fiscales de TEST y confirmar `EMITIR`. La API fiscal de la empresa sandbox crea y envía el documento con el importe pagado, marcando el registro `provider=facturadirecta-sandbox`. En pruebas se usa `prueba@example.com` para la petición de correo, y FacturaDirecta redirige los correos del sandbox a su propietario; el email de un cliente real no recibe ninguna factura de prueba. No se publica automáticamente un anuncio pagado en modo sandbox.

Las solicitudes de devolución parcial/total, una vez revisadas y confirmadas, actúan sobre Stripe TEST y crean rectificativas R1 en FacturaDirecta Sandbox. La corrección fiscal del comprador genera rectificativa R4 y factura nueva sin devolver dinero. Las operaciones mantienen referencias e idempotencia y rechazan cruzar un documento facturado en sandbox con el proveedor real.

Los botones siguen requiriendo confirmación; **no se ha habilitado facturación automática sin revisión**. El simulador local anterior permanece disponible de forma independiente.

### Preparación para pasar a modo real

No basta con una sola clave: usar `DPARRANDA_BILLING_MODE=live`, `DPARRANDA_STRIPE_MODE=live`, las credenciales `STRIPE_SECRET_KEY=sk_live_...` y `STRIPE_WEBHOOK_SECRET=whsec_...` de un webhook REAL, empresa real de FacturaDirecta `FACTURADIRECTA_API_KEY`, `FACTURADIRECTA_COMPANY_ID`, `FACTURADIRECTA_IGIC_SALES_TAX_ID`, series ordinaria y rectificativa, cuenta de ingresos y `FACTURADIRECTA_FISCAL_SETUP_CONFIRMED=true`. Comprobar el régimen fiscal del titular, revisar el perfil del emisor y autorizar el primer cobro. Se conservan registros históricos de pruebas pero el backend comprueba `cs_test_` frente a `cs_live_` y `provider` para impedir convertir facturas ficticias en facturas reales.

**No activar producción ni marcar el régimen fiscal como confirmado hasta el alta censal, validación contable y autorización expresa del titular.** Pruebas automatizadas y mocks no equivalen a conexión end-to-end real. Pendiente: credenciales, verificación del sandbox real, pruebas con tarjeta Stripe TEST, PDFs, envío redirigido e idempotencia ante fallos externos.

---

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


## Prueba directa de FacturaDirecta Sandbox desde Administración (17/11/2026)

En Administración → Publicidad, el bloque «Pruebas con el sistema de facturación real» aparece **antes** del simulador local. «Verificar FacturaDirecta Sandbox» realiza lecturas al proveedor, valida la marca de empresa sandbox, el impuesto y la serie. Solo cuando el resultado indica `verified + ready + enabled` se habilita «Crear factura en FacturaDirecta Sandbox». El usuario confirma escribiendo PRUEBA; el servidor exige además «PRUEBA SANDBOX» y revalida sandbox antes de escribir. Usa únicamente datos ficticios, no necesita ni crea ningún pago de Stripe y no envía correos. El resultado ofrece ID, total y enlace `webUrl` de FacturaDirecta (o acceso a la empresa de pruebas si el proveedor no lo devuelve), donde se puede abrir/descargar el PDF de pruebas con marca «Sin validez legal». No se ha realizado aún ninguna llamada real con las credenciales del usuario: debe verificar el resultado de la operación.


El flujo de prueba directa solicita además `PUT /{companyId}/invoices/{id}/pdf` tras comprobar mediante GET la factura creada. Muestra el enlace HTTPS temporal al PDF (el proveedor documenta una duración aproximada de 24 horas) y el enlace a la ficha de la factura; si generar el PDF falla se mantiene el ID y el enlace a FacturaDirecta Sandbox, sin reemitir otra factura.


## Diagnóstico de rechazo al crear contacto (17/11/2026)

El usuario probó la conexión real de Sandbox: empresa verificada con IGIC 7 %, series ordinaria y rectificativa, pero la primera emisión se detuvo en `POST /contacts`, HTTP 400 (no se creó ninguna factura ni hubo cobro). El 400 original ocultaba el JSON de validaciones. Se sustituyó el NIF ficticio `00000000T` por el CIF de ejemplo `B12345674` de la documentación oficial de FacturaDirecta; para corregidos se usa `12345678Z`. Se incorporó propagación limitada de `errors[].path/message` para mostrar en el panel el campo rechazado sin incluir claves ni cuerpos de petición. Pendiente: reintentar con la cuenta de Sandbox real y atender el campo concreto que informe la API. Enlace de referencia: https://www.facturadirecta.com/desarrolladores/api/referencia/contacts/ .
