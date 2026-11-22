<script setup>
import RecordPagination from './ui/RecordPagination.vue'
import {usePagination} from '../usePagination.js'
import {computed,onMounted,ref,watch} from 'vue'
import {api,useLearning} from '../useLearning.js'
import {icon} from '../assets.js'
import SourceReader from './SourceReader.vue'
import {readLibraryMetadata} from '../libraryQuery.js'
const emit=defineEmits(['add-material','discuss'])
const {state,refresh,notify}=useLearning()
const items=ref([]),scope=ref(''),reader=ref(null),error=ref(''),loading=ref(false),archived=ref(false)
let version=0
async function load(){const v=++version;loading.value=true;error.value='';try{const data=await readLibraryMetadata(api,{kind:'material'});if(v===version)items.value=data.items}catch(e){if(v===version)error.value=e.message}finally{if(v===version)loading.value=false}}
const shelves=computed(()=>{const map=new Map();for(const entry of items.value){const key=entry.session_id||'public';if(!map.has(key))map.set(key,{id:key,title:entry.space_title,entries:[],image:'shelf-method'});map.get(key).entries.push(entry)}return [...map.values()].map(group=>{const course=state.boot?.sessions.find(s=>s.id===group.id)?.course_id;return {...group,image:course==='programming'?'shelf-science':course==='mathematics'?'shelf-method':course==='reading'?'shelf-history':group.id==='public'?'shelf-life':'shelf-society'}})})
const visible=computed(()=>items.value.filter(e=>(!scope.value||(e.session_id||'public')===scope.value)&&[e.title,e.snippet,e.source].join(' ').toLowerCase().includes(state.query.trim().toLowerCase())))
async function read(entry){try{reader.value=await api('/knowledge/entry?'+new URLSearchParams({key:entry.key}))}catch(e){error.value=e.message}}
function discuss(entry){reader.value=null;emit('discuss',entry)}
async function archive(entry){try{await api('/materials/'+entry.key.slice('material:'.length),{method:'DELETE'});reader.value=null;await refresh();notify('资料已归档，可以从已归档列表恢复。')}catch(e){error.value=e.message}}
async function restore(identifier){try{await api('/materials/'+identifier+'/restore',{method:'POST'});await refresh();notify('资料已恢复。')}catch(e){error.value=e.message}}
watch(()=>state.boot?.materials,load)
onMounted(load)
const {page:sourcePage,items:sourceRows}=usePagination(visible,()=>[scope.value,state.query])
const {page:archivePage,items:archiveRows}=usePagination(()=>state.boot?.archived_materials||[])
</script>
<template><section class="reading-library-live"><div class="section-heading"><h2>我的书架</h2><button class="text-button" @click="archived=!archived">{{ archived?'返回当前书架':'已归档资料' }}</button><button class="text-button" @click="scope=''">查看全部</button></div><p class="section-description">按实际学习空间整理已导入资料和已开始课程的自编讲义。</p><div v-if="archived" class="reading-archive-list"><p v-if="!state.boot.archived_materials.length">还没有归档资料。</p><button v-for="item in archiveRows" :key="item.id" class="secondary-button" @click="restore(item.id)">{{ item.title }} · 恢复资料</button><RecordPagination v-model="archivePage" :total="state.boot.archived_materials.length" label="归档资料"/></div><div v-else class="reading-shelves"><button v-for="shelf in shelves" :key="shelf.id" :class="{active:scope===shelf.id}" @click="scope=scope===shelf.id?'':shelf.id"><img :src="'/assets/split-elements/scenes/'+shelf.image+'.png'" alt=""><strong>{{ shelf.title }}</strong><small>{{ shelf.entries.length }} 份实际资料</small></button><button class="reading-add-shelf" @click="emit('add-material')"><span>＋</span><strong>加入资料</strong><small>TXT、Markdown 或文字摘录</small></button></div><div v-if="!archived" class="reading-detail-grid"><section><div class="section-heading"><h2>{{ scope?'书架中的资料':'可以继续阅读' }}</h2><small>{{ visible.length }} 份</small></div><p v-if="loading" role="status">正在读取资料…</p><p v-if="error" class="inline-error">{{ error }}</p><div class="reading-source-list"><button v-for="entry in sourceRows" :key="entry.key" @click="read(entry)"><img :src="icon('file-text')" alt=""><div><h3>{{ entry.title }}</h3><p>{{ entry.snippet }}</p><small>{{ entry.source }} · {{ entry.space_title }}</small></div><img :src="icon('chevron-right')" alt=""></button></div><RecordPagination v-model="sourcePage" :total="visible.length" label="阅读资料"/><div v-if="!loading&&!visible.length" class="studio-empty-soft"><h3>给自己的问题，找一份可靠材料。</h3><p>可以导入讲义、自己的课程笔记或文章摘录。</p><button class="primary-button" @click="emit('add-material')">加入第一份资料</button></div></section><aside><section class="reading-reflection-card"><span>“</span><h3>读完之后，留下一个可以继续追问的问题。</h3><p>这句话如何核查？它在什么条件下成立？还需要什么证据？</p></section><section class="studio-side-card"><h2>让材料参与讨论</h2><p>打开原文后选择“加入讨论”，引用会跟随问题保留。</p><button v-if="visible[0]" class="secondary-button" @click="read(visible[0])">从一份材料开始</button></section></aside></div><SourceReader v-if="reader" :entry="reader" :query="state.query" :can-archive="!reader.published" @archive="archive" @close="reader=null" @discuss="discuss"/></section></template>
