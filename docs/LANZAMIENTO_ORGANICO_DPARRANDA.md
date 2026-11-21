# D’Parranda · Lanzamiento orgánico (noviembre de 2026)

## Objetivo
Descubrir planes, atraer visitas desde Google y redes sociales y dar visibilidad a campañas propias (incluida AriMar), **sin venta de publicidad a terceros ni registro público de anunciantes**.

## Activado en la web
- Portada indexable, canonical https://dparranda.es/ y sitemap en https://dparranda.es/sitemap.xml.
- Contacto general: hola@dparranda.es (buzón confirmado por el titular).
- El feed muestra solo campañas activas desde /api/ads. AriMar sigue en el archivo de respaldo public/ads.json y en administración.
- No se muestran invitaciones de «Anúnciate» ni espacios comerciales de captación.
- /anunciate/* y /anunciantes/* redirigen temporalmente a /. La antigua interfaz permanece en el repositorio.
- Las API de captación antiguas y nuevas y el área del anunciante responden como no disponibles, salvo que se active DPARRANDA_ADVERTISING_SALES_ENABLED=true.
- La función ensureApprovedPayment impide crear o reenviar enlaces de pago nuevos mientras esté pausada.
- El panel /admin/ permanece operativo: eventos y campañas propias siguen siendo administrables.
- Se ha pausado el cron comercial de Telegram; el script, las pruebas y la ejecución manual permanecen instalados.
- Resend, Stripe, facturación, datos y plantillas no se han eliminado ni sus secretos alterados.

## Reactivar el modelo comercial más adelante
1. Revisar situación fiscal y protección de datos antes de aceptar contratos.
2. En Vercel (Production), configurar DPARRANDA_ADVERTISING_SALES_ENABLED=true y redeplegar; conservar DPARRANDA_LEADS_ENABLED y el resto de claves verificadas.
3. Eliminar **solamente** las redirecciones temporales de /anunciate y /anunciantes de vercel.json; desplegar.
4. Volver a incluir en portada las llamadas a contratar y los espacios comerciales si se desea; houseBannerHtml y houseEventHtml siguen conservados como funciones.
5. Restaurar el cron `*/5 * * * *` en .github/workflows/telegram-advertising-leads.yml si se quieren alertas periódicas.
6. Revisar destinatarios y dominio de Resend; verificar modo **test/live** de Stripe explícitamente; probar extremo a extremo sin activar cobros reales por accidente.
7. Revisar manualmente cualquier enlace de Stripe emitido **antes** de la pausa: la web puede bloquear contrataciones nuevas, pero un enlace de Stripe ya creado podría seguir cobrando directamente hasta desactivarlo en Stripe.

## SEO pendiente de siguientes fases
- Crear páginas regionales y municipales con contenido visible para rastreadores, sin duplicados ni indexación masiva vacía.
- Conectar y revisar la propiedad dparranda.es en Google Search Console y enviar el sitemap.
- Medir Search Console y conversiones hacia AriMar (clics sobre sus anuncios) antes de ampliar la inversión en campañas.

## Reglas de seguridad
La variable de pausa solo regula **nueva contratación**; no desactivar Stripe webhook de pagos ya iniciados sin antes comprobar enlaces históricos. No modificar ni suspender los anuncios propios desde este interruptor.
