<script setup>
import RecordPagination from './ui/RecordPagination.vue'
import {usePagination} from '../usePagination.js'
import {requestId as newRequestId} from '../requestId.js'

import {computed,nextTick,onMounted,onUnmounted,ref,watch} from 'vue'
import {TabsRoot,TabsList,TabsTrigger,TabsContent} from 'reka-ui'
import {api,useLearning} from '../useLearning.js'
import {artwork,icon} from '../assets.js'
import {prepareWrite} from '../retryRequest.js'
import MessageBody from './MessageBody.vue'
import PblProcessReport from './PblProcessReport.vue'
import SourceReader from './SourceReader.vue'
const {state,navigate,openSession}=useLearning()
const artifactReader=ref(null),execution=ref(null),executionError=ref(''),executionActive=computed(()=>!!execution.value?.current_version&&['pending','running'].includes(execution.value?.state))
const catalog=ref(null),study=ref(null),loading=ref(false),busy=ref(false),chatBusy=ref(false),error=ref(''),chatError=ref(''),tab=ref('requirements'),evidenceTab=ref('runs')
const plan=ref(''),code=ref(''),draft=ref(''),explanation=ref(''),chosen=ref(''),rationale=ref(''),answers=ref([]),draftWarning=ref('')
let commandRequest=null,chatRequest=null,loadVersion=0,disposed=false,executionTimer=null,executionPollVersion=0,executionFailures=0
const acknowledged=new Set()
async function acknowledgeHelp(){
 if(disposed||!study.value)return
 const sid=study.value.session_id
 for(const message of study.value.messages){const id=message.metadata?.assistance_id;if(id&&!acknowledged.has(id)){try{await api('/sessions/'+sid+'/assistance/'+id+'/ack',{method:'POST'});acknowledged.add(id)}catch{}}}
}
const stage=computed(()=>study.value?.stage??0),project=computed(()=>study.value?.project||catalog.value?.project)
const runtime=computed(()=>study.value?.runtime||catalog.value?.runtime)
const runtimeMessage=computed(()=>runtime.value?.available?'代码在受限环境检查，回执与保存版本关联。':'代码检查暂不可用，可以先保存计划、代码和讨论。')
const editable=computed(()=>tab.value==='plan'?stage.value===2:tab.value==='code'&&(stage.value===3||stage.value===4&&study.value?.collected.remediation&&study.value?.collected.tests?.status!=='passed'))
const currentKind=computed(()=>tab.value==='plan'?'plan':'code')
const currentText=computed({get:()=>currentKind.value==='plan'?plan.value:code.value,set:value=>{if(currentKind.value==='plan')plan.value=value;else code.value=value}})
const dirty=computed(()=>!!study.value&&currentText.value!==(study.value.artifacts[currentKind.value]?.text||(currentKind.value==='code'?project.value.starter:'')))
const reviewed=computed(()=>!!study.value?.reviews[currentKind.value]&&!dirty.value)
const codeDirty=computed(()=>!!study.value&&code.value!==(study.value.artifacts.code?.text||project.value.starter))
const decisionDirty=computed(()=>{const saved=study.value?.collected.decisions[0];return !!saved&&(chosen.value!==saved.chosen||rationale.value!==(saved.rationale||''))})
const canNext=computed(()=>{
 if(!study.value||busy.value||chatBusy.value||executionActive.value||study.value.busy||study.value.status==='completed')return false
 if(stage.value===4&&codeDirty.value)return false
 if(stage.value===0||stage.value===6)return !!explanation.value.trim()
 if(stage.value===1)return study.value.actions.includes('next')&&!decisionDirty.value
 if(stage.value===2||stage.value===3){const kind=stage.value===2?'plan':'code';return !!study.value.reviews[kind]&&(kind==='plan'?plan.value:code.value)===study.value.artifacts[kind]?.text}
 return study.value.actions.includes('next')
})
function key(){return 'zhixing.pbl-draft.'+study.value?.id}
function storeDraft(){if(!study.value)return;try{sessionStorage.setItem(key(),JSON.stringify({plan:plan.value,code:code.value,draft:draft.value,explanation:explanation.value,chosen:chosen.value,rationale:rationale.value}))}catch{draftWarning.value='当前浏览器不能保留草稿，请及时保存或复制内容。'}}
function update(data,initial=false){
 if(disposed)return
 const same=study.value?.id===data.id
 if(same&&!initial&&data.revision<study.value.revision)return
 const planDirty=same&&plan.value!==(study.value.artifacts.plan?.text||'')
 const codeDirty=same&&code.value!==(study.value.artifacts.code?.text||study.value.project.starter)
 study.value=data;state.pblStudyId=data.id
 if(data.latest_execution)setExecution(data.latest_execution)
 nextTick(acknowledgeHelp)
 history.replaceState(null,'','/app?'+new URLSearchParams({view:'pbl',study:data.id}))
 if(!planDirty||initial)plan.value=data.artifacts.plan?.text||''
 if(!codeDirty||initial)code.value=data.artifacts.code?.text||data.project.starter
 if(initial){chosen.value=data.collected.decisions[0]?.chosen||'';rationale.value=data.collected.decisions[0]?.rationale||'';try{const saved=JSON.parse(sessionStorage.getItem(key())||'null');if(saved){plan.value=saved.plan??plan.value;code.value=saved.code??code.value;draft.value=saved.draft||'';explanation.value=saved.explanation||'';chosen.value=saved.chosen||'';rationale.value=saved.rationale||''}}catch{draftWarning.value='草稿未能恢复，已保存的项目内容仍在服务器。'}}
}
async function load(){const version=++loadVersion;loading.value=true;error.value='';try{catalog.value=await api('/pbl/catalog');const id=new URLSearchParams(location.search).get('study');if(id){const data=await api('/pbl/studies/'+encodeURIComponent(id));if(version===loadVersion&&!disposed){state.pblStudyId=data.id;await openSession(data.session_id,null,'pbl');update(data,true)}}}catch(e){error.value=e.message}finally{if(version===loadVersion)loading.value=false}}
async function start(){if(busy.value)return;busy.value=true;error.value='';try{const data=await api('/pbl/studies',{method:'POST',body:{request_id:newRequestId()}});if(disposed)return;state.pblStudyId=data.id;await openSession(data.session_id,null,'pbl');update(data,true)}catch(e){error.value=e.message}finally{busy.value=false}}
async function command(kind,fields={}){
 if(busy.value||!study.value)return;busy.value=true;error.value=''
 const before=stage.value;const payload={kind,expected_revision:study.value.revision,...fields}
 commandRequest=prepareWrite(commandRequest,payload)
 try{const data=await api('/pbl/studies/'+study.value.id+'/commands',{method:'POST',body:{...payload,request_id:commandRequest.key}});if(kind==='plan'||kind==='code'){if(kind==='plan')plan.value=data.artifacts.plan.text;else code.value=data.artifacts.code.text}update(data);commandRequest=null;if(data.stage!==before){explanation.value='';answers.value=[];storeDraft()}}catch(e){error.value=e.message}finally{busy.value=false}
}
function save(){return command(currentKind.value,{text:currentText.value})}
function next(){const kind=stage.value===2?'plan':'code';return command('next',{text:explanation.value,artifact_sha:study.value.artifacts[kind]?.sha256||''})}
async function chat(review=false){
 if(chatBusy.value||!study.value)return
 const message=review?'请检查当前保存版本是否符合公开要求；如有具体问题请指出，没有则说明检查边界，并建议怎样核对自己的理解。':draft.value.trim()
 if(!message)return
 chatBusy.value=true;chatError.value=''
 const payload={message,review_kind:review?currentKind.value:'',artifact_sha:review?study.value.artifacts[currentKind.value]?.sha256||'':''}
 chatRequest=prepareWrite(chatRequest,payload)
 try{update(await api('/pbl/studies/'+study.value.id+'/chat',{method:'POST',body:{...payload,request_id:chatRequest.key}}));if(!review&&draft.value.trim()===message)draft.value='';chatRequest=null;storeDraft();await nextTick();if(disposed)return;document.querySelector('.pbl-conversation')?.scrollTo({top:999999,behavior:'smooth'})}catch(e){chatError.value=e.message}finally{chatBusy.value=false}
}
function setExecution(job){
 if(disposed||!job||study.value?.id!==job.study_id)return
 const old=execution.value
 if(old&&old.job_id===job.job_id&&old.updated_at>job.updated_at)return
 if(old&&old.job_id!==job.job_id&&old.started_at>job.started_at)return
 execution.value=job;clearTimeout(executionTimer);executionTimer=null
 if(['pending','running'].includes(job.state))executionTimer=setTimeout(()=>pollExecution(job.job_id),1500)
}
async function pollExecution(jobId=execution.value?.job_id){
 const id=study.value?.id;if(!id||!jobId||disposed)return
 const version=++executionPollVersion;executionError.value=''
 try{
  const data=await api('/pbl/studies/'+id+'/run/'+jobId)
  if(disposed||study.value?.id!==id||version!==executionPollVersion)return
  executionFailures=0;setExecution(data)
  if(!['pending','running'].includes(data.state))await refreshStatus()
 }catch(e){if(!disposed&&study.value?.id===id&&version===executionPollVersion){executionError.value='检查状态暂未同步，结果仍待确认。'+e.message;if(++executionFailures<=3)executionTimer=setTimeout(()=>pollExecution(jobId),executionFailures*2500)}}
}
async function evaluate(){
 if(busy.value||executionActive.value||codeDirty.value||!study.value)return
 const id=study.value.id;busy.value=true;error.value='';executionError.value=''
 const payload={expected_revision:study.value.revision};commandRequest=prepareWrite(commandRequest,{kind:'run',...payload})
 try{const job=await api('/pbl/studies/'+id+'/run',{method:'POST',body:{...payload,request_id:commandRequest.key}});if(disposed||study.value?.id!==id)return;commandRequest=null;setExecution(job);evidenceTab.value='runs'}
 catch(e){if(e.retry?.job_id&&study.value?.id===id){commandRequest=null;await pollExecution(e.retry.job_id)}else error.value=e.message}
 finally{busy.value=false}
}
async function stopWaiting(){
 const id=study.value?.id,job=execution.value;if(!id||!job||busy.value)return
 busy.value=true;executionError.value=''
 try{const data=await api('/pbl/studies/'+id+'/run/'+job.job_id+'/cancel',{method:'POST'});if(!disposed&&study.value?.id===id){++executionPollVersion;setExecution(data);await refreshStatus()}}
 catch(e){executionError.value=e.message}
 finally{busy.value=false}
}
async function readArtifact(item){const id=study.value?.id;if(!id)return;try{const key='record:pbl-'+id+'-'+item.kind+'-'+item.revision;const entry=await api('/knowledge/entry?'+new URLSearchParams({key,session_id:study.value.session_id}));if(study.value?.id===id)artifactReader.value=entry}catch(e){error.value=e.message}}
async function refreshStatus(){const id=study.value?.id;if(!id)return;try{const fresh=await api('/pbl/studies/'+id);if(study.value?.id===id)update(fresh)}catch(e){error.value=e.message}}
function overview(){storeDraft();clearTimeout(executionTimer);++executionPollVersion;execution.value=null;study.value=null;state.pblStudyId=null;history.replaceState(null,'','/app?view=pbl');load()}
watch([plan,code,draft,explanation,chosen,rationale],storeDraft)
watch(stage,value=>{tab.value=value===2?'plan':value===3||value===4?'code':'requirements'})
onMounted(load)
onUnmounted(()=>{disposed=true;++loadVersion;++executionPollVersion;clearTimeout(executionTimer)})
const {page:eventPage,items:eventRows}=usePagination(()=>[...(study.value?.events||[])].reverse(),()=>study.value?.id)
</script>
<template>
<section class="pbl-page"><header class="pbl-heading"><button class="text-button" @click="navigate('explore')">‹ 返回课程广场</button><p>课程广场 / 编程与智能 / 项目学习</p><h1>{{ project?.title||'项目学习' }}</h1><span>把变量、条件与循环，连成一个可以解释的小项目。</span><img src="/assets/competition-v1/pbl/laptop.png.webp" alt=""></header>
 <p v-if="loading" role="status">正在读取保存的项目…</p><div v-if="error" class="pbl-error" role="alert"><span>{{ error }}</span><button :disabled="busy" @click="load">刷新项目记录</button></div><p v-if="draftWarning" role="status" class="pbl-draft-warning">{{ draftWarning }}</p>
 <template v-if="project&&!loading"><section v-if="!study" class="pbl-overview"><div><span class="course-tag lavender">项目式学习</span><h2>从想清楚，到做出来。</h2><p>{{ project.description }}</p><h3>你将完成</h3><p>{{ project.contract }}</p><ol><li>说清输入与输出，记录自己的选择。</li><li>保存计划和代码，让林知围绕当前版本给出建议。</li><li>在隔离环境中检查结果，再用测验和复盘检查理解。</li></ol><button class="primary-button" :disabled="busy||state.designPreview" @click="start">{{ busy?'正在打开…':catalog.studies.length?'继续项目学习':'开始项目学习' }}</button><p class="pbl-subtle">项目记录保存在当前学习空间；阅读介绍不会创建学习记录。</p></div><aside><img src="/assets/competition-v1/pbl/laptop.png.webp" alt="项目编程插画"><h3>{{ runtime.label }}</h3><p>{{ runtimeMessage }}</p><details><summary>流程来源</summary><p>采用 OpenMAIC v1.4.0 的阶段状态机；知行伴学适配持久化、辅导和执行。</p></details></aside></section>
 <template v-else><nav class="pbl-stage-nav" aria-label="项目阶段"><span v-for="(label,index) in project.stages" :key="label" :class="{active:stage===index,done:study.completed_stages.includes(index)}" :aria-current="stage===index?'step':undefined"><b>{{ index+1 }}</b>{{ label }}</span></nav><div v-if="study.status==='completed'" class="pbl-completed"><h2>项目过程已完成</h2><p>报告依据已保存的选择、产物、实际检查、测验与复盘，不等同于长期掌握认证。</p><button class="secondary-button" @click="evidenceTab='evidence'">查看过程记录</button></div>
 <div class="pbl-workspace"><main><TabsRoot v-model="tab" class="pbl-artifact"><TabsList class="pbl-artifact-tabs" aria-label="项目文件"><TabsTrigger value="requirements">项目要求</TabsTrigger><TabsTrigger value="plan">PLAN.md</TabsTrigger><TabsTrigger value="code">main.py</TabsTrigger></TabsList><TabsContent value="requirements"><h2>{{ stage===0?'先理解这个项目':project.stages[stage]+' · 当前任务' }}</h2><p class="pbl-contract">{{ project.contract }}</p><template v-if="stage===0"><p class="pbl-lesson">{{ project.lesson }}</p><label>用自己的话说说，准备怎样合并重复主题的时长？<textarea v-model="explanation" rows="4" maxlength="3000" placeholder="写下当前理解，或说明还有哪里不确定…"></textarea></label><small>这是你的解释记录，不自动判定独立掌握。</small></template><template v-else-if="stage===1"><h3>{{ project.decisions[0].decisionPrompt }}</h3><label>我的选择<textarea v-model="chosen" rows="3" maxlength="2000"></textarea></label><label>选择的理由<textarea v-model="rationale" rows="3" maxlength="2000"></textarea></label><button class="primary-button" :disabled="busy||!chosen.trim()||!rationale.trim()" @click="command('decision',{chosen,rationale})">保存我的决策</button><p v-if="study.collected.decisions.length" class="pbl-saved">已保存：{{ study.collected.decisions[0].chosen }}</p></template><template v-else-if="stage===5"><fieldset v-for="(question,index) in project.quiz" :key="question.q" class="pbl-quiz"><legend>{{ index+1 }}. {{ question.q }}</legend><label v-for="(option,optionIndex) in question.options" :key="option"><input v-model="answers[index]" type="radio" :name="'pbl-quiz-'+index" :value="optionIndex">{{ option }}</label></fieldset><button class="primary-button" :disabled="busy||project.quiz.some((_,i)=>!Number.isInteger(answers[i]))" @click="command('quiz',{answers})">提交测验</button><p v-if="study.collected.quiz" role="status">本次答对 {{ study.collected.quiz.score }} / {{ study.collected.quiz.total }} 题。{{ study.collected.quiz.passed?'可以继续复盘。':'请回看自己的理解，再重新作答。' }}</p></template><template v-else-if="stage===6"><label>哪些选择有效，哪里需要改进？<textarea v-model="explanation" rows="6" maxlength="4000" :disabled="study.status==='completed'"></textarea></label></template><p v-else>在文件页签中查看或保存对应产物；实际运行结果会显示在下方。</p></TabsContent>
 <TabsContent v-for="kind in ['plan','code']" :key="kind" :value="kind"><div class="pbl-editor-heading"><h2>{{ kind==='plan'?'写下你的实现计划':'按计划实现并检查' }}</h2><span>{{ !study.artifacts[kind]?'尚未保存':(kind==='plan'?plan:code)!==study.artifacts[kind].text?'草稿 · 尚未保存':'已保存 v'+study.artifacts[kind].revision }}</span></div><textarea v-if="kind==='plan'" v-model="plan" class="pbl-source-editor" aria-label="项目计划" rows="15" maxlength="20000" :readonly="stage!==2||busy" placeholder="要解决的问题、输入与输出、实现步骤、准备怎样检查…"></textarea><textarea v-else v-model="code" class="pbl-source-editor code" aria-label="项目代码" rows="15" maxlength="20000" spellcheck="false" :readonly="!(stage===3||stage===4&&study.collected.remediation&&study.collected.tests?.status!=='passed')||busy||executionActive||study.busy"></textarea><div v-if="editable" class="pbl-editor-actions"><small v-if="stage===4">根据检查反馈修正，保存后重新运行当前版本。</small><small v-else>{{ dirty?'先保存内容，再请求当前版本的建议。':reviewed?'林知已给出当前版本建议，请自己核对并决定是否继续。':'保存后可以请求林知审阅。' }}</small><button class="secondary-button" :disabled="busy||executionActive||study.busy||!dirty||!currentText.trim()" @click="save">{{ busy?'保存中…':kind==='plan'?'保存计划':'保存代码' }}</button><button v-if="stage===2||stage===3" class="primary-button" :disabled="busy||chatBusy||dirty||!study.artifacts[kind]" @click="chat(true)">{{ chatBusy?'林知正在审阅…':'请林知审阅' }}</button></div><p v-else class="pbl-subtle">当前阶段只读；历史内容可以回看。</p></TabsContent></TabsRoot>
 <TabsRoot v-model="evidenceTab" class="pbl-evidence"><TabsList aria-label="项目证据视图"><TabsTrigger value="runs">运行记录</TabsTrigger><TabsTrigger value="report">过程报告</TabsTrigger><TabsTrigger value="evidence">学习证据</TabsTrigger></TabsList><TabsContent value="runs"><section v-if="execution" class="execution-status" :class="execution.state" aria-live="polite"><h3>{{ ({pending:'检查已排队',running:'正在检查当前保存版本',passed:'检查通过',failed:'当前版本需要修正',unknown:'检查结果尚未确认',cancelled:'已停止等待'})[execution.state] }}</h3><p>{{ execution.detail }}</p><small>{{ execution.current_version?'当前保存版本':'历史版本记录' }} · {{ execution.source_sha256.slice(0,10) }}</small><p v-if="executionActive">可以离开页面，返回后继续查看。</p><div><button class="secondary-button" :disabled="busy" @click="pollExecution()">查询这次检查</button><button v-if="executionActive" class="text-button" :disabled="busy" @click="stopWaiting">停止等待</button></div></section><p v-if="executionError" class="inline-error" role="alert">{{ executionError }} <button class="text-button" @click="pollExecution()">重新查询</button></p><template v-if="study.collected.tests"><h3>{{ study.collected.tests.status==='passed'?'当前版本检查通过':'当前版本需要修正' }}</h3><p>{{ study.collected.tests.publicFeedback }}</p><ul><li v-for="check in study.collected.tests.publicDiagnostics.caseResults" :key="check.id">{{ check.passed?'✓':'○' }} {{ check.label }}</li></ul><small>结果绑定保存版本：{{ study.collected.tests.revision.id.slice(0,12) }}</small></template><div v-else class="pbl-no-runs"><img src="/assets/competition-v1/pbl/books.png.webp" alt=""><p>当前保存版本还没有可用的检查结果，运行回执与历史记录会保留在这里。</p></div><button v-if="stage===4" class="primary-button" :disabled="busy||!runtime.available||codeDirty||executionActive||study.busy" @click="evaluate">{{ executionActive?'检查进行中…':busy?'正在提交检查…':'运行与测试' }}</button></TabsContent><TabsContent value="report"><PblProcessReport :study="study" @refresh="refreshStatus" @artifact="readArtifact"/></TabsContent><TabsContent value="evidence"><ol><li v-for="entry in eventRows" :key="entry.id"><span>{{ new Date(entry.created_at).toLocaleString('zh-CN') }}</span><strong>{{ ({'session.started':'开始项目','stage.entered':'进入阶段','stage.completed':'确认阶段','decision.recorded':'保存决策','artifact.recorded':'保存产物','evaluation.recorded':'实际检查','quiz.recorded':'提交测验','session.completed':'完成项目'})[entry.kind]||'保存学习过程' }}</strong></li></ol><RecordPagination v-model="eventPage" :total="study.events.length" label="项目学习证据"/><p>记录来自实际保存与执行，不用模型文字代替完成回执。</p></TabsContent></TabsRoot>
 </main><aside class="pbl-mentor"><header><img :src="artwork.mentor" alt="林知导师"><div><h2>林知 <span>{{ study.role_label }}</span></h2><p>先说清思路，再动手实现。</p></div></header><div class="pbl-conversation" role="log" aria-label="项目辅导对话" aria-live="polite"><article v-for="message in study.messages.filter(m=>m.stage===stage)" :key="message.id" :class="message.role"><strong>{{ message.role==='user'?'我':'林知' }}</strong><MessageBody :text="message.content"/><small v-if="message.metadata.review_kind">{{ message.metadata.review_accepted?'基于保存版本的建议':'历史版本建议，请以当前内容为准' }} · 不是运行测试</small></article><div v-if="!study.messages.some(m=>m.stage===stage)" class="pbl-mentor-empty"><img :src="artwork.mentor" alt=""><h3>{{ study.status==='completed'?'回看这次的选择与检查记录。':stage===4||stage===5?'先独立检查，再回看思路。':'把当前的问题说给林知听。' }}</h3><p>{{ study.status==='completed'?'本次项目已结束，可查看过程报告与已保存的版本；也可以前往学习伙伴继续讨论。':stage===4||stage===5?'测试与测验按保存结果推进，答疑不会代替检查。':'可以问概念、选择的依据，或请林知检查保存的计划与代码。' }}</p></div></div><form v-if="![4,5].includes(stage)&&study.status!=='completed'" class="pbl-composer" @submit.prevent="chat(false)"><label class="sr-only" for="pbl-message">向项目导师提问</label><textarea id="pbl-message" v-model="draft" aria-label="向项目导师提问" rows="3" maxlength="4000" placeholder="说说你的想法，或向林知提问…"></textarea><p v-if="chatError" role="alert">{{ chatError }}</p><footer><span>{{ draft.length }}/4000</span><button class="primary-button" :disabled="chatBusy||!draft.trim()">{{ chatBusy?'正在回答…':chatError?'重试发送':'发送' }}</button></footer></form></aside></div>
 <footer class="pbl-status-strip"><div><strong>{{ runtime.label }}</strong><p>{{ runtimeMessage }}</p></div><button class="secondary-button" :disabled="busy" @click="overview">回到项目概览</button><button class="primary-button" :disabled="!canNext" @click="next">{{ study.status==='completed'?'项目已完成':stage===2?'确认计划并继续':stage===3?'确认代码并继续':stage===6?'保存复盘并完成':'保存并进入下一步' }}</button></footer>
 </template></template>
<SourceReader v-if="artifactReader" :entry="artifactReader" return-label="返回项目" :can-discuss="false" @close="artifactReader=null"/>
</section>
</template>
