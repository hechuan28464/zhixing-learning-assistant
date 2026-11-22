<script setup>
import { computed, nextTick, onMounted, ref, watch,defineAsyncComponent } from 'vue'
import { artwork, icon } from './assets.js'
import { useDialogFocus } from './useDialogFocus.js'
import { api, useLearning } from './useLearning.js'
import TutorPanel from './components/TutorPanel.vue'
import LessonWorkspace from './components/LessonWorkspace.vue'
import NewGoalDialog from './components/NewGoalDialog.vue'
import NoteEditorDialog from './components/NoteEditorDialog.vue'
import PageArtwork from './components/PageArtwork.vue'
import { pageArtwork } from './pageArtwork.js'
import LearningOverview from './components/LearningOverview.vue'
import CourseGallery from './components/CourseGallery.vue'
import PblWorkspace from './components/PblWorkspace.vue'
import ReadingLibrary from './components/ReadingLibrary.vue'
import ProjectsPage from './components/ProjectsPage.vue'
import NotesGarden from './components/NotesGarden.vue'
import BuddyPage from './components/BuddyPage.vue'
import LearningTimeline from './components/LearningTimeline.vue'
import SettingsPage from './components/SettingsPage.vue'
import KnowledgeSpace from './components/KnowledgeSpace.vue'
const VideoPage=defineAsyncComponent(()=>import('./components/VideoPage.vue'))
import { buildHomeCards, buildNextActions } from './homeLayout.js'
import { prepareWrite } from './retryRequest.js'
import {authSession,showLogin,signOut} from './authState.js'

