import {nextTick,onUnmounted,watch} from 'vue'
let serial=0
// Native dialogs still need an explicit return target when Vue removes their DOM.
export function useDialogFocus(dialog){
 let opener=null,previous=null
 function restore(){
  if(previous?.open)previous.close()
  previous=null
  nextTick(()=>{if(document.querySelector('dialog[open]'))return;if(opener?.isConnected)opener.focus({preventScroll:true})})
 }
 watch(dialog,element=>{
  if(!element){restore();return}
  opener=document.activeElement;previous=element
  const heading=element.querySelector('h1,h2,h3')
  if(heading&&!element.hasAttribute('aria-labelledby')){if(!heading.id)heading.id='zhixing-dialog-title-'+(++serial);element.setAttribute('aria-labelledby',heading.id)}
  nextTick(()=>{if(dialog.value!==element)return;if(!element.open)element.showModal();const initial=element.querySelector('[autofocus]')||element.querySelector('textarea,input,select')||element.querySelector('button');initial?.focus({preventScroll:true})})
 },{flush:'post'})
 onUnmounted(restore)
}
