/* D’Parranda · optional mobile PWA installation.
   Android Chromium: native beforeinstallprompt.
   iOS/other browsers: accurate manual home-screen instructions.
   Never display inside the installed application. */
(function(){
 'use strict';
 const dock=document.getElementById('dpInstallDock');
 const action=document.getElementById('dpInstallAction');
 const dismiss=document.getElementById('dpInstallDismiss');
 const overlay=document.getElementById('dpInstallGuideOverlay');
 const close=document.getElementById('dpInstallGuideClose');
 const done=document.getElementById('dpInstallGuideDone');
 const steps=document.getElementById('dpInstallGuideSteps');
 const description=document.getElementById('dpInstallGuideDescription');
 if(!dock||!action||!dismiss||!overlay||!close||!done||!steps||!description)return;
 // Remember confirmed installations for a limited time when the same user reopens
 // the browser tab; do not suppress permanently after an uninstall.
 const installedKey='dparranda_install_confirmed_v1';
 const installedHintMs=90*24*60*60*1000;
 function installedRecently(){
   try{const ts=Number(localStorage.getItem(installedKey));
    return Number.isFinite(ts)&&ts>0&&Date.now()-ts<installedHintMs;
   }catch{return false}
 }
 let dismissedForVisit=false;
 let installedInThisVisit=false;
 let nativePrompt=null;
 let focusBeforeDialog=null;
 const isStandalone=()=>(
   window.matchMedia('(display-mode: standalone)').matches ||
   window.matchMedia('(display-mode: fullscreen)').matches ||
   navigator.standalone===true
 );
 const metricEndpoint='/api/ads?op=pwa-event';
 // Send only a validated event name; never a visitor or device identifier.
 function reportMetric(event){
   const payload=JSON.stringify({event});
   try{
     if(typeof navigator.sendBeacon==='function' && typeof Blob!=='undefined'){
       const body=new Blob([payload],{type:'application/json'});
       if(navigator.sendBeacon(metricEndpoint,body))return;
     }
   }catch{}
   try{
     if(typeof fetch==='function')fetch(metricEndpoint,{
       method:'POST',headers:{'Content-Type':'application/json'},
       body:payload,credentials:'omit',keepalive:true
     }).catch(()=>{});
   }catch{}
 }
 function storedValue(key){try{return localStorage.getItem(key)}catch{return null}}
 function markMetricOnce(key,event){
   if(storedValue(key))return;
   try{localStorage.setItem(key,'1')}catch{}
   reportMetric(event);
 }
 function canaryDay(){
   const parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{
     timeZone:'Atlantic/Canary',year:'numeric',month:'2-digit',day:'2-digit'
   }).formatToParts(new Date()).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
   return parts.year+'-'+parts.month+'-'+parts.day;
 }
 function trackStandalone(){
   if(!isStandalone())return;
   markMetricOnce('dparranda_pwa_first_open_v1','standalone_first');
   const today=canaryDay();
   const key='dparranda_pwa_last_open_day_v1';
   if(storedValue(key)!==today){
     try{localStorage.setItem(key,today)}catch{}
     reportMetric('standalone_day');
   }
 }
 const narrowScreen=()=>window.matchMedia('(max-width: 720px)').matches;
 function shouldShow(){
   // Only an actual standalone window means that the current context is
   // installed. Historical localStorage flags may outlive an uninstallation.
   return narrowScreen() && !isStandalone() &&
     !dismissedForVisit && !installedInThisVisit && !installedRecently();
 }
 function update(){
   trackStandalone();
   dock.classList.toggle('hidden',!shouldShow());
 }
 function markInstalled(nativeConfirmed=true){
   if(nativeConfirmed)markMetricOnce('dparranda_pwa_native_confirmed_v1','native_install');
   installedInThisVisit=true;
   try{localStorage.setItem(installedKey,String(Date.now()))}catch{}
   nativePrompt=null;
   closeGuide();
   update();
 }
 function dismissDock(){
   // The X hides the invitation for this page view only. A reload restores
   // the option if the visitor still uses DParranda in the browser.
   dismissedForVisit=true;
   update();
 }
 function closeGuide(){
   if(overlay.classList.contains('hidden'))return;
   overlay.classList.add('hidden');
   document.body.classList.remove('dp-install-guide-open');
   if(focusBeforeDialog&&typeof focusBeforeDialog.focus==='function')focusBeforeDialog.focus();
   focusBeforeDialog=null;
 }
 function openGuide(){
   const ios=/iPad|iPhone|iPod/i.test(navigator.userAgent) ||
             (navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
   const list=ios?
     ['Abre D’Parranda en Safari si estás usando otro navegador.',
      'Pulsa Compartir (el icono de un cuadrado con una flecha hacia arriba).',
      'Selecciona «Añadir a pantalla de inicio» y confirma con «Añadir».']:
     ['Abre el menú de tu navegador (normalmente ⋮, arriba a la derecha).',
      'Elige «Instalar aplicación» o «Añadir a pantalla de inicio».',
      'Confirma para poner D’Parranda en tu pantalla principal.'];
   description.textContent=ios?
     'En iPhone y iPad se añade desde el menú Compartir de Safari.':
     'Tu navegador no ha ofrecido la instalación automática; puedes hacerlo desde su menú.';
   steps.replaceChildren();
   list.forEach(item=>{const li=document.createElement('li');li.textContent=item;steps.append(li)});
   focusBeforeDialog=document.activeElement;
   overlay.classList.remove('hidden');
   document.body.classList.add('dp-install-guide-open');
   close.focus();
 }
 action.addEventListener('click',()=>{
   if(isStandalone()){markInstalled(false);return}
   reportMetric('install_click');
   if(!nativePrompt){openGuide();return}
   const prompt=nativePrompt;
   nativePrompt=null;
   // Must be called synchronously inside the user's click, not after an await.
   try{
     const result=prompt.prompt();
     Promise.resolve(result).then(()=>prompt.userChoice).then(choice=>{
       if(choice&&choice.outcome==='accepted')markInstalled();
       else update();
     }).catch(()=>{update();openGuide()});
   }catch{
     openGuide();
   }
 });
 dismiss.addEventListener('click',dismissDock);
 close.addEventListener('click',closeGuide);
 done.addEventListener('click',closeGuide);
 overlay.addEventListener('click',e=>{if(e.target===overlay)closeGuide()});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)update()});
 document.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&!overlay.classList.contains('hidden')){e.stopImmediatePropagation();closeGuide()}
 });
 window.addEventListener('beforeinstallprompt',e=>{
   e.preventDefault();
   nativePrompt=e;
   update();
 });
 window.addEventListener('appinstalled',markInstalled);
 const standaloneMedia=window.matchMedia('(display-mode: standalone)');
 if(standaloneMedia.addEventListener)standaloneMedia.addEventListener('change',update);
 window.addEventListener('resize',update,{passive:true});
 window.addEventListener('pageshow',update);
 update();
})();
