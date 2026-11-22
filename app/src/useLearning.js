import {requestId as newRequestId} from './requestId.js'
import { reactive, computed, nextTick } from 'vue'
import {requestLogin,authSession} from './authState.js'

export async function api(path, options = {}) {
  if (state.designPreview && options.method && options.method !== 'GET') throw new Error('这是只读布局预览，不会修改学习记录。请返回正式页面操作。')
  const controller = new AbortController()
  const externalSignal=options.signal
  const abort=()=>controller.abort()
  if(externalSignal?.aborted)controller.abort()
  externalSignal?.addEventListener('abort',abort,{once:true})
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs||100000)
  try {
    const response = await fetch('/api' + path, {
      ...options, signal: controller.signal,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
    let data
    try{data=await response.json()}catch{
      const failure=new Error('学习服务暂时没有返回完整结果，输入已保留，请稍后重试。');failure.status=response.status;throw failure
    }
    if(response.status===401&&data.code==='login_required'&&!options.authRetried){clearTimeout(timeout);await requestLogin();return api(path,{...options,authRetried:true})}
    if (!response.ok) {
      const detail = Array.isArray(data.detail) ? '填写内容未通过检查，请核对字段。' : data.detail
      const failure = new Error(detail || '操作暂时没有完成，请重试。'); failure.status=response.status; failure.retry=data.retry||null; throw failure
    }
    return data
  } catch (error) {
    if (error.name === 'AbortError') {
      if(externalSignal?.aborted){const stopped=new Error('已停止本次回答。');stopped.name='AbortError';throw stopped}
      throw new Error('请求等待时间较长，请稍后刷新记录，或重试。')
    }
    if (error instanceof TypeError) throw new Error('暂时连不上本地学习服务，请检查服务是否启动。')
    throw error
  } finally { clearTimeout(timeout);externalSignal?.removeEventListener('abort',abort) }
}

const state = reactive({
  boot: null, current: null, view: 'home', query: '', loading: true, error: '',
  run: null, answer: '', result: null, hint: '', taskBusy: false, hintBusy: false,
  submitKey: '', chatBusy: false, chatSession: null, chatError:'', planBusy: false,
  newGoal: false, goalSeed: '', materialDialog: false, noteDialog: false,
  editNote: null, materialPreview: null, toast: '',
  designPreview: false,
  lessonTab:'practice', next:null, evidence:null, evidenceBusy:false, evidenceError:'', taskBusyId:'', retryAction:null,
  designPanel: '', knowledgeCitation: null, pblStudyId:null,videoId:null,
})
let navigation = 0
let taskNavigation = 0
let contextNavigation = 0
let toastTimer
let previousChat = null
let activeChat = null
function syncWorkspaceLocation(){
  if(state.designPreview||!/^\/app\/?$/.test(location.pathname))return
  const params=new URLSearchParams()
  if(state.view!=='home')params.set('view',state.view)
  if(state.view==='pbl'&&state.pblStudyId)params.set('study',state.pblStudyId)
  if(state.view==='videos'&&state.videoId)params.set('video',state.videoId)
  if(state.current&&['lesson','buddy'].includes(state.view)){
    params.set('space',state.current.id)
    if(state.view==='lesson'&&state.current.current_lesson){params.set('lesson',state.current.current_lesson);if(state.run?.task?.id)params.set('task',state.run.task.id);if(state.lessonTab!=='practice')params.set('panel',state.lessonTab)}
  }
  history.replaceState(null,'','/app'+(params.size?'?'+params:''))
}
const notify = message => { state.toast = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => state.toast = '', 3500) }

