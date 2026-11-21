// Lanzamiento orgánico: la venta de publicidad queda pausada por defecto.
// El panel de administración y los anuncios propios NO dependen de este interruptor.
// Para reactivarla, configurar DPARRANDA_ADVERTISING_SALES_ENABLED=true
// y eliminar las redirecciones temporales de /anunciate y /anunciantes en vercel.json.
export const advertisingSalesOpen=()=>process.env.DPARRANDA_ADVERTISING_SALES_ENABLED==='true';
