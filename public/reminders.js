/* D’Parranda · Recordatorios mediante calendario personal.
 * La agenda estática no envía push en segundo plano.
 * El usuario decide cuándo avisar y confirma la importación del .ics.
 */
'use strict';
function reminderTimed(e){
 return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(String(e.start||''));
}
function calendarUtcFromCanary(day,hour,minute=0){
 // Compute the actual UTC instant of the requested Canary local civil time.
 // At 18:00 there is no ambiguous local DST transition.
 const [year,month,date]=day.split('-').map(Number);
 if(!year||!month||!date)throw Error('Fecha incorrecta');
 const desired=Date.UTC(year,month-1,date,hour,minute);
 const fmt=new Intl.DateTimeFormat('en-GB',{timeZone:'Atlantic/Canary',
  year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',
  minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 const parts=Object.fromEntries(fmt.formatToParts(new Date(desired))
  .filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));
 const asUTC=Date.UTC(parts.year,parts.month-1,parts.day,parts.hour,parts.minute,parts.second);
 return new Date(desired-(asUTC-desired));
}
function reminderEventTime(e){
 if(!reminderTimed(e))return null;
 const t=e.start.slice(11,16).split(':').map(Number);
 return calendarUtcFromCanary(e.start.slice(0,10),t[0],t[1]);
}
function reminderPreviousFriday(day){
 const local=new Date(day+'T12:00:00Z');
 const weekday=local.getUTCDay(); // Friday=5; strict previous Friday
 let delta=(weekday-5+7)%7;
 if(delta===0)delta=7;
 local.setUTCDate(local.getUTCDate()-delta);
 return local.toISOString().slice(0,10);
}
function reminderAlarmTime(e,lead){
 const day=String(e.start||'').slice(0,10);
 const timed=reminderTimed(e);
 if(lead==='FRIDAY'){
  // Friday at 18:00 in the Canary Islands, including for Sunday plans.
  return calendarUtcFromCanary(reminderPreviousFriday(day),18,0);
 }
 const alarmDays={P1D:1,P2D:2,P3D:3,P7D:7};
 if(Object.prototype.hasOwnProperty.call(alarmDays,lead)){
  const d=new Date(day+'T12:00:00Z');
  d.setUTCDate(d.getUTCDate()-alarmDays[lead]);
  const prior=d.toISOString().slice(0,10);
  // Date-only events get a useful afternoon alert, never midnight.
  if(!timed)return calendarUtcFromCanary(prior,18,0);
  const [h,m]=e.start.slice(11,16).split(':').map(Number);
  return calendarUtcFromCanary(prior,h,m);
 }
 if(!timed)throw Error('Avisos por horas requieren hora de inicio confirmada');
 const hours={PT15M:15,PT1H:60,PT3H:180};
 if(!Object.prototype.hasOwnProperty.call(hours,lead))throw Error('Antelación incorrecta');
 return new Date(reminderEventTime(e).getTime()-hours[lead]*60000);
}
function reminderChoices(e){
 const choices=[
  ...(reminderTimed(e)?[['PT15M','15 minutos antes'],['PT1H','1 hora antes'],['PT3H','3 horas antes']]:[]),
  ['P1D','1 día antes'],['P2D','2 días antes'],['P3D','3 días antes'],['P7D','1 semana antes']
 ];
 const dow=new Date(String(e.start).slice(0,10)+'T12:00:00Z').getUTCDay();
 if(dow===6||dow===0)choices.unshift(['FRIDAY','Viernes anterior · 18:00']);
 const now=Date.now()+60000;
 return choices.filter(c=>{
  try{return reminderAlarmTime(e,c[0]).getTime()>now}catch{return false}
 });
}
function reminderCanSchedule(e){
 const day=String(e.start||'').slice(0,10);
 // Don't assume the next session of an already-started multi-day programme.
 if(day<todayKey())return false;
 if(reminderTimed(e)&&reminderEventTime(e).getTime()<=Date.now())return false;
 return reminderChoices(e).length>0;
}
function reminderEscapeText(value){
 return String(value||'').replace(/[\r\n]+/g,' ').replace(/\\/g,'\\\\')
  .replace(/;/g,'\\;').replace(/,/g,'\\,').slice(0,450);
}
function reminderICS(e,lead){
 if(!reminderCanSchedule(e)||!reminderChoices(e).some(c=>c[0]===lead))
  throw Error('No se puede preparar este aviso');
 const day=e.start.slice(0,10),stamp=new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
 const startDate=day.replace(/-/g,'');
 const timed=reminderTimed(e);
 const start=timed?'DTSTART;TZID=Atlantic/Canary:'+startDate+'T'+e.start.slice(11,16).replace(':','')+'00':
  'DTSTART;VALUE=DATE:'+startDate;
 const alarm=reminderAlarmTime(e,lead).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
 const lines=[
  'BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//DParranda//Agenda Canaria//ES',
  'CALSCALE:GREGORIAN','METHOD:PUBLISH',
  'BEGIN:VTIMEZONE','TZID:Atlantic/Canary','X-LIC-LOCATION:Atlantic/Canary',
  'BEGIN:STANDARD','TZOFFSETFROM:+0100','TZOFFSETTO:+0000','TZNAME:WET',
  'DTSTART:19701025T020000','RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU','END:STANDARD',
  'BEGIN:DAYLIGHT','TZOFFSETFROM:+0000','TZOFFSETTO:+0100','TZNAME:WEST',
  'DTSTART:19700329T010000','RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU',
  'END:DAYLIGHT','END:VTIMEZONE','BEGIN:VEVENT',
  'UID:padonde-'+e.id+'-'+lead+'@canaryevent.vercel.app',
  'DTSTAMP:'+stamp,start,
  'SUMMARY:'+reminderEscapeText(e.title),
  'LOCATION:'+reminderEscapeText((venueName(e)==='Recinto por confirmar'?'':venueName(e)+', ')+e.municipality+', Gran Canaria'),
  'DESCRIPTION:'+reminderEscapeText('Consulta posibles cambios de fecha u hora en la fuente oficial.'),
  'URL:https://canaryevent.vercel.app/?evento='+encodeURIComponent(e.id),
  'BEGIN:VALARM','ACTION:DISPLAY',
  'DESCRIPTION:'+reminderEscapeText('Recordatorio: '+e.title),
  'TRIGGER;VALUE=DATE-TIME:'+alarm,
  'END:VALARM','END:VEVENT','END:VCALENDAR'
 ];
 return lines.join('\r\n')+'\r\n';
}
function openReminderDialog(e){
 const choices=reminderChoices(e);
 const valid=reminderCanSchedule(e);
 const options=choices.map(c=>'<option value="'+c[0]+'">'+c[1]+'</option>').join('');
 openModal('<div class="form-panel"><span class="eyebrow">MIS FAVORITOS · RECORDATORIOS</span>'+
  '<h2 id="modalHeading">🔔 Recordar este plan</h2>'+
  '<p><strong>'+escapeHTML(e.title)+'</strong></p>'+
  '<p>'+escapeHTML(cardDateLabel(e))+' · '+escapeHTML(e.municipality)+'</p>'+
  (valid?'<form id="reminderForm" class="stack-form"><div class="field">'+
  '<label for="reminderLead">¿Cuándo quieres que te avisen?</label>'+
  '<select id="reminderLead">'+options+'</select></div>'+
  '<button class="primary-btn" type="submit">Añadir al calendario</button></form>':
  '<p class="footnote">No hay una fecha futura confirmada o las opciones de aviso ya han pasado. Consulta la fuente del evento antes de programarlo.</p>')+
  (!reminderTimed(e)?'<p class="footnote">Este plan no tiene hora confirmada: se añadirá como evento de día completo.</p>':'')+
  '<p class="footnote">Para recibir el aviso con la web cerrada, abre el archivo descargado e impórtalo en el calendario del móvil. El calendario gestiona las notificaciones; no son avisos push de D’Parranda.</p>'+
  '<button type="button" id="reminderBack" class="inline-link">Volver al evento</button></div>');
 $('reminderBack').onclick=()=>showEvent(e.id);
 if(!valid)return;
 $('reminderForm').onsubmit=ev=>{
  ev.preventDefault();
  const select=$('reminderLead').value;
  try{
   const ics=reminderICS(e,select);
   const url=URL.createObjectURL(new Blob([ics],{type:'text/calendar;charset=utf-8'}));
   const a=document.createElement('a');
   a.href=url;a.download='recordatorio-dparranda-'+e.id+'.ics';
   document.body.appendChild(a);a.click();a.remove();
   setTimeout(()=>URL.revokeObjectURL(url),2000);
   if(!state.favorites.has(e.id))toggleFav(e.id);
   toast('Importa el archivo para activar el aviso en tu calendario');
  }catch{
   toast('No se pudo preparar el archivo del recordatorio');
  }
 };
}