async function refresh() { state.boot = await api('/bootstrap') }
async function initialize() {
  state.loading = true
  try {
    await refresh()
    const params = new URLSearchParams(location.search)
    state.lessonTab=['lecture','practice','history'].includes(params.get('panel'))?params.get('panel'):'practice'
    const saved = localStorage.getItem('zhixing.active-space')
    if (saved && state.boot.sessions.some(s => s.id === saved)) state.current = await api('/sessions/' + saved)
    state.pblStudyId=params.get('study');state.videoId=params.get('video');
    const allowedViews=['videos','pbl','home','learning','explore','graph','reading','projects','notes','buddy','messages','settings','lesson']
    const requestedView=allowedViews.includes(params.get('view'))?params.get('view'):'home'
    const requestedSpace=params.get('space')
    if(requestedSpace){
      if(!state.boot.sessions.some(s=>s.id===requestedSpace))throw new Error('没有找到这个学习目标，可以在“我的学习”中重新选择。')
      await openSession(requestedSpace,params.get('lesson')||undefined,requestedView,params.get('task'))
    }else if(requestedView==='buddy'){
      const target=state.current||state.boot.sessions[0]
      if(target)await openSession(target.id,null,'buddy')
      else navigate('buddy')
    }else navigate(requestedView)
    if(params.get('new')==='1'){state.goalSeed='';state.newGoal=true}
    if(params.get('import')==='1')state.materialDialog=true
  } catch (e) { state.error = e.message }
  finally { state.loading = false }
}
async function fetchLearningContext() {
  const sid=state.current?.id
  if(!sid||state.designPreview)return
  const rev=++contextNavigation
  state.evidenceBusy=true;state.evidenceError=''
  const [next,evidence]=await Promise.allSettled([api(`/sessions/${sid}/next`),api(`/sessions/${sid}/evidence`)])
  if(state.current?.id!==sid||rev!==contextNavigation)return
  state.next=next.status==='fulfilled'?next.value:null
  state.evidence=evidence.status==='fulfilled'?evidence.value:null
  if(evidence.status==='rejected')state.evidenceError=evidence.reason.message
  state.evidenceBusy=false
}
async function executeTaskAction(action){
 const sid=action.sessionId||state.current?.id,taskId=action.task_id||action.taskId,lid=action.lesson_id||action.lessonId
 if(!sid||!taskId)return
 if(state.view!=='lesson'||sid!==state.current?.id||(lid&&lid!==currentLesson.value?.id))return openSession(sid,lid,'lesson',taskId)
 return loadTaskById(taskId)
}
function setLessonTab(tab,focus=false){
  if(!['lecture','practice','history'].includes(tab))return
  state.lessonTab=tab;syncWorkspaceLocation()
  if(focus)nextTick(()=>document.getElementById('lesson-tab-'+tab)?.focus())
}
async function loadTaskById(taskId,{restart=false}={}) {
  if(!state.current||!taskId)return
  const sid=state.current.id,rev=++taskNavigation
  const task=currentLesson.value?.tasks?.find(t=>t.id===taskId)||[currentLesson.value?.practice,currentLesson.value?.review].find(t=>t?.id===taskId)
  if(!task){state.error='这项任务尚未加载，请重新选择当前单元。';return}
  state.taskBusyId=taskId;state.run=null;state.result=null;state.hint='';state.answer='';state.retryAction=null
  try{
    const saved=!restart&&(state.current.attempts||[]).find(a=>a.task_id===taskId)
    if(saved){state.run={run_id:saved.run_id,task,purpose:saved.result.purpose,assistance:[]};state.result={...saved.result,attempt_id:saved.id};state.answer=saved.response}
    else if(state.designPreview){state.run={run_id:'design-only-task',task,purpose:task.purpose||'practice',assistance:[]}}
    else{
      const data=await api(`/sessions/${sid}/tasks/open`,{method:'POST',body:{task_id:taskId}})
      if(rev!==taskNavigation||state.current?.id!==sid)return
      state.run=data;state.submitKey=newRequestId()
      state.answer=localStorage.getItem('zhixing.draft.'+data.run_id)||''
      state.hint=data.assistance.filter(a=>a.delivery==='delivered'&&a.kind==='hint').map(a=>a.content).join('\n')
    }
    syncWorkspaceLocation()
  }catch(e){if(rev===taskNavigation&&state.current?.id===sid){state.error=e.message;state.retryAction=e.retry||{task_id:taskId}}}
  finally{if(rev===taskNavigation)state.taskBusyId=''}
}
async function loadTask(purpose='auto') {
  const lesson=currentLesson.value;if(!lesson)return
  const tasks=lesson.tasks||[]
  const suggested=state.next?.lesson_id===lesson.id?tasks.find(t=>t.id===state.next.task_id):null
  const task=purpose==='auto'?(suggested||tasks.find(t=>t.purpose==='diagnostic')||lesson.practice):(tasks.find(t=>t.purpose===purpose)||lesson[purpose])
  if(task)await loadTaskById(task.id)
}
async function openSession(id,lessonId,view='lesson',preferredTaskId=null) {
  const version=++navigation;++taskNavigation;++contextNavigation
  const initialTaskNavigation=taskNavigation
  state.error='';state.run=null;state.result=null;state.next=null;state.evidence=null;state.evidenceBusy=false
  try{
    const data=await api('/sessions/'+id)
    if(version!==navigation){return}
    state.current=data;state.view=view
    if(!state.designPreview)localStorage.setItem('zhixing.active-space',id)
    if(lessonId&&lessonId!==data.current_lesson){
      await api(`/sessions/${id}/lessons/${lessonId}`,{method:'POST'})
      if(version!==navigation){return}
      state.current.current_lesson=lessonId
    }
    await fetchLearningContext()
    if(version!==navigation){return}
    if(view==='lesson'&&data.lessons.length&&taskNavigation===initialTaskNavigation){if(preferredTaskId)await loadTaskById(preferredTaskId);else await loadTask()}
    if(version===navigation)syncWorkspaceLocation()
  }catch(e){if(version===navigation)state.error=e.message}
}
async function openCourse(courseId,lessonId) {
  try {
      const previous=state.boot?.sessions.some(s=>s.course_id===courseId)
      const target=lessonId||(!previous?state.boot?.courses.find(c=>c.id===courseId)?.entry_lesson_id:undefined)
    const session = await api('/sessions', { method: 'POST', body: { course_id: courseId, daily_minutes: state.boot?.profile?.daily_minutes || 30 } })
      await refresh(); await openSession(session.id,target)
  } catch (e) { state.error = e.message }
}
async function selectLesson(id) {
  if(!state.current)return
  const sid=state.current.id,version=++navigation;++taskNavigation;++contextNavigation
  state.run=null;state.result=null;state.next=null;state.evidence=null;state.error=''
  try{
    await api(`/sessions/${sid}/lessons/${id}`,{method:'POST'})
    if(state.current?.id!==sid||version!==navigation)return
    state.current.current_lesson=id
    await fetchLearningContext()
    if(version!==navigation)return
    await loadTask();syncWorkspaceLocation()
  }catch(e){if(version===navigation)state.error=e.message}
}
function setAnswer(value) {
  state.answer = value
  if (state.run && !state.designPreview) localStorage.setItem('zhixing.draft.' + state.run.run_id, value)
}
async function submitAttempt() {
  if (!state.current || !state.run || !state.answer.trim() || state.taskBusy) return
  const sid = state.current.id, runId = state.run.run_id
  state.taskBusy = true; state.error = ''
  try {
    const result = await api(`/sessions/${sid}/attempts`, { method: 'POST', body: { run_id: runId, response: state.answer, request_id: state.submitKey } })
    if (state.current?.id === sid && state.run?.run_id === runId) {
      state.result = result
      const updated = await api('/sessions/' + sid)
      if (state.current?.id === sid && state.run?.run_id === runId) state.current = updated
      localStorage.removeItem('zhixing.draft.' + runId)
    }
    await refresh()
    if(state.current?.id===sid)await fetchLearningContext()
  } catch (e) { if(state.current?.id===sid&&state.run?.run_id===runId){state.error=e.message;state.retryAction=e.retry||null} }
  finally { state.taskBusy = false }
}
async function hint() {
  if (!state.current || !state.run || state.hintBusy) return
  const sid = state.current.id, runId = state.run.run_id
  state.hintBusy = true
  try {
    const help = await api(`/sessions/${sid}/hints`, { method: 'POST', body: { run_id: runId } })
    if (state.current?.id !== sid || state.run?.run_id !== runId) return
    state.hint = help.content
    await nextTick()
    await api(`/sessions/${sid}/assistance/${help.id}/ack`, { method: 'POST' })
  } catch (e) { state.error = e.message }
  finally { state.hintBusy = false }
}
async function ensureLearningSpace(){
 if(state.current)return state.current
 if(authSession.login_required&&!authSession.authenticated)await requestLogin()
 await refresh()
 const existing=state.boot?.sessions[0]
 if(existing)await openSession(existing.id,null,'buddy')
 else{
  const course=state.boot?.courses[0]
  if(!course)throw new Error('课程暂未加载，请刷新后重试。')
  const session=await api('/sessions',{method:'POST',body:{course_id:course.id,daily_minutes:30}})
  await refresh();await openSession(session.id,null,'buddy')
 }
 return state.current
}
async function stopChat(){
 const active=activeChat;if(!active)return
 active.stopped=true
 const cancellation=api(`/sessions/${active.sid}/chat/cancel`,{method:'POST',body:{request_id:active.requestId},timeoutMs:10000}).catch(()=>null)
 active.controller.abort()
 notify('已停止本次回答。')
 await cancellation
}
async function sendChat(message,referenceIds=[]) {
  const referenceKey=JSON.stringify(referenceIds)
  if (!message.trim() || state.chatBusy) return false
  if(!state.current){try{await ensureLearningSpace()}catch(e){state.error=e.message;return false}}
  const sid = state.current.id
  const requestId = previousChat?.sid === sid && previousChat?.message === message && previousChat?.referenceKey === referenceKey && previousChat?.failed
    ? previousChat.requestId : newRequestId()
  previousChat = { sid, message, requestId, referenceKey, failed: false }
  const active={sid,requestId,controller:new AbortController(),stopped:false};activeChat=active
  state.chatBusy = true; state.chatSession = sid; state.error = '';state.chatError=''
  if(!state.current.messages.some(m=>m.metadata?.request_id===requestId))state.current.messages.push({id:'pending:'+requestId,role:'user',content:message,metadata:{pending:true,request_id:requestId}})
  try {
    const data = await api(`/sessions/${sid}/chat`, { method: 'POST', body: { message, request_id: requestId, run_id: state.run?.run_id || null, reference_ids:referenceIds },signal:active.controller.signal,timeoutMs:300000 })
    if (state.current?.id === sid) {
      const updated = await api('/sessions/' + sid)
      if (state.current?.id !== sid) return true
      state.current = updated
      await nextTick()
      if (data.assistance_id) await api(`/sessions/${sid}/assistance/${data.assistance_id}/ack`, { method: 'POST' })
    }
    await refresh()
    return true
  } catch (e) {
    if(active.stopped){if(state.current?.id===sid)state.current=await api('/sessions/'+sid).catch(()=>state.current);return true}
    previousChat.failed = true; state.error = e.message;state.chatError=e.message
    if (state.current?.id === sid) state.current = await api('/sessions/' + sid).catch(() => state.current)
    return false
  } finally { if(activeChat===active){activeChat=null;state.chatBusy = false; state.chatSession = null} }
}
async function generatePlan() {
  if (!state.current || state.planBusy) return
  const sid = state.current.id
  state.planBusy = true
  try {
    const plan = await api(`/sessions/${sid}/plan`, { method: 'POST' })
    if (state.current?.id === sid) { state.current.plan = plan; state.current.plan_status = 'draft' }
    await refresh(); notify('路线草案已生成，请检查后确认。')
  } catch (e) { state.error = e.message }
  finally { state.planBusy = false }
}
async function confirmPlan() {
  const sid = state.current.id, revision = state.current.plan?.draft?.revision
  if (!revision) return
  try {
    state.current.plan = await api(`/sessions/${sid}/plan/confirm`, { method: 'POST', body: { revision } })
    state.current.plan_status = 'confirmed'; await refresh(); notify('学习路线已确认。')
  } catch (e) { state.error = e.message }
}
function navigate(view) { ++navigation; state.view = view; state.query = ''; state.error = ''; syncWorkspaceLocation() }
const currentLesson = computed(() => state.current?.lessons?.find(l => l.id === state.current.current_lesson) || state.current?.lessons?.[0] || null)
const attempts = computed(() => state.current?.attempts || [])

export function useLearning() {
  return { state, currentLesson, attempts, initialize, refresh, openCourse, openSession, selectLesson,
    loadTask, loadTaskById, executeTaskAction, fetchLearningContext, setLessonTab, setAnswer, submitAttempt, hint, sendChat, stopChat, ensureLearningSpace, generatePlan, confirmPlan, navigate, notify }
}
