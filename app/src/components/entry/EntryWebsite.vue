<script setup>
import {computed,onMounted,ref} from 'vue'
import {artwork,icon} from '../../assets.js'
import {entryArt,walkthroughSteps,sampleById} from '../../entryContent.js'
import {api,useLearning} from '../../useLearning.js'
import {useDialogFocus} from '../../useDialogFocus.js'
import NewGoalDialog from '../NewGoalDialog.vue'
import ExamplesPage from './ExamplesPage.vue'
import LearningGuide from './LearningGuide.vue'
import GoalHandoffDialog from './GoalHandoffDialog.vue'
import {prepareWrite} from '../../retryRequest.js'

const {state}=useLearning()
const path=location.pathname.replace(/\/$/,'')||'/'
const route=path==='/examples'?'examples':path==='/how-it-works'?'guide':path==='/'?'landing':'missing'
const mobileOpen=ref(false),courseDialog=ref(null),courseChoice=ref(null),courseBusy=ref(false),courseError=ref(''),minutes=ref(30)
const stagedMaterial=ref(null),handoff=ref(null),handoffBusy=ref(false),handoffError=ref('')
let courseRequest=null,materialRequest=null
useDialogFocus(courseDialog)
const courseExample=computed(()=>sampleById(courseChoice.value?.id))
function newGoal(seed='',material=null){stagedMaterial.value=material;materialRequest=null;state.goalSeed=seed;state.newGoal=true}
function startCourse(example){courseChoice.value=example;courseRequest=null;courseError.value='';minutes.value=30}
async function confirmCourse(){
  if(courseBusy.value)return
  courseBusy.value=true;courseError.value=''
  try{
    const payload={course_id:courseChoice.value.id,daily_minutes:minutes.value}
    courseRequest=prepareWrite(courseRequest,payload)
    const space=await api('/sessions',{method:'POST',body:{...payload,request_id:courseRequest.key}})
    location.assign('/app?'+new URLSearchParams({space:space.id,lesson:courseChoice.value.lesson,view:'lesson'}))
  }catch(e){courseError.value=e.message;courseBusy.value=false}
}
async function completeGoal(space){
  if(handoffBusy.value)return
  handoff.value=space;handoffBusy.value=true;handoffError.value=''
  try{
    if(stagedMaterial.value){
      const payload={...stagedMaterial.value,session_id:space.id}
      materialRequest=prepareWrite(materialRequest,payload)
      await api('/materials',{method:'POST',body:{...payload,request_id:materialRequest.key}})
      stagedMaterial.value=null
    }
    location.assign('/app?'+new URLSearchParams({space:space.id,view:'lesson'}))
  }catch(e){handoffError.value='目标已经创建，资料尚未确认保存。'+e.message}
  finally{handoffBusy.value=false}
}
onMounted(()=>{document.title=route==='examples'?'学习示例 · 知行伴学':route==='guide'?'学习方式 · 知行伴学':'知行伴学 · 让好奇，慢慢成为能力。'})
</script>

