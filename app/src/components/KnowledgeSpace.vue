<script setup>
import RecordPagination from './ui/RecordPagination.vue'
import {usePagination} from '../usePagination.js'
import { computed,nextTick,onMounted,onUnmounted,ref,watch } from 'vue'
import { api,useLearning } from '../useLearning.js'
import {TabsRoot,TabsList,TabsTrigger,TabsContent} from 'reka-ui'
import { icon } from '../assets.js'
import {splitAsset} from '../splitArtwork.js'
import { pageArtwork } from '../pageArtwork.js'
import KnowledgeGraph from './KnowledgeGraph.vue'
import SourceReader from './SourceReader.vue'
import CitationDiscussion from './CitationDiscussionPage.vue'
import MemoryConfirmDialog from './MemoryConfirmDialog.vue'
const emit=defineEmits(['add-material','new-goal','open-material'])
const {state,openSession,refresh,notify}=useLearning()
const tab=ref('library'),scope=ref(''),query=ref(''),kind=ref(''),items=ref([]),counts=ref({}),total=ref(0),synced=ref(''),loading=ref(false),error=ref(''),selected=ref(null),detailLoading=ref(false)
const reader=ref(null),discussion=ref(null),confirmation=ref(null),memoryBusy=ref(false),memoryError=ref(''),searchInput=ref(null),zoom=ref(1),includeInactive=ref(false)
const groups=[{id:'material',label:'资料',asset:'library-books',glyph:'file-text',x:50,y:76},{id:'note',label:'笔记',asset:'notes-notebook',glyph:'leaf',x:20,y:27},{id:'record',label:'学习记录',asset:'learning-calendar',glyph:'calendar',x:80,y:27},{id:'conversation',label:'对话',asset:'conversation-figures',glyph:'users',x:14,y:66},{id:'memory',label:'学习记忆',asset:'memory-sprout',glyph:'leaf',x:86,y:66}]
const activeGroup=computed(()=>groups.find(g=>g.id===kind.value))
const resultPage=ref(1)
const memorySuggestions=ref([])
const memoryCandidate=computed(()=>selected.value?.kind==='memory'?selected.value:memorySuggestions.value[0])
const memoryStatus={pending:'待确认',confirmed:'已确认',ignored:'已忽略',revoked:'已撤回'}
const gardenStyle=computed(()=>({backgroundImage:`url(/assets/split-elements/scenes/knowledge-garden-background.png.webp),url(${pageArtwork.graph.scene})`}))
let requestVersion=0,detailVersion=0,debounce,timer,disposed=false
function endpoint(){const p=new URLSearchParams({query:query.value,kind:kind.value,include_inactive:String(includeInactive.value),limit:'10',offset:String((resultPage.value-1)*10)});if(scope.value)p.set('session_id',scope.value);return '/knowledge?'+p}
async function select(entry){
 const version=++detailVersion;detailLoading.value=true;selected.value=null
 try{const p=new URLSearchParams({key:entry.key});if(scope.value)p.set('session_id',scope.value);const data=await api('/knowledge/entry?'+p);if(!disposed&&version===detailVersion)selected.value=data}
 catch(e){if(version===detailVersion)error.value=e.message}
 finally{if(version===detailVersion)detailLoading.value=false}
}
async function load(quiet=false){
 const version=++requestVersion;if(!quiet)loading.value=true;error.value=''
 try{const data=await api(endpoint());if(disposed||version!==requestVersion)return;items.value=data.items;counts.value=data.counts;total.value=data.total;synced.value=data.synced_at;memorySuggestions.value=data.memory_suggestions||[]
   const current=selected.value&&data.items.find(e=>e.key===selected.value.key)
   if(current){if(current.updated_at!==selected.value.updated_at)await select(current)}
   else{selected.value=null;++detailVersion;detailLoading.value=false;if(data.items.length)await select(data.items[0])}
 }catch(e){if(version===requestVersion)error.value=e.message}finally{if(version===requestVersion)loading.value=false}
}
function schedule(){resultPage.value=1;clearTimeout(debounce);++requestVersion;++detailVersion;selected.value=null;detailLoading.value=false;loading.value=true;debounce=setTimeout(()=>load(),220)}
function chooseGroup(id){kind.value=kind.value===id?'':id}
async function readOriginal(entry=selected.value){if(!entry)return;if(state.designPreview&&entry.key==='design-example'){reader.value=entry;return}try{reader.value={...await api('/knowledge/entry?'+new URLSearchParams({key:entry.kind==='memory'?entry.source_key:entry.key,...(scope.value?{session_id:scope.value}:{})})),paragraph:entry.paragraph||0}}catch(e){error.value=e.message}}
function discuss(entry=selected.value){if(!entry)return;reader.value=null;discussion.value=entry}
async function readMemorySource(entry){if(!entry?.source_key)return;try{reader.value=await api('/knowledge/entry?'+new URLSearchParams({key:entry.source_key}))}catch(e){error.value=e.message}}
async function askMemory(entry,action){
 try{const fresh=await api('/knowledge/entry?'+new URLSearchParams({key:entry.key}));confirmation.value={entry:fresh,action};memoryError.value=''}catch(e){error.value=e.message}
}
async function changeMemory(){
 if(!confirmation.value||memoryBusy.value)return
 memoryBusy.value=true;memoryError.value='';const {entry,action}=confirmation.value
 try{await api('/knowledge/memories/'+entry.key.slice('memory:'.length),{method:'POST',body:{action,version:entry.version}});confirmation.value=null;await load(true);await refresh();notify({confirm:'记忆已确认，后续辅导可使用。',ignore:'记忆建议已忽略，原始对话保留。',revoke:'记忆已撤回，后续辅导不再使用。'}[action])}
 catch(e){memoryError.value=e.message}finally{memoryBusy.value=false}
}
async function shortcut(event){if(event.isComposing||document.querySelector('dialog[open],[role=dialog][data-state=open],[role=alertdialog][data-state=open]')||discussion.value)return;if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();tab.value='library';await nextTick();searchInput.value?.focus()}}

