<script setup>
import RecordPagination from "./ui/RecordPagination.vue"
import {usePagination} from "../usePagination.js"
import { computed, ref, watch, nextTick } from 'vue'
import { artwork, icon } from '../assets.js'
import { api, useLearning } from '../useLearning.js'
import SourceReader from './SourceReader.vue'
import {displayLocator} from '../sourceLocator.js'
import MessageBody from './MessageBody.vue'
import CitationComposer from './CitationComposer.vue'
const props=defineProps({ expanded: Boolean,disabled:Boolean })
const emit=defineEmits(['add-material'])
const { state, currentLesson, sendChat,stopChat,executeTaskAction } = useLearning()
const draft = ref(''), scroll = ref(null),references=ref([]),reader=ref(null),sourceError=ref(''),composer=ref(null)
async function readSource(source){if(!source.key)return;sourceError.value='';try{reader.value={...await api('/knowledge/entry?'+new URLSearchParams({key:source.key,session_id:state.current.id})),paragraph:source.paragraph||0}}catch(e){sourceError.value=e.message}}
watch(() => state.current?.id, (id) => { draft.value = id ? localStorage.getItem('zhixing.chat-draft.' + id) || '' : '' }, { immediate: true })
watch(draft, value => { if (state.current && !state.designPreview) localStorage.setItem('zhixing.chat-draft.' + state.current.id, value) })
watch(() => state.current?.messages?.length, async () => { await nextTick(); if (scroll.value) scroll.value.scrollTop = scroll.value.scrollHeight })
async function send() {
 if(props.disabled||state.chatBusy)return
 const value=draft.value.trim(),sid=state.current?.id;if(!value)return
 draft.value=''
 const sent=await sendChat(value,references.value.map(item=>item.key))
 if(!sent&&!draft.value&&(!sid||state.current?.id===sid))draft.value=value
}
function suggest(text) { if(props.disabled||state.chatBusy)return;draft.value = text;nextTick(()=>composer.value?.focus()) }
function retry(message){if(state.chatBusy)return;draft.value=message.content;send()}
defineExpose({suggest})
watch(()=>state.current?.id,()=>{references.value=[]})
const chatRecords=computed(()=>state.current?.messages||[])
const {page:chatPage,items:chatRows}=usePagination(chatRecords,()=>state.current?.id)
watch(()=>chatRecords.value.length,n=>{chatPage.value=Math.max(1,Math.ceil(n/10))},{immediate:true})
</script>
<template><section :class="['tutor-panel-live',{expanded}]"><header class="tutor-header"><img :src="artwork.mentor" alt="林知导师"><div><h2>林知</h2><span>陪你理解，也陪你动手</span></div><span class="service-dot" :title="state.boot?.model?.enabled ? (state.boot?.model?.configured ? '模型已配置' : '模型未配置') : 'AI 暂未开启'"></span></header><div ref="scroll" class="conversation" role="log" aria-label="与林知的对话" aria-live="polite"><div v-if="!state.current?.messages?.length" class="tutor-empty"><img class="tutor-empty-art" src="/assets/competition-v1/lesson/tutor-empty.png.webp" alt=""><h3>从一个具体的问题开始</h3><p>可以告诉我哪里没懂，或让我结合当前材料换一种讲法。</p><button :disabled="state.chatBusy||disabled" @click="suggest('先用一个生活中的例子，讲解当前学习目标。')">用一个例子讲给我听</button><button :disabled="state.chatBusy||disabled" @click="suggest('请读取当前讲义，帮我找到最需要先理解的前置知识。')">帮我找出需要的前置知识</button><div v-if="currentLesson" class="tutor-current-source"><button class="source-citation-link" @click="readSource({key:'material:'+state.current.id+'/'+currentLesson.id,paragraph:1})">当前讲义：{{ currentLesson.title }} · 第1段</button><p>{{ currentLesson.sections[0]?.text.slice(0,92) }}{{ currentLesson.sections[0]?.text.length>92?'…':'' }}</p></div></div><article v-for="message in chatRows" :key="message.id" :class="['chat-message',message.role]"><div class="chat-author">{{ message.role === 'user' ? state.boot?.profile?.name || '我' : '林知' }}</div><MessageBody :text="message.content"/><div v-if="message.role==='user'&&['failed','cancelled'].includes(message.metadata?.turn_status)" class="chat-turn-status" role="status"><span>{{message.metadata.turn_status==='cancelled'?'这次回答已停止':'这次回答未完成，问题已保留'}}</span><button type="button" class="text-button" :disabled="state.chatBusy" @click="retry(message)">重新发送</button></div><button v-if="message.role==='assistant'&&message.metadata?.next_action?.task_id" class="secondary-button agent-next-action" :disabled="state.chatBusy" @click="executeTaskAction({...message.metadata.next_action,sessionId:message.metadata.next_action.session_id})">{{ message.metadata.next_action.title }}</button><details v-if="message.role==='assistant' && message.metadata?.tools?.length" class="tool-receipts"><summary>本次参考与操作 · {{ message.metadata.tools.length }} 项</summary><p v-for="(tool,i) in message.metadata.tools" :key="i">{{ tool.ok ? '✓' : '○' }} {{ tool.label }}</p><button v-for="(source,i) in message.metadata.sources || []" :key="'s'+i" class="source-citation-link" :disabled="!source.key" @click="readSource(source)">{{ source.title }} · {{ displayLocator(source) }}</button></details></article><div v-if="state.chatBusy && state.chatSession===state.current?.id" class="thinking-indicator"><span></span><span></span><span></span><small>正在结合学习记录与材料整理回答</small></div></div><RecordPagination v-model="chatPage" :total="chatRecords.length" label="学习对话"/><CitationComposer ref="composer" v-model="draft" v-model:references="references" :session-id="state.current?.id||''" :busy="state.chatBusy||disabled" :can-stop="state.chatBusy" :error="state.chatError" @send="send" @stop="stopChat" @attach="emit('add-material',$event)"/><p class="tutor-footnote">导师会使用当前空间的记录与资料。回答可核查，学习状态以任务证据为准。</p><p v-if="sourceError" role="alert" class="inline-error">{{ sourceError }}</p><SourceReader v-if="reader" :entry="reader" return-label="返回学习" @close="reader=null" @discuss="entry=>{references=[entry];reader=null;draft='请结合这份资料解释当前问题。'}"/></section></template>

<style scoped>
.chat-turn-status{display:flex;align-items:center;gap:14px;margin-top:12px;color:#956326;font-size:13px;line-height:1.6}.chat-turn-status button{text-decoration:underline}
</style>
