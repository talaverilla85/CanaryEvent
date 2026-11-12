# DParranda · Privacidad del titular autónomo

La futura actividad publicitaria de DParranda figurará a nombre de su titular persona física autónoma, no de AriMar. No copiar datos legales de otra empresa.

## Página preparada
- https://canaryevent.vercel.app/privacidad/
- Incluye identidad y contacto del responsable, finalidades, bases jurídicas, destinatarios, conservación y ejercicio de derechos.
- Si faltan datos legales muestra «Información legal pendiente de completar» y no habilita la recepción pública.
- Se mantiene noindex durante la fase actual de prueba.

## Variables en Vercel Production (introducir directamente, no enviarlas por chat)

- DPARRANDA_LEGAL_NAME: nombre y apellidos legales completos.
- DPARRANDA_LEGAL_ADDRESS: dirección profesional o domicilio válido para información legal.
- DPARRANDA_LEGAL_NIF: NIF del titular autónomo.
- DPARRANDA_PRIVACY_EMAIL: correo de contacto profesional, público.
- DPARRANDA_LEADS_ENABLED: true, únicamente cuando el responsable revise la información legal y decida recibir solicitudes reales.

DATABASE_URL permanece como antes. DPARRANDA_PRIVACY_URL ya no es obligatoria: cuando existe una identidad completa la aplicación utiliza su ruta HTTPS /privacidad/; existe una opción para configurar otro URL HTTPS del mismo dominio al adquirirlo.

Tras definir variables de Production, redeploy, revisar el aviso y comprobar el estado en Administración → Publicidad. La simulación y el envío de prueba del administrador no requieren abrir la recepción pública.

## Revisiones antes de cobrar
- Consultar con el asesor el alta de la actividad y obligaciones de facturación e IGIC.
- Confirmar contratos y transferencias internacionales de proveedores tecnológicos.
- Completar el aviso legal e información comercial que corresponda a la actividad online.
- Mantener Stripe solo en test hasta tener conformidad.

Normativa:
https://www.aepd.es/derechos-y-deberes/conoce-tus-derechos/derecho-de-informacion
https://www.boe.es/eli/es/lo/2018/12/05/3
https://www.boe.es/eli/es/l/2002/07/11/34
