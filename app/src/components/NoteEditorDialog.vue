<script setup>
import {requestId as newRequestId} from '../requestId.js'

import {computed,nextTick,ref} from 'vue'
import {useForm} from 'vee-validate'
import {DialogRoot,DialogPortal,DialogOverlay,DialogContent,DialogTitle,DialogDescription} from 'reka-ui'
import {api} from '../useLearning.js'
import {requiredText} from '../fieldRules.js'
import FormField from './ui/FormField.vue'
import DiscardChangesDialog from './ui/DiscardChangesDialog.vue'
const props=defineProps({note:{type:Object,default:null},sessionId:{type:String,default:null}})
const emit=defineEmits(['close','saved'])
const opener=document.activeElement
const {values,meta,errors,isSubmitting,handleSubmit,resetForm}=useForm({initialValues:{title:props.note?.title||'',text:props.note?.text||''},validationSchema:{title:requiredText('标题',150),text:requiredText('内容',120000)}})
const failure=ref(''),discard=ref(false)
let submission=null
const canSave=computed(()=>meta.value.dirty&&!!values.title?.trim()&&!!values.text?.trim()&&!Object.keys(errors.value).length&&!isSubmitting.value)
const phase=computed(()=>isSubmitting.value?'submitting':failure.value?'error':!meta.value.dirty?'idle':Object.keys(errors.value).length?'invalid':canSave.value?'ready':'editing')
function focusTitle(event){event.preventDefault();nextTick(()=>document.querySelector('.studio-editor-dialog input[name=title]')?.focus())}
function requestClose(){if(isSubmitting.value)return;if(meta.value.dirty){discard.value=true;return}emit('close')}
function escape(event){event.preventDefault();if(!event.isComposing)requestClose()}
function restoreFocus(event){event.preventDefault();if(opener?.isConnected)opener.focus({preventScroll:true})}
const save=handleSubmit(async fields=>{
 if(isSubmitting.value&&submission?.running)return
 failure.value=''
 const payload={title:fields.title,text:fields.text,session_id:props.note?props.note.session_id:props.sessionId}
 const signature=JSON.stringify(payload)
 if(!submission||submission.signature!==signature)submission={signature,key:newRequestId(),running:false}
 submission.running=true
 try{
  const result=await api('/notes'+(props.note?'/'+props.note.id:''),{method:props.note?'PATCH':'POST',body:props.note?payload:{...payload,request_id:submission.key}})
  resetForm({values:fields});emit('saved',result);emit('close')
 }catch(e){failure.value=e.message}
 finally{if(submission)submission.running=false}
})
function submit(event){event.preventDefault();if(isSubmitting.value)return;return save(event)}
</script>
<template><DialogRoot :open="true" @update:open="value=>{if(!value)requestClose()}"><DialogPortal to=".studio-shell"><DialogOverlay class="studio-editor-overlay"/><DialogContent class="form-dialog studio-editor-dialog" @open-auto-focus="focusTitle" @escape-key-down="escape" @interact-outside.prevent="requestClose" @close-auto-focus="restoreFocus"><button type="button" class="dialog-close" aria-label="关闭笔记" :disabled="isSubmitting" @click="requestClose">×</button><div class="dialog-intro"><span>把理解，写成自己的话</span><DialogTitle as="h2">{{ note?'继续这则笔记':'写一则灵感笔记' }}</DialogTitle><DialogDescription>留下自己的解释、疑问，或下次想核查的证据。</DialogDescription></div><form novalidate :aria-busy="isSubmitting" :data-form-state="phase" @submit="submit"><fieldset :disabled="isSubmitting" class="studio-editor-fields"><FormField name="title" label="标题" required :maxlength="150" placeholder="给这个想法起个名字"/><FormField name="text" label="内容" as="textarea" required :maxlength="120000" :rows="8" hint="可以不完整，重要的是保留自己的思考。" placeholder="我理解了什么，哪里仍不确定，下次如何检查…"/></fieldset><div v-if="failure" class="studio-submit-error" role="alert"><strong>暂时未能确认保存结果</strong><p>{{ failure }}</p><small>输入已保留，可以直接重试。</small></div><div class="studio-editor-bottom"><p role="status">{{ isSubmitting?'正在保存，请稍候…':failure?'内容已保留，等待重试。':meta.dirty?'有未保存的修改。':'修改后可以保存。' }}</p><div class="dialog-actions"><button type="button" class="secondary-button" :disabled="isSubmitting" @click="requestClose">取消</button><button class="primary-button" :disabled="!canSave" :aria-busy="isSubmitting"><span v-if="isSubmitting" class="studio-submit-spinner" aria-hidden="true"></span>{{ isSubmitting?'保存中…':failure?'重试保存':'保存笔记' }}</button></div></div></form></DialogContent></DialogPortal></DialogRoot><DiscardChangesDialog :open="discard" title="放弃未保存的笔记？" @keep="discard=false" @discard="discard=false;emit('close')"/></template>
