# CanaryEvent / planGC

Vista previa de eventos de Gran Canaria, diseñada principalmente para móvil y tablet.

## Estado de esta publicación

**Demostración visual, NO plataforma de eventos en producción.** Incluye 18 fichas de muestra de octubre y noviembre de 2026, tarjetas visuales, filtros por fecha/categoría, mapa, cercanía aproximada, favoritos locales y enlaces a fuentes originales. Los datos no se actualizan solos; registro y publicación de comerciantes requieren un servidor y base de datos persistente. La página está marcada noindex para no presentar contenido de prueba como agenda real.

## Despliegue

En Vercel: Importa este repositorio desde GitHub, Framework **Other**, Root Directory **./**, Output Directory **public** (ya está configurado en `vercel.json`). Se publica automáticamente tras cada push a `main`.

## Convertir en una plataforma completa

Se dispone de prototipo original de backend Python con SQLite y extracción experimental de fuentes municipales. Antes de activarlo en Vercel es imprescindible migrar a base de datos persistente (por ejemplo PostgreSQL), adaptar los endpoints API a serverless, alojar las credenciales como secretos y configurar tareas periódicas. Las fuentes no han sido verificadas en producción. No se autoriza un volcado masivo de portales privados sin un acuerdo.
