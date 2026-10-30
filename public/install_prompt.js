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
 const steps=document.getElementById('dpInstallGuideSteps');
 const description=document.getElementById('dpInstallGuideDescription');
 if(!dock||!action||!dismiss||!overlay||!close||!steps||!description)return;
 const DISMISS_KEY='dparranda_install_dismissed_until_v1';
 const INSTALLED_KEY='dparranda_install_installed_at_v1';
 const HIDE_DAYS=7;
 let nativePrompt=null;
 let focusBeforeDialog=null;
 const isStandalone=()=>(
   window.matchMedia('(display-mode: standalone)').matches ||
   window.matchMedia('(display-mode: fullscreen)').matches ||
   navigator.standalone===true
 );
 const narrowScreen=()=>window.matchMedia('(max-width: 720px)').matches;
 function readTime(key){
   try{return Number(window.localStorage.getItem(key))||0}catch{return 0}
 }
 function saveTime(key,value){
   try{window.localStorage.setItem(key,String(value))}catch{}
 }
 function shouldShow(){
   const now=Date.now();
   return narrowScreen() && !isStandalone() &&
     readTime(DISMISS_KEY)<now &&
     // appinstalled fires while still in the browser tab: don't ask to install twice.
     !(readTime(INSTALLED_KEY)>now-90*86400000);
 }
 function update(){
   dock.classList.toggle('hidden',!shouldShow());
 }
 function markInstalled(){
   saveTime(INSTALLED_KEY,Date.now());
   nativePrompt=null;
   closeGuide();
   update();
 }
 function dismissDock(){
   saveTime(DISMISS_KEY,Date.now()+HIDE_DAYS*86400000);
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
   if(isStandalone()){markInstalled();return}
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
 overlay.addEventListener('click',e=>{if(e.target===overlay)closeGuide()});
 document.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&!overlay.classList.contains('hidden')){e.stopPropagation();closeGuide()}
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
