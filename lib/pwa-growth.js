// PWA metrics are anonymous, aggregated by Canary date and event type.
// Browser-side localStorage avoids repeated signals; no identifier crosses the network.
export const PWA_EVENT_TYPES = Object.freeze([
  'install_click','native_install','standalone_first','standalone_day'
]);
const allowed = new Set(PWA_EVENT_TYPES);
export function validPwaEvent(body){
  if (!body || typeof body !== 'object' || Array.isArray(body)) return '';
  const keys=Object.keys(body);
  return keys.length===1 && keys[0]==='event' && allowed.has(body.event) ? body.event : '';
}
const count=n=>Number.isFinite(Number(n))&&Number(n)>=0 ? Number(n) : 0;
export function growthStatsPayload(totals=[],days=[]){
  const summary=Object.fromEntries(PWA_EVENT_TYPES.map(type=>[type,{
    today:0,last_7_days:0,last_30_days:0,total:0
  }]));
  for(const row of totals){
    if(!allowed.has(row.event_type))continue;
    summary[row.event_type]={
      today:count(row.today),last_7_days:count(row.last_7_days),
      last_30_days:count(row.last_30_days),total:count(row.total)
    };
  }
  const daily=days.filter(row=>allowed.has(row.event_type)&&/^20\d{2}-\d{2}-\d{2}$/.test(row.day))
    .map(row=>({day:row.day,event_type:row.event_type,count:count(row.count)}));
  return {time_zone:'Atlantic/Canary',metrics:summary,daily,
    notes:'Recuentos de señales, no personas únicas. Confirmaciones nativas y primeras aperturas pueden corresponder a la misma instalación.'};
}
