/* Calendario flexible de ¿Pa' Dónde?: date/month inputs complement quick filters.
 * Functions are invoked by the main app only after it defines shared state.
 */
'use strict';
function prettyDate(s,opts){
 return new Intl.DateTimeFormat('es-ES',{timeZone:'UTC',...opts}).format(new Date(s+'T12:00:00Z'));
}
function closeCustomDatePanel(){
 $('customDatePanel').classList.add('hidden');
 $('customDateToggle').setAttribute('aria-expanded','false');
}
function openCustomDatePanel(){
 if(!state.dateRange){
  $('filterMonth').value=todayKey().slice(0,7);
  $('filterFrom').value='';
  $('filterTo').value='';
 }
 $('customDateError').textContent='';
 $('customDatePanel').classList.remove('hidden');
 $('customDateToggle').setAttribute('aria-expanded','true');
}
function selectCustomDate(range,label){
 state.dateRange=range;
 state.dateRangeLabel=label;
 state.when='custom';
 state.tab='explore';
 state.newOnly=false;
 state.visibleLimit=48;
 closeCustomDatePanel();
 render();
}
function applyCustomDate(){
 const month=$('filterMonth').value;
 const from=$('filterFrom').value;
 const to=$('filterTo').value;
 $('customDateError').textContent='';
 if(from||to){
  if(!from||!to){
   $('customDateError').textContent='Elige las dos fechas.';
   return;
  }
  if(from>to){
   $('customDateError').textContent='El final debe ser igual o posterior al inicio.';
   return;
  }
  const label=from===to?
    'Para el '+prettyDate(from,{day:'numeric',month:'long',year:'numeric'}):
    'Del '+prettyDate(from,{day:'numeric',month:'short'})+' al '+
      prettyDate(to,{day:'numeric',month:'short',year:'numeric'});
  selectCustomDate({start:from,end:to},label);
  return;
 }
 if(!/^\d{4}-\d{2}$/.test(month)){
  $('customDateError').textContent='Elige un mes.';
  return;
 }
 const start=month+'-01';
 const end=new Date(Date.UTC(Number(month.slice(0,4)),Number(month.slice(5,7)),0))
  .toISOString().slice(0,10);
 selectCustomDate({start,end},'En '+prettyDate(start,{month:'long',year:'numeric'}));
}