const { state, currentLesson, initialize, refresh, openCourse, openSession, selectLesson, loadTask, loadTaskById, executeTaskAction, generatePlan, confirmPlan, navigate, notify } = useLearning()
const navItems=[['home','首页','home'],['book-open','我的学习','learning'],['grid','课程广场','explore'],['network','知识图谱','graph'],['file-text','阅读与思考','reading'],['play','视频研学','videos'],['box','项目实践','projects'],['leaf','灵感笔记','notes'],['users','学习伙伴','buddy']]
const headings={pbl:['项目学习','把理解变成可以检查的产物。'],learning:['我的学习','让每一次探索，都有迹可循。'],explore:['课程广场','从数学、Python与批判性阅读课程开始，或创建自己的跨学科目标。'],graph:['知识图谱','看清当前目标之间的联系，找到适合自己的下一步。'],reading:['阅读与思考','把可靠的材料，变成可以讨论和核查的依据。'],projects:['项目实践','从真实问题出发，先预测，再检查理解。'],notes:['灵感笔记','留下自己的解释、疑问和下一步。'],buddy:['学习伙伴','林知在这里，陪你把一个问题慢慢想清楚。'],messages:['学习动态','真实保存的目标、作答、资料和辅导记录。'],settings:['偏好设置','让学习节奏更适合你。']}
const goalQuery=ref(''), category=ref('全部'), modalBusy=ref(false), modalError=ref(''), drawerOpen=ref(false)
const materialDialog=ref(null), readerDialog=ref(null)
useDialogFocus(materialDialog);useDialogFocus(readerDialog)
const materialForm=ref({title:'',text:'',source:'手动录入',evidence_kind:'authored',session_id:null})
const noteForm=ref({title:'',text:'',session_id:null})
const profileForm=ref({name:'学习者',daily_minutes:30,style:'先理解，再动手'})
const selectedNote=ref(null)
let fileSelection=0
let materialRequest=null
const showArchivedMaterials=ref(false), showArchivedNotes=ref(false)
const today=new Intl.DateTimeFormat('zh-CN',{month:'long',day:'numeric',weekday:'long'}).format(new Date())
const matches=item=>[item.title,item.goal,item.domain,item.tag,item.text].filter(Boolean).join(' ').toLowerCase().includes(state.query.trim().toLowerCase())
const sessions=computed(()=>(state.boot?.sessions||[]).filter(matches))
const courses=computed(()=>(state.boot?.courses||[]).filter(matches).filter(c=>category.value==='全部'||c.tag===category.value))
const homeCards=computed(()=>buildHomeCards(state.boot?.sessions,state.query))
const nextActions=computed(()=>buildNextActions(state.boot?.sessions,state.boot?.materials,state.current?.id))
const materials=computed(()=>(showArchivedMaterials.value?state.boot?.archived_materials||[]:state.boot?.materials||[]).filter(matches))
const notes=computed(()=>(showArchivedNotes.value?state.boot?.archived_notes||[]:state.boot?.notes||[]).filter(matches))
const searchResults=computed(()=>[
  ...(state.boot?.sessions||[]).map(item=>({...item,searchType:'space',typeLabel:'学习目标'})),
  ...(state.boot?.courses||[]).map(item=>({...item,searchType:'course',typeLabel:'示例课程'})),
  ...(state.boot?.materials||[]).map(item=>({...item,searchType:'material',typeLabel:'学习资料'})),
  ...(state.boot?.notes||[]).map(item=>({...item,searchType:'note',typeLabel:'灵感笔记'})),
].filter(matches).slice(0,8))
const records=computed(()=>(state.boot?.sessions||[]).flatMap(s=>(s.states?Object.entries(s.states):[]).filter(([,v])=>v.attempts).map(([id,v])=>({...v,session:s,lessonId:id}))))
const planNodes=computed(()=>state.current?.plan?.draft?.nodes || state.current?.plan?.active?.nodes || [])
const recommendations=[{id:'systems',title:'用一次散步\n理解复杂系统',tag:'思维模型 · 跨学科',goal:'从日常例子理解复杂系统与相互影响'},{id:'city',title:'城市的数学：\n从路线到可能性',tag:'数学 · 真实世界',goal:'结合数学与城市生活理解路线选择'},{id:'curiosity',title:'好的提问，\n是另一种创造',tag:'阅读 · 思考力',goal:'学会围绕材料提出可检查的好问题'}]
const imageFor=item=>artwork[item.course_id || item.id] || artwork.systems
const tintFor=item=>state.boot?.courses.find(c=>c.id===(item.course_id||item.id))?.tint || 'lavender'
const formatTime=value=>new Intl.DateTimeFormat('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value))
async function logout(){try{await signOut()}catch{state.error='退出未完成，请检查连接后重试。'}}
function newGoal(seed=''){state.goalSeed=seed;state.newGoal=true}
function go(view){drawerOpen.value=false;if(view==='buddy')openBuddy();else navigate(view)}
async function openBuddy(){const id=state.current?.id||state.boot?.sessions[0]?.id;if(id)await openSession(id,null,'buddy');else navigate('buddy')}
function openLibraryDiscussion(entry){state.knowledgeCitation=entry;navigate('graph')}
function handleDrawerKey(event){
 if(!drawerOpen.value)return
 if(event.key==='Escape'){event.preventDefault();drawerOpen.value=false;return}
 if(event.key!=='Tab')return
 const choices=[...event.currentTarget.querySelectorAll('a,button')].filter(e=>!e.disabled)
 const first=choices[0],last=choices.at(-1)
 if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}
 else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}
}
watch(drawerOpen,async open=>{await nextTick();if(open)document.querySelector('.sidebar .nav-item')?.focus();else document.querySelector('.mobile-menu')?.focus({preventScroll:true})})
function startFromHero(){newGoal(goalQuery.value)}
async function runNextAction(action){
  if(action.taskId){await openSession(action.sessionId,action.lessonId||null,'lesson',action.taskId);return}
  if(action.kind==='space'||action.kind==='route')return openSession(action.sessionId)
  if(action.kind==='review'){await openSession(action.sessionId);if(currentLesson.value)await loadTask('review');return}
  if(action.kind==='material'){
    if(action.sessionId)await openSession(action.sessionId,null,'reading');else go('reading')
    if(state.boot.materials.some(m=>!m.session_id||m.session_id===action.sessionId))return
    addMaterial();return
  }
  if(action.kind==='create')return newGoal()
  go('explore')
}
function addMaterial(scopeId=null){++fileSelection;materialRequest=null;materialForm.value={title:'',text:'',source:'手动录入',evidence_kind:'authored',session_id:typeof scopeId==='string'&&state.boot.sessions.some(s=>s.id===scopeId)?scopeId:state.current?.id || null};modalError.value='';state.materialDialog=true}
async function loadFile(event){const selection=++fileSelection;const file=event.target.files?.[0];if(!file)return;if(file.size>1024*1024){modalError.value='请选择1MB以内的TXT或Markdown文件。';return}if(!/\.(txt|md)$/i.test(file.name)){modalError.value='当前版本支持TXT和Markdown，也可以直接粘贴文字。';return}const text=await file.text();if(selection!==fileSelection||!state.materialDialog)return;if(text.length>120000){modalError.value='文本超过当前12万字元的导入上限，请分段整理。';return}materialForm.value.title=file.name.replace(/\.(txt|md)$/i,'');materialForm.value.text=text;materialForm.value.source=file.name;modalError.value=''}
async function saveMaterial(){
 if(modalBusy.value)return
 modalBusy.value=true;modalError.value='';let saved=false
 try{
  materialRequest=prepareWrite(materialRequest,materialForm.value)
  await api('/materials',{method:'POST',body:{...materialForm.value,request_id:materialRequest.key}})
  saved=true;state.materialDialog=false;await refresh();notify('资料已加入，可以在对应学习空间向导师提问。')
 }catch(e){if(saved)state.error='资料已保存，但列表未刷新。'+e.message;else modalError.value='暂时未能确认保存结果，内容已保留，可以重试。'+e.message}
 finally{modalBusy.value=false}
}
async function readMaterial(id){try{state.materialPreview=await api('/materials/'+id)}catch(e){state.error=e.message}}
async function archiveMaterial(id){try{await api('/materials/'+id,{method:'DELETE'});state.materialPreview=null;await refresh();notify('资料已归档。')}catch(e){state.error=e.message}}
async function restoreItem(kind,id){try{await api('/'+kind+'/'+id+'/restore',{method:'POST'});await refresh();notify('已恢复到当前列表。')}catch(e){state.error=e.message}}
function editNote(note=null){selectedNote.value=note;noteForm.value={title:note?.title||'',text:note?.text||'',session_id:note?.session_id||state.current?.id||null};modalError.value='';state.noteDialog=true}
async function onNoteSaved(){try{await refresh();notify('笔记已保存。')}catch(e){state.error='笔记已保存，但列表未刷新。'+e.message}}
async function archiveNote(id){try{await api('/notes/'+id,{method:'DELETE'});await refresh();notify('笔记已归档。')}catch(e){state.error=e.message}}
async function saveProfile(){modalBusy.value=true;try{await api('/profile',{method:'PATCH',body:profileForm.value});await refresh();notify('学习偏好已保存。')}catch(e){state.error=e.message}finally{modalBusy.value=false}}
function chooseSearch(result){state.query='';if(result.searchType==='space')openSession(result.id);else if(result.searchType==='course')openCourse(result.id);else if(result.searchType==='material')readMaterial(result.id);else editNote(result)}
watch(()=>state.view,view=>{if(view==='settings'&&state.boot)profileForm.value={...state.boot.profile}})
onMounted(initialize)
</script>

