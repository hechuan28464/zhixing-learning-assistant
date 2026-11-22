// Track only input method, never field values or typed content.
export function setupFocusModality(){
 const root=document.documentElement
 root.dataset.inputModality='pointer'
 const pointer=()=>{root.dataset.inputModality='pointer'}
 const keyboard=event=>{if(['Tab','Enter','Escape',' ','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)||(event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k')root.dataset.inputModality='keyboard'}
 document.addEventListener('pointerdown',pointer,true)
 document.addEventListener('keydown',keyboard,true)
 if(import.meta.hot)import.meta.hot.dispose(()=>{document.removeEventListener('pointerdown',pointer,true);document.removeEventListener('keydown',keyboard,true)})
}