<template>
<div class="entry-site" @keydown.esc="mobileOpen=false">
  <a class="entry-skip" href="#entry-content">跳到页面内容</a>
  <header class="entry-header">
    <a href="/" class="entry-brand" aria-label="知行伴学网站首页"><img :src="artwork.logo" alt=""><strong>知行伴学</strong><span>让好奇，慢慢成为能力</span></a>
    <nav class="entry-nav" aria-label="网站导航"><a href="/how-it-works" :aria-current="route==='guide'?'page':undefined">学习方式</a><a href="/app?view=graph">知识空间</a><a href="/app?view=buddy">认识林知</a></nav>
    <div class="entry-header-actions"><a href="/examples" class="entry-button secondary" :aria-current="route==='examples'?'page':undefined">查看示例</a><a href="/app" class="entry-button">进入学习空间</a><button class="entry-menu" aria-label="展开网站导航" :aria-expanded="mobileOpen" aria-controls="entry-mobile-links" @click="mobileOpen=!mobileOpen"><img :src="icon('menu')" alt=""></button></div>
    <nav v-if="mobileOpen" id="entry-mobile-links" class="entry-mobile-nav" aria-label="手机网站导航"><a href="/how-it-works">学习方式</a><a href="/app?view=graph">知识空间</a><a href="/app?view=buddy">认识林知</a><a href="/examples">查看示例</a></nav>
  </header>

  <main v-if="route==='landing'" id="entry-content" tabindex="-1">
    <section class="entry-hero" :style="{backgroundImage:`url(${artwork.hero})`}">
      <div class="entry-hero-inner"><h1>让好奇，<br>慢慢成为能力。</h1><h2>面向自主学习者的跨学科 AI 伴学空间</h2><p>从一个问题出发，把资料、讨论与练习连起来，<br class="entry-wide-break">逐步形成自己的理解。</p><div class="entry-action-row"><button class="entry-button" @click="newGoal()">开始我的学习<img :src="icon('arrow-right','white')" alt=""></button><a class="entry-button secondary" href="/how-it-works">先看看如何学习</a></div><small>从数学、编程、阅读示例开始，也可以提出自己的跨学科问题。</small></div>
      <span class="entry-hero-path" aria-hidden="true">提出问题 <span>→</span> 查阅资料 <span>→</span> 解释与练习</span>
    </section>
    <section class="entry-method entry-container" aria-labelledby="entry-method-title"><header><h2 id="entry-method-title">把一个问题，学成自己的理解。</h2><p>有目标，有依据，也有可以回看的学习过程。</p></header><div class="entry-method-steps"><a v-for="step in walkthroughSteps.slice(0,3)" :key="step.id" :href="'/how-it-works?step='+step.id"><img :src="step.art" alt=""><h3>{{ step.id==='1'?'从问题开始':step.id==='2'?'带着资料讨论':'用练习检查理解' }}</h3><p>{{ step.id==='1'?'写下想弄懂的事，选择适合自己的学习目标。':step.id==='2'?'围绕来源提问，和林知一起澄清概念。':'留下解释与作答，用实际表现决定下一步。' }}</p></a></div></section>
    <section class="entry-knowledge entry-container"><img class="entry-knowledge-scene" :src="entryArt.knowledge" alt="书本、笔记和幼苗组成的学习空间插画"><div><h2>让学过的，重新连起来。</h2><p>在知识空间中，搜索资料、笔记与讨论。<br>学习记忆先展示来源，由你确认后再使用。</p><div class="entry-mentor"><img :src="artwork.mentor" alt="学习伙伴林知"><span>林知，陪你把问题慢慢想清楚。</span></div><div class="entry-action-row"><a class="entry-text-link" href="/app?view=graph">了解知识空间<img :src="icon('arrow-right')" alt=""></a><a class="entry-text-link" href="/app?view=buddy">认识学习伙伴<img :src="icon('arrow-right')" alt=""></a></div></div></section>
    <section class="entry-invitation" :style="{backgroundImage:`url(${entryArt.footer})`}"><h2>今天，你想弄懂什么？</h2><a class="entry-button" href="/app">进入学习空间<img :src="icon('arrow-right','white')" alt=""></a></section>
  </main>
  <ExamplesPage v-else-if="route==='examples'" @new-goal="newGoal()" @start-course="startCourse"/>
  <LearningGuide v-else-if="route==='guide'" @new-goal="newGoal"/>
  <main v-else id="entry-content" class="entry-missing"><h1>这个页面还没有找到</h1><p>可以回到首页，或继续已有的学习目标。</p><div class="entry-action-row"><a href="/" class="entry-button">返回网站首页</a><a href="/app" class="entry-button secondary">进入学习空间</a></div></main>

  <footer class="entry-footer"><a class="entry-brand" href="/"><img :src="artwork.logo" alt=""><strong>知行伴学</strong></a><span>让好奇，慢慢成为能力。</span><a href="/how-it-works">学习方式</a><a href="/examples">学习示例</a></footer>
  <NewGoalDialog v-if="state.newGoal" @created="completeGoal"/>
  <dialog v-if="courseChoice" ref="courseDialog" class="form-dialog entry-course-dialog" @cancel.prevent="!courseBusy&&(courseChoice=null)"><button class="dialog-close" aria-label="关闭开始学习确认" :disabled="courseBusy" @click="courseChoice=null">×</button><div class="dialog-intro"><span>从示例进入自己的学习</span><h2>开始这个学习目标？</h2><p>{{ courseExample.tag }}：{{ courseExample.title }}</p></div><p>确认后创建学习目标；如果已经开始过这门课程，将恢复已有目标。刚才浏览的示例回答不会保存为作答。下面的时间只用于新目标，已有目标会保留原设置。</p><label>每天可用时间<select v-model.number="minutes" :disabled="courseBusy"><option :value="15">15 分钟</option><option :value="30">30 分钟</option><option :value="45">45 分钟</option><option :value="60">60 分钟</option></select></label><p v-if="courseError" class="inline-error" role="alert">{{ courseError }}</p><div class="dialog-actions"><button class="secondary-button" :disabled="courseBusy" @click="courseChoice=null">继续看示例</button><button class="primary-button" :disabled="courseBusy" @click="confirmCourse">{{ courseBusy?'正在打开学习目标…':courseError?'重试打开学习目标':'确认，进入学习' }}</button></div></dialog>
  <GoalHandoffDialog v-if="handoff" :space="handoff" :busy="handoffBusy" :error="handoffError" @retry="completeGoal(handoff)"/>
</div>
</template>