<template>
<div class="studio-shell" :class="{'drawer-open':drawerOpen}">
  <button v-if="drawerOpen" class="sidebar-scrim" aria-label="收起导航" @click="drawerOpen=false"></button>
  <aside class="sidebar" @keydown="handleDrawerKey" :style="{backgroundImage:`url(${artwork.sidebar})`}">
    <a class="brand-lockup" href="#home" @click.prevent="go('home')"><img :src="artwork.logo" alt="知行伴学山径书页标志"><div><strong>知行伴学</strong><span>让好奇，慢慢成为能力</span></div></a>
    <nav id="studio-main-navigation" aria-label="主导航"><button v-for="[id,label,view] in navItems" :key="id" :aria-label="label" :title="label" :class="['nav-item',{active:state.view===view || view==='learning'&&state.view==='lesson' || view==='explore'&&state.view==='pbl'}]" @click="go(view)"><img :src="icon(id,'white')" alt=""><span>{{ label }}</span></button></nav>
    <div class="sidebar-secondary"><button aria-label="消息" title="消息" :class="['nav-item',{active:state.view==='messages'}]" @click="go('messages')"><img :src="icon('bell','white')" alt=""><span>消息</span></button><button aria-label="设置" title="设置" :class="['nav-item',{active:state.view==='settings'}]" @click="go('settings')"><img :src="icon('settings','white')" alt=""><span>设置</span></button></div>
    <div class="sidebar-quote">在更大的世界里<br>成为更好的自己。<span></span></div>
  </aside>
  <div class="workspace" :inert="drawerOpen">
    <header class="topbar"><button class="mobile-menu icon-button" aria-label="展开导航" :aria-expanded="drawerOpen" aria-controls="studio-main-navigation" @click="drawerOpen=!drawerOpen"><img :src="icon('menu')" alt=""></button><div class="global-search-shell"><label class="top-search"><img :src="icon('search')" alt=""><input v-model="state.query" aria-label="搜索学习内容" placeholder="搜索课程、目标、资料与笔记…" @keydown.esc="state.query=''" @keydown.enter.prevent="event=>{if(!event.isComposing&&searchResults.length)chooseSearch(searchResults[0])}"><kbd>搜索</kbd></label><div v-if="state.query.trim()" class="global-search-results"><button v-for="result in searchResults" :key="result.searchType+result.id" @click="chooseSearch(result)"><span>{{ result.typeLabel }}</span><strong>{{ result.title }}</strong></button><p v-if="!searchResults.length">没有匹配内容，可以新建一个学习目标。</p><button class="search-new" @click="newGoal(state.query);state.query=''">以这个问题创建学习目标</button><button class="search-dismiss" @click="state.query=''">收起搜索</button></div></div><div class="top-actions"><button class="text-button" @click="authSession.authenticated?go('settings'):showLogin()">{{authSession.authenticated?authSession.username:"登录"}}</button><button v-if="authSession.authenticated" class="text-button" @click="logout">退出</button><span><img :src="icon('calendar')" alt="">{{ today }}</span><button class="icon-button" aria-label="查看学习动态" @click="go('messages')"><img :src="icon('bell')" alt=""></button><button class="avatar-button" aria-label="打开个人设置" @click="go('settings')"><img :src="artwork.learner" alt="学习者头像"></button></div></header>
    <div v-if="state.error" class="app-error" role="alert"><span>{{ state.error }}</span><button v-if="state.retryAction?.task_id" @click="executeTaskAction(state.retryAction)">换一道任务</button><button @click="state.error=''; state.boot ? refresh().catch(e=>state.error=e.message) : initialize()">重试连接</button><button aria-label="关闭提示" @click="state.error=''">×</button></div>

    <main v-if="state.loading" class="page-loading"><span class="spinner"></span><p>正在打开你的学习空间…</p></main>
    <main v-else-if="!state.boot" class="full-empty"><h1>学习记录暂时没有连接上</h1><p>请确认本地服务已启动，再试一次。已保存的记录不会因页面断开而删除。</p><button class="primary-button" @click="initialize">重新连接</button></main>

    <div v-else-if="state.view==='home'" :class="['dashboard-grid','home-dashboard',{'no-learning':!state.boot.sessions.length}]">
      <main class="main-column"><section class="hero" :style="{backgroundImage:`url(${artwork.hero})`}"><div class="hero-copy"><p>你好，{{ state.boot.profile.name }}。<br>欢迎回到知行伴学。</p><h1>让好奇，慢慢成为能力。</h1><form class="hero-search" @submit.prevent="startFromHero"><img :src="icon('search')" alt=""><input v-model="goalQuery" aria-label="新的学习目标" placeholder="今天想探索什么？从一个问题开始…"><button aria-label="创建新的学习目标"><img :src="icon('arrow-right','white')" alt=""></button></form><div class="topic-links"><button @click="openCourse('mathematics')">数学思维</button><button @click="openCourse('programming')">Python 入门</button><button @click="openCourse('reading')">阅读与写作</button><button @click="newGoal()">自选跨学科目标</button></div></div></section>
        <section v-if="state.boot.sessions.length" class="courses-section"><div class="section-heading"><h2>继续学习<img :src="icon('chevron-right')" alt=""></h2><button class="text-button" @click="go('learning')">查看全部</button></div><p class="section-description">只展示你已经开始的目标，从适合现在的一步继续。</p><button v-if="homeCards.length===1" class="resume-spotlight" @click="openSession(homeCards[0].id)"><div class="resume-picture" :style="{backgroundImage:`url(${imageFor(homeCards[0])})`}"></div><div class="resume-copy"><span :class="['course-tag',tintFor(homeCards[0])]">{{ homeCards[0].domain }}</span><h3>{{ homeCards[0].title }}</h3><p>{{ homeCards[0].course_id ? '带着上次的作答与反馈，继续当前单元。' : '你的目标和已有路线都在这里，随时继续。' }}</p><div><span>{{ homeCards[0].daily_minutes }} 分钟 / 天</span><strong>继续这个目标 <img :src="icon('arrow-right')" alt=""></strong></div></div></button><div v-else-if="homeCards.length" class="course-grid home-learning-grid" :style="{'--home-card-count':homeCards.length}"><button v-for="card in homeCards" :key="card.id" class="course-card" @click="openSession(card.id)"><div class="course-art" :style="{backgroundImage:`url(${imageFor(card)})`}"><span :class="['course-tag',tintFor(card)]">{{ card.domain }}</span><h3>{{ card.title }}</h3><p>{{ card.daily_minutes }} 分钟 / 天</p></div><div class="course-footer"><span :class="['progress-dot',tintFor(card)]"></span><div><strong>{{ card.completed ? card.completed+' 个单元有独立新题表现' : card.course_id ? '继续理解与练习' : '查看目标与学习路线' }}</strong><small>{{ formatTime(card.updated_at) }}</small></div><img :src="icon('chevron-right')" alt=""></div></button></div><div v-else class="dashed-empty"><p>没有匹配的已开始目标。</p><button class="secondary-button" @click="state.query=''">清除筛选</button></div></section>
        <section class="recommendations"><div class="section-heading"><h2><img :src="icon('leaf')" alt="">换个角度，发现联系</h2><button class="text-button" @click="newGoal()">写下自己的问题</button></div><div class="recommendation-grid"><button v-for="item in recommendations" :key="item.id" @click="newGoal(item.goal)"><img class="recommendation-art" :src="artwork[item.id]" :alt="item.title.replace('\n','')"><div><h3>{{ item.title }}</h3><span>{{ item.tag }}</span></div><img class="chevron" :src="icon('chevron-right')" alt=""></button></div></section>
      </main>
      <aside class="right-column"><section class="plan-panel next-step-panel"><div class="section-heading"><h2>{{ state.boot.sessions.length ? '你的下一步' : '从哪里开始' }}</h2><button class="text-button" @click="newGoal()">新建目标</button></div><template v-for="action in nextActions" :key="action.id"><p v-if="action.target" class="next-step-target">围绕目标：{{ action.target }}</p><div class="next-step-primary"><span class="next-action-symbol"><img :src="icon(action.icon)" alt=""></span><div><strong>{{ action.title }}</strong><small>{{ action.detail }}</small></div><img class="tiny-icon" :src="icon('chevron-right')" alt=""></div><div class="next-step-reason"><span>为什么建议这一步</span><p>{{ action.reason }}</p></div><button class="primary-button next-step-cta" @click="runNextAction(action)">{{ action.taskId?'从这一步开始':action.kind==='create'?'写下我的目标':'从这一步继续' }}<img :src="icon('arrow-right','white')" alt=""></button></template><button class="next-step-secondary" @click="go('explore')">也可以先看看示例课程 <img :src="icon('arrow-right')" alt=""></button></section>
        <section class="mentor-panel"><div class="section-heading"><h2>学习伙伴 · AI 导师</h2><button class="text-button" @click="openBuddy">与我对话</button></div><div class="mentor-intro"><img :src="artwork.mentor" alt="林知导师"><div><h3>林知</h3><p>我在这里，陪你把好奇一点点<br>变成真实的能力。</p></div></div><div class="mentor-prompts"><button @click="openBuddy">我有一个想法，想一起梳理<img :src="icon('arrow-right')" alt=""></button><button @click="state.current ? openSession(state.current.id) : newGoal()">从当前目标继续学习<img :src="icon('arrow-right')" alt=""></button><button @click="go('reading')">加入一份自己的学习材料<img :src="icon('arrow-right')" alt=""></button></div></section>
        <div class="growth-banner" :style="{backgroundImage:`url(${artwork.growth})`}"><span>真正的成长，<br>是把好奇变成一次次微小的行动。</span><small>—— 知行伴学</small></div>
      </aside>
    </div>

    <LessonWorkspace v-else-if="state.view==='lesson' && state.current && currentLesson" @note="editNote()" @add-material="addMaterial"/>
    <main v-else-if="state.view==='lesson' && state.current" class="learning-layout" :class="{'custom-space':!currentLesson}">
      <aside class="lesson-rail"><button class="back-link" @click="go('learning')">‹ 我的学习</button><span class="course-tag" :class="tintFor(state.current)">{{ state.current.domain }}</span><h2>{{ state.current.title }}</h2><p>{{ state.current.daily_minutes }} 分钟 / 天</p><div class="lesson-steps"><button v-for="(lesson,index) in state.current.lessons" :key="lesson.id" :class="{selected:currentLesson?.id===lesson.id}" @click="selectLesson(lesson.id)"><span>{{ String(index+1).padStart(2,'0') }}</span><div><strong>{{ lesson.title }}</strong><small>{{ state.current.states[lesson.id]?.label }}</small></div></button></div><button class="secondary-button" @click="go('graph')">查看目标关系</button><button class="text-button rail-material" @click="addMaterial">加入相关资料</button></aside>
      <article class="custom-content"><PageArtwork page="lesson" motif/><span class="course-tag lavender">{{ state.current.domain }}</span><h1>{{ state.current.title }}</h1><p class="learning-objective">{{ state.current.goal }}</p><div class="goal-facts"><span>每天 {{ state.current.daily_minutes }} 分钟</span><span>基础：{{ state.current.foundation || '尚未说明，可在对话中补充' }}</span></div><div class="section-heading"><h2>把目标变成小步骤</h2><button class="primary-button" :disabled="state.planBusy" @click="generatePlan">{{ state.planBusy ? '正在组织路线…' : planNodes.length ? '重新生成草案' : '生成学习路线' }}</button></div><p class="section-description">路线是模型建议，确认后保存。尚未接入审核题目的主题，可先围绕材料讨论，不生成已掌握结论。</p><div v-if="planNodes.length" class="plan-nodes"><article v-for="(node,index) in planNodes" :key="node.id"><span>{{ index+1 }}</span><div><h3>{{ node.title }}</h3><p>{{ node.objective }}</p><small>{{ node.minutes }} 分钟</small></div></article><button v-if="state.current.plan?.draft" class="primary-button" @click="confirmPlan">确认这份学习路线</button><p v-else class="confirmed-plan">✓ 路线已确认，随时可以据新情况生成草案。</p></div><div v-else class="custom-start"><img :src="artwork.systems" alt="探索的起点"><div><h3>先迈出一小步</h3><p>生成路线，加入一份可靠资料，或直接向林知说明你想解决的问题。</p><button class="secondary-button" @click="addMaterial">加入学习资料</button></div></div></article>
      <TutorPanel @add-material="addMaterial"/>
    </main>

    <main v-else class="content-page"><PageArtwork v-if="!['graph','pbl','videos'].includes(state.view)" :page="state.view" :title="headings[state.view]?.[0] || '学习空间'" :description="headings[state.view]?.[1]"><button v-if="['learning','explore','graph'].includes(state.view)" class="primary-button" @click="newGoal()"><img :src="icon('plus','white')" alt="">新建学习目标</button><button v-if="state.view==='reading'" class="primary-button" @click="addMaterial"><img :src="icon('upload','white')" alt="">加入资料</button><button v-if="state.view==='notes'" class="primary-button" @click="editNote()"><img :src="icon('plus','white')" alt="">写一则笔记</button></PageArtwork>
      <LearningOverview v-if="state.view==='learning'" @new-goal="newGoal" @next="runNextAction" @note="editNote"/>
      <CourseGallery v-if="state.view==='explore'" @new-goal="newGoal"/><PblWorkspace v-if="state.view==='pbl'"/>
      <KnowledgeSpace v-if="state.view==='graph'" @add-material="addMaterial" @new-goal="newGoal()" @open-material="readMaterial"/>
      <ReadingLibrary v-if="state.view==='reading'" @add-material="addMaterial" @discuss="openLibraryDiscussion"/>
      <VideoPage v-if="state.view==='videos'" @discuss="openLibraryDiscussion"/>
      <ProjectsPage v-if="state.view==='projects'" @new-goal="newGoal"/>
      <NotesGarden v-if="state.view==='notes'" @edit="editNote" @archive="archiveNote" @restore="id=>restoreItem('notes',id)"/>
      <BuddyPage v-if="state.view==='buddy'" @new-goal="newGoal()" @add-material="addMaterial" @read-material="readMaterial"/>
      <LearningTimeline v-if="state.view==='messages'" @new-goal="newGoal()" @explore="go('explore')"/>
      <SettingsPage v-if="state.view==='settings'"/>
    </main>
  </div>
  <NewGoalDialog v-if="state.newGoal"/>
  <dialog v-if="state.materialDialog" ref="materialDialog" class="form-dialog" @cancel.prevent="!modalBusy&&(state.materialDialog=false)"><button class="dialog-close" aria-label="关闭资料导入" :disabled="modalBusy" @click="!modalBusy&&(state.materialDialog=false)">×</button><div class="dialog-intro"><span>给学习一份可靠依据</span><h2>加入学习资料</h2><p>支持TXT、Markdown和粘贴文字。内容保存在当前工作区，提问时导师可检索相关段落。</p></div><form @submit.prevent="saveMaterial"><label class="file-picker"><img :src="icon('upload')" alt="">选择TXT或Markdown文件<input type="file" accept=".txt,.md,text/plain,text/markdown" @change="loadFile"></label><label>资料标题<input v-model="materialForm.title" required maxlength="150"></label><label>原文或摘录<textarea v-model="materialForm.text" required maxlength="120000" rows="7"></textarea></label><div class="form-two"><label>来源或署名<input v-model="materialForm.source" maxlength="200"></label><label>资料性质<select v-model="materialForm.evidence_kind" aria-label="资料性质" aria-describedby="material-kind-help"><option value="authored">自己编写的材料</option><option value="official_doc">官方资料链接或摘录</option><option value="self_reported">自己的学习自述</option><option value="external_record">外部练习记录</option></select><small id="material-kind-help">来源类型不代替实际作答，也不代表已经核验。</small></label><label>关联范围<select v-model="materialForm.session_id"><option :value="null">公共资料，各空间可检索</option><option v-for="space in state.boot.sessions" :key="space.id" :value="space.id">{{ space.title }}</option></select></label></div><p v-if="modalError" class="inline-error" role="alert">{{ modalError }}</p><div class="dialog-actions"><button type="button" class="secondary-button" :disabled="modalBusy" @click="!modalBusy&&(state.materialDialog=false)">取消</button><button class="primary-button" :disabled="modalBusy || !materialForm.title.trim() || !materialForm.text.trim()">{{ modalBusy?'保存中…':modalError?'重试保存资料':'保存资料' }}</button></div></form></dialog>
  <NoteEditorDialog v-if="state.noteDialog" :note="selectedNote" :session-id="noteForm.session_id" @close="state.noteDialog=false" @saved="onNoteSaved"/>
  <dialog v-if="state.materialPreview" ref="readerDialog" class="reader-dialog" @cancel.prevent="state.materialPreview=null"><button class="dialog-close" aria-label="关闭资料预览" @click="state.materialPreview=null">×</button><span class="muted-label">{{ state.materialPreview.source }}</span><h1>{{ state.materialPreview.title }}</h1><div class="reader-text">{{ state.materialPreview.text }}</div><footer><span>{{ formatTime(state.materialPreview.created_at) }}</span><button class="quiet-button" @click="archiveMaterial(state.materialPreview.id)">归档资料</button></footer></dialog>
  <div v-if="state.toast" class="app-toast" role="status">{{ state.toast }}</div>
</div>
</template>
