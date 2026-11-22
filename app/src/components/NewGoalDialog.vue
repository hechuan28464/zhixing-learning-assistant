<script setup>
import {computed,ref} from 'vue'
import {useDialogFocus} from '../useDialogFocus.js'
import {api,useLearning} from '../useLearning.js'
import {prepareWrite} from '../retryRequest.js'
const {state,refresh,openSession}=useLearning()
const emit=defineEmits(['created'])
const dialog=ref(null),discardDialog=ref(null),discard=ref(false),busy=ref(false),error=ref(''),createdSpace=ref(null)
const form=ref({goal:state.goalSeed||'',domain:'',foundation:'',daily_minutes:state.boot?.profile?.daily_minutes||30})
const initial=JSON.stringify(form.value)
const dirty=computed(()=>JSON.stringify(form.value)!==initial)
let request=null
useDialogFocus(dialog);useDialogFocus(discardDialog)
function close(){if(busy.value)return;discard.value=false;state.newGoal=false;state.goalSeed=''}
function requestClose(){if(busy.value)return;if(dirty.value&&!createdSpace.value){discard.value=true;return}close()}
async function create(){
  if(busy.value||!form.value.goal.trim())return
  busy.value=true;error.value=''
  try{
    const payload={...form.value,title:form.value.goal.split(/\r?\n/)[0].trim().slice(0,40)}
    request=prepareWrite(request,payload)
    const space=createdSpace.value||await api('/sessions',{method:'POST',body:{...payload,request_id:request.key}})
    createdSpace.value=space
    await refresh();await openSession(space.id)
    busy.value=false;close();emit('created',space)
  }catch(e){error.value=(createdSpace.value?'目标已创建，重试只恢复入口。':'暂时未能确认创建结果，输入已保留，可以重试。')+' '+e.message}
  finally{busy.value=false}
}
</script>
<template>
<dialog ref="dialog" class="form-dialog" @cancel.prevent="requestClose" @click="event=>{if(event.target===dialog)requestClose()}">
  <button class="dialog-close" aria-label="关闭新建目标" :disabled="busy" @click="requestClose">×</button>
  <div class="dialog-intro"><span>从你的问题出发</span><h2>今天，想学会什么？</h2><p>不限学科。先写清希望能做什么，路线可以稍后一起调整。</p></div>
  <form :aria-busy="busy" @submit.prevent="create">
    <label>学习目标<textarea v-model="form.goal" :disabled="busy||!!createdSpace" required maxlength="2000" rows="3" placeholder="例如：能读懂一份统计图表，并解释其中的结论"></textarea></label>
    <div class="form-two"><label>主题或学科<input v-model="form.domain" :disabled="busy||!!createdSpace" maxlength="100" placeholder="可以跨学科，也可以暂时不填"></label><label>每天可用时间<select v-model.number="form.daily_minutes" :disabled="busy||!!createdSpace"><option :value="15">15 分钟</option><option :value="30">30 分钟</option><option :value="45">45 分钟</option><option :value="60">60 分钟</option></select></label></div>
    <label>已有基础<input v-model="form.foundation" :disabled="busy||!!createdSpace" maxlength="500" placeholder="学过什么、哪里不熟悉，留空也可以"></label>
    <p v-if="error" class="inline-error" role="alert">{{ error }}</p>
    <div class="dialog-actions"><button type="button" class="secondary-button" :disabled="busy" @click="requestClose">稍后再说</button><button class="primary-button" :disabled="busy||!form.goal.trim()">{{ busy?'创建中…':createdSpace?'恢复已创建的目标':error?'重试创建':'创建学习空间' }}</button></div>
  </form>
</dialog>
<dialog v-if="discard" ref="discardDialog" class="form-dialog goal-discard-dialog" @cancel.prevent="discard=false"><div class="dialog-intro"><span>保留你的想法</span><h2>放弃尚未保存的目标？</h2><p>继续填写会保留当前内容，放弃后关闭填写窗口。</p></div><div class="dialog-actions"><button autofocus class="primary-button" @click="discard=false">继续填写</button><button class="secondary-button" @click="close">放弃填写</button></div></dialog>
</template>
