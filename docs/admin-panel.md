# DParranda · Panel privado de administración (fase inicial)

## Qué está desplegado

Ruta de acceso: https://canaryevent.vercel.app/admin/

La web es estática, pero el panel habla con una función **de servidor** de Vercel
(/api/admin), nunca directamente con PostgreSQL desde el navegador.

Secciones implementadas:

- Acceso exclusivo de administrador mediante contraseña scrypt verificada en servidor.
  Sesiones HMAC con cookie HttpOnly, Secure, SameSite=Strict, caducidad 12 horas.
  Protección CSRF por origen y límite de ocho intentos en quince minutos por dirección anonimizada.
- Eventos: buscador, listado de posibles duplicados, marcar como revisados,
  corregir título, descripción, recinto, categoría, precio y gratuidad,
  ocultar una ficha y vincularla a la principal si pertenecen al mismo municipio y día.
- Publicidad: editar AriMar y otras campañas, crear una nueva, activar/pausar,
  fechas, municipios y enlaces de destino HTTPS.
- Los cambios se guardan en las tablas de Neon (event_overrides y ad_campaigns).
  Los extractores no sobrescriben los cambios editoriales.
- Lecturas públicas en /api/catalog y /api/ads. El frontend consulta esas rutas
  con respaldo automático en /events.json y /ads.json si falla la API.
- Se evita servir recursos de administración mediante el service worker.

## Estado de activación

**El panel todavía está bloqueado de forma intencional.** La conexión
DPARRANDA_DATABASE_URL de GitHub Actions no llega automáticamente a las
funciones de Vercel. Son sistemas distintos; no debe hacerse pública la contraseña.

Para habilitar el panel, el proyecto Vercel canaryevent necesita tres
variables de entorno de **servidor**, como encrypted/sensitive, en Production:

1. DATABASE_URL: cadena PostgreSQL de Neon. Recomendado conectar Neon mediante
   Vercel Marketplace y que la integración cree la variable. No copiarla al HTML.
2. DPARRANDA_ADMIN_PASSWORD_SCRYPT: SALT_HEX:HASH_HEX, donde SALT_HEX son al
   menos 16 bytes en hexadecimal y HASH_HEX tiene 64 bytes scrypt en hexadecimal.
3. DPARRANDA_SESSION_SECRET: cadena aleatoria criptográficamente segura
   (mínimo 32 caracteres, idealmente 32 bytes o más).

Generar los valores de autenticación **localmente**, sin publicar contraseñas
en el repositorio ni enviarlas por chat. Ejemplo desde Node.js, con
`ADMIN_PASSWORD` solo en un entorno seguro (no el shell history):

```js
import {randomBytes,scryptSync} from 'node:crypto';
const salt=randomBytes(16);
const hash=scryptSync(process.env.ADMIN_PASSWORD,salt,64);
console.log('DPARRANDA_ADMIN_PASSWORD_SCRYPT='+salt.toString('hex')+':'+hash.toString('hex'));
console.log('DPARRANDA_SESSION_SECRET='+randomBytes(48).toString('hex'));
```

No activar contraseñas por defecto, usuarios de demostración ni rutas de
escritura públicas. Si falta cualquier variable, /api/admin devuelve 503.

Tras conectar y definir la contraseña, hacer redeploy de Vercel y comprobar:

1. Sin login: /api/admin?op=stats devuelve 401.
2. Contraseña incorrecta: devuelve 401; tras varios intentos, 429.
3. Login correcto y sesión: /api/admin?op=session authenticated=true.
4. Ocultar un evento de prueba: no aparece en /api/catalog, sigue en SQLite.
5. Restaurar la ficha: vuelve a aparecer, y la sincronización nocturna no
   deshace la corrección.
6. Crear campaña desactivada: no aparece en /api/ads; activarla sí.
7. Confirmar que la web pública sigue mostrando el JSON si PostgreSQL falla.

## Protección y límites

- La ruta /admin es de acceso público a nivel de archivos HTML, pero no muestra
  datos administrativos ni permite operaciones sin autenticación válida.
  Noindex, Content Security Policy, antiframing y caché deshabilitada.
- **No hay alta de usuarios** ni registro de anunciantes.
- Todavía no hay subida de imágenes ni informes de clics reales. Los anuncios
  pueden apuntar a imágenes propias ya subidas a public/sponsors/.
- La búsqueda de duplicados muestra candidatos: no fusiona sin la revisión
  explícita de administración.
- El campo de unificación usa un identificador de ficha publicado (no obliga a
  borrar ningún registro de SQLite).
