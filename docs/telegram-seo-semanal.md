# Telegram: informe semanal SEO D’Parranda

El mismo bot privado de Telegram que usa la supervisión de la agenda publica **un único resumen los domingos** con la evolución de las páginas de eventos. Se crea mediante el workflow `.github/workflows/telegram-seo-weekly.yml`, sin nuevo bot ni credenciales adicionales.

## Resumen de los domingos
- GitHub Actions ejecuta el resumen cada domingo a las **10:17 UTC**, después de la sincronización diaria. Al integrar por primera vez el flujo también envía una medición inicial, evitando repetir la misma semana.
- `scripts/telegram_seo_report.py --weekly` consulta el **sitemap público real** y el catálogo público de D’Parranda. Solo considera candidatos SEO los IDs positivos no promocionados. No confunde sesiones de ID negativo ni anuncios con páginas SEO pendientes.
- Compara los IDs elegibles con `data/seo_weekly_snapshot.json` (histórico versionado) y muestra el total anterior y actual, cuántos se han incorporado, cuántos dejaron de ser aptos y cuántos candidatos siguen pendientes.
- Para «eventos mejorados y verificados durante los últimos 7 días», cuenta **IDs distintos activos** que tienen una prueba reciente en `event_enrichment_proofs` de `data/events.sqlite`. Un evento puede tener varios campos corregidos, pero se cuenta una vez.
- El primer informe se etiqueta explícitamente **«primera medición»**; no inventa variaciones ni datos de indexación de Google. No declara que una URL esté indexada: que aparezca en el sitemap solo significa que es apta.
- La medición se guarda **solo después de confirmarse el envío a Telegram**. Volver a ejecutar el mismo domingo no duplica el mensaje.

## Alertas SEO: solo excepciones
- La misma automatización verifica el sitemap diariamente a las **11:37 UTC** con dos intentos por ejecución.
- Solo alerta si el sitemap falla en **dos comprobaciones diarias** o si el informe del enriquecedor lleva **más de 72 horas** sin actualizarse.
- `data/seo_monitor_state.json` almacena la incidencia notificada, evita avisos repetidos y permite informar una vez cuando se recupera.
- Esto complementa, no sustituye, los avisos existentes del bot sobre eventos nuevos, fallos de los extractores y fuentes con incidencias.
- No activa ni modifica el bot de solicitudes de publicidad, que permanece pausado.

## Uso y seguridad
- Se reutilizan los secretos `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` del repositorio.
- No se envían datos personales, emails ni teléfonos; solo conteos, estado técnico y enlaces públicos.
- Se puede ejecutar `python scripts/telegram_seo_report.py --weekly --dry-run` y `--health --dry-run` sin enviar nada ni cambiar el histórico.
- Se pueden repetir manualmente desde GitHub Actions eligiendo el modo `weekly` o `health`.
- Las pruebas están en `tests/test_telegram_seo_report.py`.

## Límites
La evolución de fichas **aptas para Google** no equivale a páginas indexadas ni a visitas orgánicas. La medición real de impresiones y clics queda para una futura conexión con Google Search Console.
