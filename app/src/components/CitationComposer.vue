<script setup>
import {computed,nextTick,ref,watch} from 'vue'
import {api,useLearning} from '../useLearning.js'
import {icon} from '../assets.js'
import ReferencePicker from './ReferencePicker.vue'
import {readLibraryMetadata} from '../libraryQuery.js'
const props=defineProps({modelValue:String,references:Array,sessionId:String,busy:Boolean,error:String,canStop:Boolean})
const emit=defineEmits(['update:modelValue','update:references','send','stop','attach'])
const {state}=useLearning()
const input=ref(null),picker=ref(false),candidates=ref([]),loading=ref(false),loadFailed=ref(false),pickerError=ref(''),referencePicker=ref(null),referenceTrigger=ref(null),attachmentTrigger=ref(null)
const selectedKeys=computed(()=>props.references.map(item=>item.key))
function remove(key){emit('update:references',props.references.filter(item=>item.key!==key))}
function selectKeys(keys){
 if(keys.length>3){pickerError.value='每次问题最多引用 3 份内容，请先移除一份。';return}
 const lookup=new Map([...props.references,...candidates.value].map(item=>[item.key,item]))
 pickerError.value='';emit('update:references',keys.map(key=>lookup.get(key)).filter(Boolean))
}
function closePicker(reason='trigger'){picker.value=false;if(reason!=='outside')nextTick(()=>reason==='composer'?input.value?.focus():referenceTrigger.value?.focus())}
let request=0
async function load(){
 const version=++request;loading.value=true;loadFailed.value=false;pickerError.value=''
 try{
  const params=new URLSearchParams({kind:'material'});if(props.sessionId)params.set('session_id',props.sessionId)
  const result=await readLibraryMetadata(api,Object.fromEntries(params))
  if(version===request)candidates.value=result.items
 }catch(e){if(version===request){loadFailed.value=true;pickerError.value=e.message}}
 finally{if(version===request)loading.value=false}
}
async function openPicker(){if(picker.value){closePicker();return}picker.value=true;await load();await nextTick();referencePicker.value?.focusSearch()}
async function attach(){picker.value=false;await nextTick();attachmentTrigger.value?.focus();emit('attach',props.sessionId)}
watch(()=>props.sessionId,()=>{++request;candidates.value=[];picker.value=false;emit('update:references',props.references.filter(item=>!item.session_id||item.session_id===props.sessionId))})
watch(()=>state.boot?.materials,()=>{if(picker.value)load()})
defineExpose({focus:()=>input.value?.focus()})
</script>
<template>
<div class="citation-entry-composer">
 <div v-if="references.length" class="citation-attached-list" aria-label="本次引用内容">
  <div v-for="reference in references" :key="reference.key" class="citation-attached-card">
   <img :src="icon('file-text')" alt="">
   <div><strong>引用：{{ reference.title }}</strong><small>来源：{{ reference.source }}<span v-if="reference.snippet"> · {{ reference.snippet }}</span></small></div>
   <button type="button" :aria-label="'移除引用：'+reference.title" :disabled="busy" @click="remove(reference.key)"><img :src="icon('close')" alt=""></button>
  </div>
 </div>
 <ReferencePicker v-if="picker" ref="referencePicker" :items="candidates" :selected-keys="selectedKeys" :loading="loading" :error="pickerError" :can-retry="loadFailed" @select="selectKeys" @close="closePicker" @attach="attach" @retry="load"/>
 <form class="citation-input-box" @submit.prevent="emit('send')">
  <textarea ref="input" :value="modelValue" aria-label="围绕引用提问" rows="3" maxlength="6000" placeholder="输入你的问题…" :disabled="busy" @input="emit('update:modelValue',$event.target.value)" @keydown.ctrl.enter.prevent="event=>{if(!event.isComposing&&!busy)emit('send')}"></textarea>
  <p v-if="error" class="inline-error" role="alert">{{ error }}</p>
  <footer>
   <div class="citation-input-tools"><button type="button" ref="attachmentTrigger" class="citation-attachment-button" aria-label="加入附件资料" title="导入 TXT 或 Markdown 资料" :disabled="busy" @click="attach"><img :src="icon('paperclip')" alt=""></button><button type="button" ref="referenceTrigger" class="citation-reference-button" :aria-expanded="picker" :disabled="busy" @click="openPicker"><span>@</span> 引用资料</button></div>
   <small>{{ modelValue.length }}/6000</small><button v-if="busy&&canStop" type="button" class="citation-send-button" aria-label="停止生成" @click="emit('stop')"><span aria-hidden="true" style="width:14px;height:14px;border-radius:2px;background:currentColor"></span>停止</button><button v-else class="citation-send-button" :aria-busy="busy" :disabled="busy||!modelValue.trim()"><img :src="icon('send','white')" alt="">{{ busy?'回答中…':'发送' }}</button>
  </footer>
 </form>
</div>
</template>
