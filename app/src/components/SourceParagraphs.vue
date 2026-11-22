<script setup>
import {computed,nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import RecordPagination from './ui/RecordPagination.vue'
import {sourcePages,sourcePageForParagraph} from '../sourcePages.js'
const props=defineProps({text:{type:String,default:''},paragraph:{type:Number,default:0},query:{type:String,default:''},pageChars:{type:Number,default:600}})
const root=ref(null),highlight=ref(0),requested=ref(0),page=ref(1)
const paragraphs=computed(()=>props.text.split(/\n\s*\n/).map(s=>s.trim()).filter(Boolean))
const pages=computed(()=>sourcePages(props.text,{maxChars:props.pageChars,maxParagraphs:4}))
const rows=computed(()=>pages.value[page.value-1]||[])
let timer
async function locate(value){requested.value=Number(value)||0;highlight.value=0;clearTimeout(timer);if(requested.value<1||requested.value>paragraphs.value.length)return;page.value=sourcePageForParagraph(pages.value,requested.value);highlight.value=requested.value;await nextTick();root.value?.querySelector(`[data-source-paragraph="${requested.value}"]`)?.scrollIntoView({block:'nearest',behavior:'auto'});timer=setTimeout(()=>highlight.value=0,2000)}
function parts(text){const q=props.query.trim();if(!q)return [{text,hit:false}];const out=[];let from=0,index;while((index=text.toLowerCase().indexOf(q.toLowerCase(),from))>=0){out.push({text:text.slice(from,index),hit:false},{text:text.slice(index,index+q.length),hit:true});from=index+q.length}out.push({text:text.slice(from),hit:false});return out}
function initialLocation(){return props.paragraph||(props.query.trim()?paragraphs.value.findIndex(text=>text.toLowerCase().includes(props.query.trim().toLowerCase()))+1:0)}
watch(()=>[props.text,props.paragraph,props.pageChars,props.query],()=>{page.value=1;locate(initialLocation())})
watch(page,()=>{nextTick(()=>{const body=root.value?.querySelector('.source-paragraphs');if(body)body.scrollTop=0})})
onMounted(()=>locate(initialLocation()));onUnmounted(()=>clearTimeout(timer))
defineExpose({locate})
</script>
<template><div ref="root" class="source-text-pages"><p v-if="requested" class="source-location-note" role="status"><span>{{ requested<=paragraphs.length?'已定位到第'+requested+'段':'引用段落不在当前内容中' }}</span><button v-if="requested<=paragraphs.length" @click="locate(requested)">再次定位</button></p><div class="source-paragraphs"><section v-for="row in rows" :key="row.number+'-'+row.part" :data-source-paragraph="row.number" :class="['source-paragraph',{located:highlight===row.number}]"><span aria-hidden="true">{{ row.number }}<small v-if="row.parts>1">{{ row.part }}/{{ row.parts }}</small></span><div class="raw-source-text"><template v-for="(part,i) in parts(row.text)" :key="i"><mark v-if="part.hit">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></div></section></div><RecordPagination v-model="page" :total="pages.length" :page-size="1" :summary="'共 '+paragraphs.length+' 段 · 第 '+page+' / '+pages.length+' 页'" label="来源原文"/></div></template>
