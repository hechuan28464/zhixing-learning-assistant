<script setup>
import {useDialogFocus} from '../useDialogFocus.js'
import { computed, onMounted, ref } from 'vue'
import { icon } from '../assets.js'
import SourceParagraphs from './SourceParagraphs.vue'
const props=defineProps({entry:Object,query:{type:String,default:''},canArchive:Boolean,canDiscuss:{type:Boolean,default:true},returnLabel:{type:String,default:'返回知识空间'},paragraph:{type:Number,default:0}})
const emit=defineEmits(['close','discuss','archive'])
const dialog=ref(null),copied=ref(false)
const parts=computed(()=>{
  const text=props.entry?.text||'',q=props.query.trim()
  if(!q)return [{text,hit:false}]
  const lower=text.toLowerCase(),needle=q.toLowerCase(),out=[];let start=0,index
  while((index=lower.indexOf(needle,start))>=0){out.push({text:text.slice(start,index),hit:false},{text:text.slice(index,index+q.length),hit:true});start=index+q.length}
  out.push({text:text.slice(start),hit:false});return out
})
async function copy(){try{await navigator.clipboard.writeText(props.entry.title+'\n'+props.entry.text+'\n来源：'+props.entry.source);copied.value=true}catch{copied.value=false}}
useDialogFocus(dialog)
</script>
<template>
<dialog ref="dialog" class="knowledge-reader" aria-labelledby="source-reader-title" @cancel.prevent="emit('close')">
  <header class="source-reader-top"><span><img :src="icon('file-text')" alt="">原文阅读</span><button class="dialog-close" aria-label="关闭原文阅读" @click="emit('close')">×</button></header>
  <div class="source-reader-layout"><article class="source-document"><span class="knowledge-type">{{ entry.type_label }}</span><h1 id="source-reader-title">{{ entry.title }}</h1><span v-if="entry.evidence_label" class="source-evidence-type">{{ entry.evidence_label }}</span><p class="source-document-meta">{{ entry.source }} · {{ entry.space_title }}</p><div v-if="entry.archived" class="source-archived"><strong>来源已归档，无法定位</strong><p>原引用仍保留出处，可返回知识空间查看其他资料。</p><button class="secondary-button" @click="emit('close')">{{ returnLabel }}</button></div><SourceParagraphs v-else :text="entry.text" :query="query" :paragraph="paragraph||entry.paragraph||0"/></article>
  <aside class="source-reader-aside"><a v-if="entry.video_id" class="text-button" :href="'/app?view=videos&amp;video='+entry.video_id">回到视频与字幕</a><img class="source-reader-art" src="/assets/competition-v1/citation/magnifier.png.webp" alt="" @error="$event.target.hidden=true"><h2>原文信息</h2><dl><dt>来源</dt><dd>{{ entry.source }}</dd><dt>所属空间</dt><dd>{{ entry.space_title }}</dd><dt>保存时间</dt><dd>{{ new Date(entry.updated_at).toLocaleString('zh-CN') }}</dd></dl><p>{{ canDiscuss?'讨论时会保留这条内容的引用，方便随时核查。':'原文与保存时间属于这一版本，便于核对实际产物。' }}</p><button v-if="canDiscuss" class="primary-button" :disabled="entry.archived" @click="emit('discuss',entry)">加入讨论</button><button class="secondary-button" :disabled="entry.archived" @click="copy">{{ copied?'已复制引用':'复制原文与来源' }}</button><button v-if="canArchive" class="text-button" @click="emit('archive',entry)">归档这份资料</button><button class="text-button" @click="emit('close')">{{ returnLabel }}</button></aside></div>
</dialog>
</template>
