<script setup>
import RecordPagination from "./ui/RecordPagination.vue"
import {usePagination} from "../usePagination.js"
import {requestId as newRequestId} from '../requestId.js'

import {computed,nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import {api,useLearning} from '../useLearning.js'
import {artwork,icon} from '../assets.js'
import {pageArtwork} from '../pageArtwork.js'
import MessageBody from './MessageBody.vue'
import SourceParagraphs from './SourceParagraphs.vue'
import {displayLocator} from '../sourceLocator.js'
import CitationComposer from './CitationComposer.vue'
const props=defineProps({entry:Object})
const emit=defineEmits(['close','changed','read','new-goal','attach'])
const {state,executeTaskAction}=useLearning()
const history=ref([]),draft=ref(''),error=ref(''),busy=ref(false),loading=ref(false),references=ref(props.entry.archived?[]:[props.entry]),conversation=ref(null),composer=ref(null),showGuide=ref(true)
const sessionId=ref(props.entry.session_id||state.current?.id||state.boot?.sessions?.[0]?.id||'')
const suggestions=[['search','这句话的证据有哪些？'],['scale','如何判断一个陈述是事实还是判断？'],['help-circle','在什么情况下它可能不成立？'],['lightbulb','这句话包含哪些隐含假设？'],['book-open','能举一个生活中的例子吗？'],['network','和相关的其他观点有什么区别？']]
let version=0,previous=null,disposed=false,chatController=null,chatStopped=false
async function stop(){
 if(!chatController||!previous)return
 chatStopped=true
 const pending=api('/sessions/'+sessionId.value+'/chat/cancel',{method:'POST',body:{request_id:previous.key},timeoutMs:10000}).catch(()=>null)
 chatController.abort();await pending
}
async function load(){const rev=++version;history.value=[];error.value='';if(!sessionId.value||state.designPreview)return;loading.value=true;try{const s=await api('/sessions/'+sessionId.value);if(!disposed&&rev===version){history.value=s.messages;showGuide.value=!s.messages.length}}catch(e){if(rev===version)error.value=e.message}finally{if(rev===version)loading.value=false}}
function suggest(text){draft.value=text;composer.value?.focus()}
async function send(){
 if(!draft.value.trim()||!sessionId.value||busy.value)return
 const text=draft.value,sid=sessionId.value,refs=references.value.map(item=>item.key),signature=JSON.stringify([sid,text,refs])
 const key=previous?.signature===signature?previous.key:newRequestId();previous={signature,key};busy.value=true;error.value=''
 draft.value='';chatStopped=false;chatController=new AbortController()
 history.value.push({id:'sending-'+key,role:'user',content:text,metadata:{references:references.value}});showGuide.value=false
 await nextTick();if(conversation.value)conversation.value.scrollTop=conversation.value.scrollHeight
 try{
  const reply=await api('/sessions/'+sid+'/chat',{method:'POST',body:{message:text,request_id:key,reference_ids:refs},signal:chatController.signal,timeoutMs:300000})
  const s=await api('/sessions/'+sid);if(disposed)return;history.value=s.messages;draft.value='';previous=null
  await nextTick();if(conversation.value)conversation.value.scrollTop=conversation.value.scrollHeight
  if(reply.assistance_id)await api('/sessions/'+sid+'/assistance/'+reply.assistance_id+'/ack',{method:'POST'})
  emit('changed')
 }catch(e){if(!disposed){if(!chatStopped){error.value=e.message;if(!draft.value)draft.value=text}const s=await api('/sessions/'+sid).catch(()=>null);if(s)history.value=s.messages}}
 finally{busy.value=false;chatController=null}
}
watch(sessionId,load)
onMounted(()=>{window.scrollTo(0,0);load()})
onUnmounted(()=>{disposed=true;++version})
const chatRecords=computed(()=>history.value)
const {page:chatPage,items:chatRows}=usePagination(chatRecords,()=>sessionId.value)
watch(()=>chatRecords.value.length,n=>{chatPage.value=Math.max(1,Math.ceil(n/10))},{immediate:true})
</script>
<template>
<section class="citation-discussion-page" aria-labelledby="citation-page-title">
 <header class="citation-page-heading"><p>知识图谱 / 知识空间 / 围绕资料讨论</p><h1 id="citation-page-title">围绕资料，与林知讨论。</h1><p>基于可靠的资料来源，提出问题、澄清概念、探索更多视角。</p></header>
 <div class="citation-page-workspace"><article class="citation-page-source"><div class="citation-source-toolbar"><button class="text-button" @click="emit('close')">‹ 返回知识空间</button><button class="secondary-button" @click="emit('read',entry)">全屏阅读</button></div><a v-if="entry.video_id" class="text-button" :href="'/app?view=videos&amp;video='+entry.video_id">‹ 回到这份视频资料</a><div class="citation-source-heading"><h2>{{ entry.title }}</h2><button class="secondary-button" @click="emit('read',entry)">打开原文</button></div><span v-if="entry.evidence_label" class="source-evidence-type">{{ entry.evidence_label }}</span><p class="citation-source-meta">来源：{{ entry.source }}<span>保存时间：{{ new Date(entry.updated_at).toLocaleString('zh-CN') }}</span></p><blockquote class="citation-page-quote"><span>“</span>{{ entry.text?.split('\n').filter(Boolean)[0]||'来源已归档' }}</blockquote><div v-if="entry.archived" class="source-archived">来源已归档，无法定位。<button class="text-button" @click="emit('close')">返回知识空间</button></div><div v-else class="citation-page-document"><SourceParagraphs :text="entry.text" :page-chars="360" :paragraph="entry.paragraph||0"/></div><footer>当前展示实际保存的原文。引用会随问题一起保留，便于后续核查。</footer></article>
 <section class="citation-page-right" aria-label="与林知讨论"><div class="citation-mentor-area" :style="{backgroundImage:`url(/assets/competition-v1/citation/mountains.png.webp),url(${pageArtwork.buddy.scene})`}"><div class="citation-mentor-scenery" aria-hidden="true"><img class="discussion-platform" src="/assets/competition-v1/citation/terrace.png.webp" alt=""><img class="discussion-lamp" src="/assets/competition-v1/citation/lamp.png.webp" alt=""><img class="discussion-books" src="/assets/competition-v1/pbl/books.png.webp" alt=""><img class="discussion-cups" src="/assets/competition-v1/citation/cups.png.webp" alt=""></div><header><img :src="artwork.mentor" alt="林知导师"><div><h2>林知 <span>学习伙伴</span></h2><p>善于启发思考，陪你一起理解与成长。</p></div><button class="citation-guide-toggle" :aria-expanded="showGuide" @click="showGuide=!showGuide">讨论指引 {{ showGuide?'⌃':'⌄' }}</button></header><label v-if="!entry.session_id" class="citation-save-target">保存到<select v-model="sessionId" :disabled="busy||!!entry.session_id"><option value="" disabled>选择学习空间</option><option v-for="space in state.boot?.sessions||[]" :value="space.id" :key="space.id">{{ space.title }}</option></select></label><div v-if="!history.length && !loading" class="citation-welcome"><img :src="artwork.mentor" alt="林知"><div><h3>你想核查哪一句话？</h3><p>我们可以一起梳理这句话的含义，看看它依赖哪些证据，以及在什么情况下可能不成立。</p></div></div><section v-if="showGuide" class="citation-guidance" aria-label="讨论指引"><h3>你可以这样提问：</h3><div><button v-for="[glyph,text] in suggestions" :key="text" :disabled="busy" @click="suggest(text)"><img :src="icon(glyph)" alt=""><span>{{ text }}</span><img :src="icon('chevron-right')" alt=""></button></div></section></div>
 <section class="citation-page-chat"><div v-if="!sessionId" class="knowledge-empty"><h3>先选一个保存讨论的目标</h3><p>之后可以从知识空间检索这次对话。</p><button class="primary-button" @click="emit('new-goal')">创建学习目标</button></div><div v-if="loading||history.length||busy" ref="conversation" class="citation-page-history" role="log" aria-label="当前讨论记录" aria-live="polite"><p v-if="loading" class="citation-wait">正在读取实际对话…</p><article v-for="message in chatRows" :key="message.id" :class="['citation-page-message',message.role]"><img v-if="message.role==='assistant'" :src="artwork.mentor" alt="林知"><div><strong>{{ message.role==='user'?'我':'林知' }}</strong><div v-for="reference in message.metadata?.references||[]" :key="reference.key" class="sent-citation">引用：{{ reference.title }}</div><MessageBody :text="message.content"/><button v-if="message.role==='assistant'&&message.metadata?.next_action?.task_id" class="secondary-button agent-next-action" :disabled="busy||state.chatBusy" @click="executeTaskAction({...message.metadata.next_action,sessionId:message.metadata.next_action.session_id})">{{ message.metadata.next_action.title }}</button><details v-if="message.metadata?.sources?.length"><summary>参考来源</summary><button v-for="source in message.metadata.sources" :key="source.title+source.locator" class="source-citation-link" :disabled="!source.key" @click="emit('read',{...source,key:source.key})">{{ source.title }} · {{ displayLocator(source) }}</button></details></div></article><p v-if="busy" class="citation-wait" role="status">林知正在读取学习记录和所选内容…</p></div>
 <RecordPagination v-model="chatPage" :total="chatRecords.length" label="资料讨论"/><CitationComposer ref="composer" v-model="draft" v-model:references="references" :session-id="sessionId" :busy="busy" :can-stop="busy" :error="error" @send="send" @stop="stop" @attach="emit('attach',$event)"/></section>
 </section></div>
</section>
</template>
