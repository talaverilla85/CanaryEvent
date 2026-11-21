/* Separate administrative PWA; never caches or stores administrator credentials. */
(()=>{
 'use strict';
 const dock=document.getElementById('adminInstallDock');
 const action=document.getElementById('adminInstallBtn');
 const dismiss=document.getElementById('adminInstallDismiss');
 const guide=document.getElementById('adminInstallGuide');
 const steps=document.getElementById('adminInstallSteps');
 const intro=document.getElementById('adminInstallIntro');
 const close=document.getElementById('adminInstallClose');
 if(!dock||!action||!dismiss||!guide||!steps||!intro||!close)return;
 const key='dparranda_admin_installed_hint_v1';
 const rememberDays=90;
 let deferred=null,installedThisVisit=false,dismissedThisVisit=false;
 const isStandalone=()=>window.matchMedia('(display-mode: standalone)').matches||
  window.matchMedia('(display-mode: fullscreen)').matches||navigator.standalone===true;
 const installedRecently=()=>{try{const at=Number(localStorage.getItem(key));
  return Number.isFinite(at)&&at>0&&Date.now()-at<rememberDays*86400000;
 }catch{return false}};
 function update(){dock.hidden=isStandalone()||installedThisVisit||dismissedThisVisit||installedRecently()}
 function installed(){installedThisVisit=true;deferred=null;
  try{localStorage.setItem(key,String(Date.now()))}catch{}
  if(guide.open)guide.close();
  update();
 }
 function showGuide(){
  const ios=/iPhone|iPad|iPod/i.test(navigator.userAgent)||
    (navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  intro.textContent=ios?
   'En iPhone o iPad, abre esta página en Safari y añádela a la pantalla de inicio.':
   'Si no aparece la ventana de instalación, usa el menú del navegador para añadir esta aplicación.';
  const items=ios?
   ['En Safari, pulsa Compartir.','Selecciona «Añadir a pantalla de inicio».',
    'Confirma «Añadir». Después abre el icono DParranda Admin.']:
   ['Abre el menú del navegador (⋮).','Pulsa «Instalar aplicación» o «Añadir a pantalla de inicio».',
    'Confirma para crear el acceso DParranda Admin.'];
  steps.replaceChildren();
  for(const item of items){const li=document.createElement('li');li.textContent=item;steps.append(li)}
  if(typeof guide.showModal==='function')guide.showModal();
  else guide.setAttribute('open','');
 }
 action.addEventListener('click',()=>{
  if(isStandalone()){installed();return}
  if(!deferred){showGuide();return}
  const prompt=deferred;deferred=null;
  try{
   // Must be invoked immediately inside the click gesture.
   const result=prompt.prompt();
   Promise.resolve(result).then(()=>prompt.userChoice).then(choice=>{
    if(choice?.outcome==='accepted')installed();else update();
   }).catch(()=>{update();showGuide()});
  }catch{update();showGuide()}
 });
 dismiss.addEventListener('click',()=>{dismissedThisVisit=true;update()});
 close.addEventListener('click',()=>{if(typeof guide.close==='function')guide.close();
  else guide.removeAttribute('open')});
 window.addEventListener('beforeinstallprompt',event=>{
  event.preventDefault();deferred=event;update();
 });
 window.addEventListener('appinstalled',installed);
 const media=window.matchMedia('(display-mode: standalone)');
 if(media.addEventListener)media.addEventListener('change',update);
 window.addEventListener('pageshow',update);
 window.addEventListener('resize',update,{passive:true});
 if('serviceWorker' in navigator){
  window.addEventListener('load',()=>navigator.serviceWorker.register('/admin/sw.js',{scope:'/admin/'}).catch(()=>{}));
 }
 update();
})();
