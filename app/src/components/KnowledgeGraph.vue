<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { api } from '../useLearning.js'
import { icon } from '../assets.js'
const props=defineProps({sessionId:String})
const emit=defineEmits(['open-lesson','open-space','open-material'])
const data=ref(null),error=ref(''),loading=ref(false),selected=ref(null),showSequence=ref(true)
const viewport=ref(null),availableWidth=ref(620),zoom=ref(1)
let observer
watch(viewport,element=>{observer?.disconnect();if(!element)return;const measure=()=>{availableWidth.value=Math.max(160,Math.floor(element.clientWidth)-2)};measure();observer=new ResizeObserver(measure);observer.observe(element)})
onUnmounted(()=>{++revision;observer?.disconnect()})
watch(()=>props.sessionId,()=>{zoom.value=1})
function fit(){zoom.value=1;if(viewport.value){viewport.value.scrollLeft=0;viewport.value.scrollTop=0}}
let revision=0
async function load(){
  const version=++revision
  if(!props.sessionId){data.value=null;return}
  loading.value=true;error.value=''
  try{const result=await api('/sessions/'+props.sessionId+'/graph');if(version!==revision)return;data.value=result;selected.value=result.nodes.find(n=>n.kind!=='goal')?.id||result.nodes[0]?.id}
  catch(e){if(version===revision)error.value=e.message}
  finally{if(version===revision)loading.value=false}
}
watch(()=>props.sessionId,load,{immediate:true})
const objectives=computed(()=>data.value?.nodes.filter(n=>n.kind!=='goal')||[])
const width=computed(()=>availableWidth.value)
const columns=computed(()=>Math.max(1,Math.min(objectives.value.length||1,Math.floor((width.value-24)/245))))
const positioned=computed(()=>{
  if(!data.value)return []
  return data.value.nodes.map((node,index)=>{
    const row=Math.floor((index-1)/columns.value),column=(index-1)%columns.value
    const inRow=Math.min(columns.value,objectives.value.length-row*columns.value)
    return {...node,x:index===0?width.value/2:width.value/2+(column-(inRow-1)/2)*(width.value/columns.value),y:index===0?28:215+row*205,w:index===0?Math.min(270,width.value-32):Math.min(220,width.value/columns.value-24),h:index===0?115:150}
  })
})
const nodeMap=computed(()=>Object.fromEntries(positioned.value.map(n=>[n.id,n])))
const current=computed(()=>data.value?.nodes.find(n=>n.id===selected.value))
const relatedEdges=computed(()=>(data.value?.edges||[]).filter(e=>e.source===selected.value||e.target===selected.value))
const edges=computed(()=>(data.value?.edges||[]).filter(e=>showSequence.value||!['course_sequence','plan_sequence'].includes(e.relation)))
const hasPrerequisites=computed(()=>edges.value.some(e=>e.relation==='declared_prerequisite'))
const height=computed(()=>objectives.value.length?215+Math.ceil(objectives.value.length/columns.value)*205:210)
function path(edge){
  const a=nodeMap.value[edge.source],b=nodeMap.value[edge.target]
  if(!a||!b)return ''
  if(edge.relation==='contains')return `M ${a.x} ${a.y+a.h} C ${a.x} ${a.y+a.h+40},${b.x} ${b.y-40},${b.x} ${b.y}`
  if(a.y!==b.y)return `M ${a.x} ${a.y+a.h} C ${a.x} ${a.y+a.h+35},${b.x} ${b.y-35},${b.x} ${b.y}`
  if(edge.relation==='declared_prerequisite')return `M ${a.x} ${a.y+a.h} C ${a.x} ${a.y+a.h+35},${b.x} ${b.y+b.h+35},${b.x} ${b.y+b.h}`
  return `M ${a.x+a.w/2} ${a.y+60} C ${a.x+a.w/2+25} ${a.y+30},${b.x-b.w/2-25} ${b.y+30},${b.x-b.w/2} ${b.y+60}`
}
const time=value=>new Intl.DateTimeFormat('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value))
</script>
<template>
<section class="real-knowledge-graph">
  <div v-if="loading" class="graph-loading">正在读取已保存的目标与证据…</div>
  <div v-else-if="error" class="graph-error"><p>{{ error }}</p><button class="secondary-button" @click="load">重新读取图谱</button></div>
  <template v-else-if="data">
    <header class="graph-toolbar"><div><h2>当前目标的知识结构</h2><p>{{ data.nodes.length }} 个已保存节点 · {{ data.edges.length }} 条有出处的结构关系</p></div><label><input type="checkbox" v-model="showSequence">显示路线顺序</label></header>
    <div v-if="data.draft_available" class="graph-draft-notice">当前还有尚未确认的路线草案，未把它当作正式知识节点。<button class="text-button" @click="emit('open-space')">检查草案</button></div>
    <div class="graph-layout">
      <div class="graph-view-column"><div class="graph-view-controls"><button class="secondary-button" @click="fit">查看全图</button><button aria-label="缩小目标图谱" :disabled="zoom<=.7" @click="zoom=Math.max(.7,zoom-.1)">−</button><span>{{ Math.round(zoom*100) }}%</span><button aria-label="放大目标图谱" :disabled="zoom>=1.5" @click="zoom=Math.min(1.5,zoom+.1)">＋</button></div><div ref="viewport" class="graph-canvas-scroll"><div class="graph-scale-space" :style="{width:width*zoom+'px',height:height*zoom+'px'}"><div class="graph-canvas" :style="{width:width+'px',height:height+'px',transform:`scale(${zoom})`}">
        <svg :width="width" :height="height" aria-hidden="true"><defs><marker id="actual-graph-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7" fill="#95b79b"/></marker></defs><path v-for="edge in edges" :key="edge.id" :d="path(edge)" :class="['actual-graph-edge',edge.relation]" marker-end="url(#actual-graph-arrow)"/></svg>
        <button v-for="node in positioned" :key="node.id" :class="['actual-graph-node',node.kind,node.status,{selected:selected===node.id}]" :style="{left:node.x-node.w/2+'px',top:node.y+'px',width:node.w+'px',height:node.h+'px'}" @click="selected=node.id"><span class="graph-node-kind">{{ node.kind==='goal'?'学习目标':node.kind==='plan_objective'?'已确认路线单元':'课程知识单元' }}</span><strong>{{ node.title }}</strong><span v-if="node.kind!=='goal'" class="graph-node-status">{{ node.state_label }}</span><small v-if="node.kind!=='goal'">{{ node.evidence_count }} 次实际作答记录</small></button>
      </div></div></div><div class="graph-legend"><span><i class="contains"></i>空间包含</span><span><i class="sequence"></i>课程／路线顺序</span><span v-if="hasPrerequisites"><i class="prerequisite"></i>课程声明先修</span></div><p class="graph-scroll-note">图谱随可用宽度自动排列。点击节点查看出处与学习证据；放大后可滚动，点击“查看全图”恢复完整视图。顺序不自动等同于知识先修。</p></div>
      <aside v-if="current" class="graph-data-panel"><span class="muted-label">节点数据依据</span><h3>{{ current.title }}</h3><p>{{ current.description }}</p><dl><dt>来源</dt><dd>{{ current.source.label }}</dd><dt>学习状态</dt><dd>{{ current.state_label }}</dd><dt>实际作答</dt><dd>{{ current.evidence_count }} 次</dd></dl><div v-if="current.evidence?.length" class="graph-evidence-list"><h4>最近证据</h4><p v-for="entry in current.evidence" :key="entry.id">{{ entry.label }}<small>{{ time(entry.created_at) }}</small></p></div><button class="primary-button" @click="current.lesson_id?emit('open-lesson',current.lesson_id):emit('open-space')">{{ current.lesson_id?'打开这个学习单元':'回到学习空间' }}</button><details v-if="relatedEdges.length" class="graph-relations"><summary>查看相关关系 · {{ relatedEdges.length }} 条</summary><p v-for="edge in relatedEdges" :key="edge.id"><strong>{{ edge.label }}</strong><span>{{ edge.provenance }}</span></p></details><details><summary>查看记录标识</summary><code>{{ current.source.record_id }}</code></details></aside>
    </div>
    <div v-if="!objectives.length" class="graph-no-structure"><p>目标已经保存，尚未关联课程结构或已确认路线；因此图谱只展示实际存在的目标节点。</p><button class="secondary-button" @click="emit('open-space')">回到目标，整理路线</button></div>
    <div v-if="data.linked_materials.length" class="graph-linked-materials"><h3>明确关联到本空间的资料</h3><button v-for="material in data.linked_materials" :key="material.id" @click="emit('open-material',material.id)"><img :src="icon('file-text')" alt=""><span>{{ material.title }}</span><small>{{ material.source }}</small></button></div>
    <p class="graph-provenance">{{ data.provenance }}<span v-if="data.public_materials_available">另有 {{ data.public_materials_available }} 份公共资料可检索，未自动作为知识关系依据。</span></p>
  </template>
</section>
</template>