function startGoal(){discussion.value=null;emit('new-goal')}
const savedDiscussionKey='zhixing.discussion-source'
async function restoreDiscussion(){
 if(state.designPreview)return
 try{
  const saved=JSON.parse(sessionStorage.getItem(savedDiscussionKey)||'null')
  if(!saved?.key)return
  const params=new URLSearchParams({key:saved.key});if(saved.session_id)params.set('session_id',saved.session_id)
  const entry=await api('/knowledge/entry?'+params)
  if(!disposed&&!discussion.value)discussion.value=entry
 }catch(e){sessionStorage.removeItem(savedDiscussionKey);error.value='上次讨论的来源暂时无法恢复。'+e.message}
}
watch(discussion,entry=>{
 if(state.designPreview)return
 if(entry?.key)sessionStorage.setItem(savedDiscussionKey,JSON.stringify({key:entry.key,session_id:entry.session_id||state.current?.id||null}))
 else sessionStorage.removeItem(savedDiscussionKey)
})
watch([query,kind,scope,includeInactive],schedule)
watch(resultPage,()=>load())
watch(()=>state.boot,()=>load(true))
onMounted(()=>{load();if(state.knowledgeCitation){discussion.value=state.knowledgeCitation;state.knowledgeCitation=null}else restoreDiscussion();document.addEventListener('keydown',shortcut);timer=setInterval(()=>{if(!document.hidden&&!loading.value&&!memoryBusy.value)load(true)},6000)})
onUnmounted(()=>{disposed=true;++requestVersion;++detailVersion;clearTimeout(debounce);clearInterval(timer);document.removeEventListener('keydown',shortcut)})
</script>
<template>
<TabsRoot v-model="tab" as="section" class="knowledge-space">
 <template v-if="!discussion">
 <header class="knowledge-page-heading"><div><p class="knowledge-breadcrumb">知识图谱 / 知识空间</p><h1>知识空间 <span>让学过的，重新连起来。</span></h1></div><button class="secondary-button" @click="emit('add-material')"><img :src="icon('upload')" alt="">导入资料</button></header>
 <div class="knowledge-navigation"><TabsList class="knowledge-tabs" aria-label="知识空间视图"><TabsTrigger value="library">知识库与记忆</TabsTrigger><TabsTrigger value="goals">学习目标图谱</TabsTrigger></TabsList><label v-if="tab==='library'" class="knowledge-scope">内容范围<select v-model="scope"><option value="">全部学习空间</option><option v-for="space in state.boot?.sessions||[]" :key="space.id" :value="space.id">{{ space.title }}</option></select></label></div>
 <p v-if="error" class="inline-error knowledge-error" role="alert">{{ error }} <button class="text-button" @click="load()">重新读取</button></p>
 <TabsContent value="library" class="knowledge-tab-panel"><div class="knowledge-workspace"><div class="knowledge-main">
  <section class="knowledge-garden" :style="gardenStyle"><header><h2>知识庭院</h2><span class="knowledge-sync" role="status"><i></i>{{ loading?'正在同步':synced?'已同步 '+new Date(synced).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}):'等待读取' }}</span><div class="garden-controls"><button aria-label="缩小图谱" :disabled="zoom<=0.8" @click="zoom=Math.max(.8,zoom-.1)">−</button><button aria-label="恢复图谱大小" @click="zoom=1">{{ Math.round(zoom*100) }}%</button><button aria-label="放大图谱" :disabled="zoom>=1.2" @click="zoom=Math.min(1.2,zoom+.1)">＋</button></div></header>
   <div class="garden-viewport"><div class="garden-interactive" :style="{transform:`scale(${zoom})`}"><svg class="garden-connections" viewBox="0 0 800 420" preserveAspectRatio="none" aria-hidden="true"><path d="M400 230 C260 230 230 95 160 112 M400 230 C540 230 570 95 640 112 M400 230 C260 230 250 310 112 277 M400 230 C540 230 550 310 688 277 M400 230 L400 320"/></svg><div class="garden-core"><img src="/assets/competition-v1/lesson/book.png.webp" alt="知识庭院" @error="$event.target.src=pageArtwork.graph.element"><span>我的知识空间</span></div><button v-for="group in groups" :key="group.id" :class="['garden-module',group.id,{active:kind===group.id,empty:!counts[group.id]}]" :style="{left:group.x+'%',top:group.y+'%'}" :aria-pressed="kind===group.id" @click="chooseGroup(group.id)"><img :src="splitAsset(group.asset)" alt="" @error="$event.target.hidden=true"><span><img :src="icon(group.glyph)" alt=""><strong>{{ group.label }}</strong><small>{{ counts[group.id]||0 }} 条</small></span></button></div></div>
   <footer><span><i></i>内容分类</span><p>分类连接只表示内容归属；学习关系与证据见“学习目标图谱”。</p></footer>
  </section>
  <section class="knowledge-search-section" aria-label="检索知识空间"><form class="knowledge-search" @submit.prevent="load()"><img :src="icon('search')" alt=""><input ref="searchInput" v-model="query" aria-label="搜索资料、学习记录、对话或记忆" placeholder="搜索资料、学习记录、对话或记忆…" maxlength="300"><button v-if="query" type="button" aria-label="清除知识搜索" @click="query=''">×</button><kbd>Ctrl K</kbd></form><div class="knowledge-filter-row"><div class="knowledge-filters"><button :class="{active:!kind}" @click="kind=''">全部</button><button v-for="group in groups" :key="group.id" :class="{active:kind===group.id}" @click="kind=group.id">{{ group.label }}</button></div><label v-if="kind==='memory'" class="memory-history"><input type="checkbox" v-model="includeInactive">包含已忽略／撤回</label></div>
   <div class="knowledge-results-heading"><span>{{ query?'搜索结果':activeGroup?.label||'已保存的内容' }}</span><small>{{ total }} 条{{ total>100?' · 当前展示前 100 条':'' }}</small></div>
   <p v-if="loading" class="knowledge-list-status" role="status">正在读取已保存内容…</p><div v-else-if="items.length" class="knowledge-result-list"><button v-for="entry in items" :key="entry.key" :class="['knowledge-result',{selected:selected?.key===entry.key}]" @click="select(entry)"><span class="knowledge-result-icon"><img :src="icon(groups.find(g=>g.id===entry.kind)?.glyph||'file-text')" alt=""></span><span class="knowledge-result-copy"><strong>{{ entry.title }}</strong><small>{{ entry.snippet }}</small><span class="knowledge-result-source">{{ entry.source }} · {{ entry.space_title }}</span></span><span :class="['knowledge-result-type','knowledge-kind-'+entry.kind]">{{ entry.kind==='memory'?memoryStatus[entry.status]:entry.type_label }}</span><img class="tiny-icon" :src="icon('chevron-right')" alt=""></button></div><div v-else class="knowledge-empty"><img :src="splitAsset(activeGroup?.asset||'library-books')" alt="" @error="$event.target.hidden=true"><h3>{{ query?'没有找到匹配内容':kind==='memory'?'记忆从你明确表达的偏好开始':'这里会留下你实际保存的内容' }}</h3><p>{{ query?'可以换个关键词，或切换内容类型与范围。':kind==='memory'?'与林知讨论时明确表达讲解偏好，系统会提出带原话来源的记忆建议，等你确认。':'导入一份资料、写下笔记或完成一次学习，内容会自动出现在相应分类中。' }}</p><button v-if="query" class="secondary-button" @click="query='';kind=''">清除筛选</button><button v-else-if="kind!=='memory'" class="primary-button" @click="emit('add-material')">加入第一份资料</button></div>
  </section>
 <RecordPagination v-model="resultPage" :total="total" :disabled="loading" label="知识检索结果"/></div><aside class="knowledge-side"><section class="knowledge-detail"><header><h2>内容预览</h2><span v-if="selected" class="knowledge-type">{{ selected.type_label }}{{ selected.evidence_label?' · '+selected.evidence_label:'' }}</span></header><p v-if="detailLoading" class="knowledge-list-status">正在读取原文…</p><template v-else-if="selected"><h3>{{ selected.title }}</h3><p class="knowledge-detail-source">来源：{{ selected.source }}</p><div class="knowledge-preview-text">{{ selected.text.slice(0,1600) }}{{ selected.text.length>1600?'…':'' }}</div><dl class="knowledge-detail-meta"><dt>所属空间</dt><dd>{{ selected.space_title }}</dd><dt>保存时间</dt><dd>{{ new Date(selected.updated_at).toLocaleString('zh-CN') }}</dd><template v-if="selected.kind==='memory'"><dt>记忆状态</dt><dd>{{ memoryStatus[selected.status] }}</dd></template></dl><div class="knowledge-detail-actions"><button class="primary-button" @click="readOriginal()">打开原文</button><button class="secondary-button" @click="discuss()">加入讨论</button></div></template><div v-else class="knowledge-preview-empty"><img src="/assets/competition-v1/citation/magnifier.png.webp" alt="" @error="$event.target.hidden=true"><h3>选一条内容，看看它的来处。</h3><p>点击图谱分类或搜索结果，即可在这里查看原文、来源和讨论入口。</p></div></section>
 <section class="knowledge-memory"><header><h2><img :src="icon('leaf')" alt="">学习记忆</h2><span v-if="memoryCandidate" :class="['memory-status',memoryCandidate.status]">{{ memoryStatus[memoryCandidate.status] }}</span></header><template v-if="memoryCandidate"><p>{{ memoryCandidate.text||memoryCandidate.snippet }}</p><button class="memory-source-button" @click="readMemorySource(memoryCandidate)">查看原话来源</button><div v-if="memoryCandidate.status==='pending'" class="memory-card-actions"><button class="primary-button" @click="askMemory(memoryCandidate,'confirm')">确认</button><button class="secondary-button" @click="askMemory(memoryCandidate,'ignore')">忽略</button></div><button v-if="memoryCandidate.status==='confirmed'" class="secondary-button" @click="askMemory(memoryCandidate,'revoke')">撤回这条记忆</button></template><template v-else><img class="memory-card-art" src="/assets/split-elements/elements/memory-sprout.compact.webp" alt="" @error="$event.target.hidden=true"><p>让林知逐步了解你喜欢怎样学习。</p><small>建议先展示来源，由你确认后再用于辅导。</small><button class="text-button" @click="kind='memory';query=''">查看学习记忆</button></template></section>
 </aside></div></TabsContent>
 <TabsContent value="goals" class="knowledge-tab-panel"><div class="space-selector"><label>当前目标<select :value="state.current?.id||''" @change="openSession($event.target.value,null,'graph')"><option value="" disabled>请选择学习空间</option><option v-for="space in state.boot?.sessions||[]" :key="space.id" :value="space.id">{{ space.title }}</option></select></label><button v-if="state.current" class="secondary-button" @click="openSession(state.current.id)">回到学习</button></div><KnowledgeGraph v-if="state.current" :session-id="state.current.id" @open-lesson="id=>openSession(state.current.id,id)" @open-space="openSession(state.current.id)" @open-material="emit('open-material',$event)"/><div v-else class="knowledge-empty"><img src="/assets/competition-v1/lesson/bridge.png.webp" alt="" @error="$event.target.hidden=true"><h3>选择一个真实学习目标</h3><p>图谱根据已保存的课程、确认路线和作答构建。</p><button class="primary-button" @click="emit('new-goal')">创建学习目标</button></div></TabsContent>
 </template>
 <SourceReader v-if="reader" :entry="reader" :query="query" @close="reader=null" @discuss="discuss"/>
 <CitationDiscussion v-if="discussion" :entry="discussion" @close="discussion=null;load(true)" @read="readOriginal" @changed="refresh();load(true)" @new-goal="startGoal" @attach="emit('add-material',$event)"/>
 <MemoryConfirmDialog v-if="confirmation" :entry="confirmation.entry" :action="confirmation.action" :busy="memoryBusy" :error="memoryError" @close="!memoryBusy&&(confirmation=null)" @confirm="changeMemory"/>
</TabsRoot>
</template>
