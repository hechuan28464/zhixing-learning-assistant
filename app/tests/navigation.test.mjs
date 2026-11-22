import test from 'node:test'
import assert from 'node:assert/strict'
import {randomFillSync} from 'node:crypto'
import {requestId} from '../src/requestId.js'
import {useLearning} from '../src/useLearning.js'

test('HTTP IP origin can create request IDs without crypto.randomUUID',()=>{
 const original=Object.getOwnPropertyDescriptor(globalThis,'crypto')
 Object.defineProperty(globalThis,'crypto',{configurable:true,value:{getRandomValues:array=>randomFillSync(array)}})
 try{const ids=new Set(Array.from({length:100},()=>requestId()));assert.equal(ids.size,100);for(const id of ids)assert.match(id,/^[a-f\d]{8}-[a-f\d]{4}-4[a-f\d]{3}-[89ab][a-f\d]{3}-[a-f\d]{12}$/)}
 finally{if(original)Object.defineProperty(globalThis,'crypto',original);else delete globalThis.crypto}
})

for(const initialView of ['lesson','buddy','graph']) test('a task action from '+initialView+' opens the exact lesson diagnostic',async()=>{
 const originalFetch=globalThis.fetch,originalLocation=globalThis.location,originalStorage=globalThis.localStorage,originalHistory=globalThis.history
 const {state,executeTaskAction}=useLearning()
 const lesson=id=>({id,tasks:[{id:id+'-diag',purpose:'diagnostic'}],practice:{id:id+'-diag'},review:{id:id+'-review'}})
 const session={id:'s1',course_id:'mathematics',current_lesson:initialView==='lesson'?'first':'second',lessons:[lesson('first'),lesson('second')],attempts:[]}
 state.current=structuredClone(session);state.designPreview=false;state.view=initialView;let url='';const calls=[]
 globalThis.location={pathname:'/app'};globalThis.localStorage={getItem:()=>null,setItem:()=>{}};globalThis.history={replaceState:(_,__,value)=>{url=value}}
 globalThis.fetch=async(path,options={})=>{
  calls.push([path,options.method||'GET'])
  let result
  if(path==='/api/sessions/s1'&&!options.method)result=structuredClone(session)
  else if(path==='/api/sessions/s1/lessons/second'){session.current_lesson='second';result=lesson('second')}
  else if(path.endsWith('/next'))result={kind:'diagnostic',lesson_id:'second',task_id:'second-diag'}
  else if(path.endsWith('/evidence'))result={lessons:{}}
  else if(path.endsWith('/tasks/open')){assert.equal(JSON.parse(options.body).task_id,'second-diag');result={run_id:'r1',task:{id:'second-diag'},assistance:[]}}
  else throw new Error('Unexpected request '+path)
  return new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json'}})
 }
 try{
  await executeTaskAction({kind:'advance',lesson_id:'second',task_id:'second-diag'})
  assert.equal(state.view,'lesson');assert.equal(state.current.current_lesson,'second');assert.equal(state.run.task.id,'second-diag');assert.match(url,/lesson=second/);assert.match(url,/task=second-diag/);assert.equal(state.error,'')
  if(initialView==='lesson')assert.ok(calls.some(([p,m])=>p.endsWith('/lessons/second')&&m==='POST'))
 }finally{globalThis.fetch=originalFetch;globalThis.location=originalLocation;globalThis.localStorage=originalStorage;globalThis.history=originalHistory}
})

test('chat creation uses a generated ID and retains the question when AI is disabled',async()=>{
 const originalFetch=globalThis.fetch;const {state,sendChat}=useLearning();state.current={id:'s1',lessons:[],messages:[]};state.run=null;state.chatBusy=false;let posted=false
 globalThis.fetch=async(path,options={})=>{
  if(path.endsWith('/chat')){assert.match(JSON.parse(options.body).request_id,/^[a-f\d-]{36}$/);posted=true;return new Response(JSON.stringify({detail:'AI 服务暂未开启。'}),{status:503})}
  return new Response(JSON.stringify({id:'s1',messages:[]}))
 }
 try{assert.equal(await sendChat('保持这条输入'),false);assert.ok(posted);assert.match(state.error,/AI 服务暂未开启/);assert.equal(state.chatBusy,false)}finally{globalThis.fetch=originalFetch}
})

test('a truncated service response keeps the original goal and shows a recoverable message',async()=>{
 const originalFetch=globalThis.fetch;const {state,openSession}=useLearning()
 state.current={id:'original',lessons:[]};state.error=''
 globalThis.fetch=async()=>new Response('',{status:502})
 try{await openSession('another',null,'buddy');assert.equal(state.current.id,'original');assert.match(state.error,/输入已保留/);assert.doesNotMatch(state.error,/JSON|SyntaxError|Unexpected/)}finally{globalThis.fetch=originalFetch}
})
