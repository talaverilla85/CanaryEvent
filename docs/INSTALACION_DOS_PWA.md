# D'Parranda: instalación en el móvil (dos aplicaciones)

## Para visitantes — D'Parranda

- Visitar `https://dparranda.es/` desde el móvil.
- Pulsar **Instalar app**, un botón flotante en la página pública.
- Chrome/Android: cuando el navegador lo permite, aparece la instalación nativa. En otros navegadores se explica cómo instalar desde el menú.
- iPhone/iPad: abrir Safari, Compartir → Añadir a pantalla de inicio.
- La invitación desaparece al abrir la app instalada (modo standalone), al recibirse `appinstalled`, o al confirmar la instalación nativa; en el mismo navegador, una instalación confirmada queda recordada hasta 90 días. La X solo la oculta durante la visita.
- La PWA pública conserva su `start_url` /, `scope` / e identidad /; no se ha reubicado.

## Para administración — DParranda Admin

- Visitar `https://dparranda.es/admin/` y pulsar **Instalar Admin** en el encabezado.
- Chrome/Android: instalación directa cuando el navegador la ofrece. Si no, utilizar menú ⋮ → Instalar aplicación / Añadir a inicio.
- iPhone/iPad: Safari → Compartir → Añadir a pantalla de inicio.
- Se crea una **segunda** aplicación con su propio manifiesto `/admin/manifest.webmanifest`, identidad `/admin/`, alcance `/admin/`, iconos PNG diferentes (180/192/512 px) e inicio `/admin/`.
- Su botón se oculta al instalarla y abrirla, o después de una instalación confirmada en el navegador. Se conservan las mismas verificaciones de contraseña y sesión: **instalar no da acceso al panel**.
- El service worker `/admin/sw.js` únicamente gestiona su registro/actualización; no almacena la página de inicio de sesión, tokens, API, imágenes privadas ni respuestas del administrador.
- La PWA pública deja de interceptar navegación a `/admin/` para evitar mostrar la portada pública como fallback sin conexión.

### Navegadores y limitaciones

- La instalación del navegador equivale a una PWA en ventana propia, no a una aplicación distribuida mediante Google Play o App Store.
- La instalación nativa automática depende de criterios y decisiones de cada navegador. Siempre existe guía para instalación manual.
- Los navegadores y aplicaciones instaladas pueden mantener sesiones o datos separados, especialmente en iOS. El administrador puede requerir iniciar sesión de nuevo.
- La instalación automática de una PWA diferente bajo el mismo dominio puede variar según versión del navegador y otras PWA instaladas; los IDs distintos y rutas específicas evitan compartir la misma identidad de instalación.
- El panel de administración requiere conexión a internet; deliberadamente no hay versión offline de datos privados.
- Si una PWA se desinstala, la confirmación de instalación guardada temporalmente en el navegador podría mantener oculto el botón hasta que caduque el recordatorio; el navegador permite volver a instalar desde su menú.
