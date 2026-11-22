<script setup>
import {computed,ref,watch,onMounted,onUnmounted,nextTick} from 'vue'
import {Markmap} from 'markmap-view'
import {studyOutline} from '../videoOutline.js'
const props=defineProps({outline:Object,sections:{type:Array,default:()=>[]}})
const emit=defineEmits(['select'])
const svg=ref(null),failure=ref(''),branch=ref('all'),selectedNode=ref(null),expanded=ref(false)
const expandedOutline=computed(()=>studyOutline(props.outline,props.sections))
const branchOptions=computed(()=>expandedOutline.value?.children||[])
const currentTree=computed(()=>branch.value==='all'?expandedOutline.value:{...expandedOutline.value,children:[branchOptions.value[Number(branch.value)]].filter(Boolean)})
const nodeIndex=new Map()
function count(node){return node?1+(node.children||[]).reduce((n,c)=>n+count(c),0):0}
const nodeCount=computed(()=>count(expandedOutline.value))
const selectedDetail=computed(()=>selectedNode.value?.detail||props.sections.find(s=>(s.segment_ids||[]).some(id=>selectedNode.value?.segment_ids?.includes(id)))?.body||'点击“查看字幕依据”核对原句；该节点没有额外说明。')
const clock=value=>new Date(Math.max(0,value||0)*1000).toISOString().slice(14,19)
let map,observer
const escape=text=>String(text||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))
function tree(node,path='0'){nodeIndex.set(path,node);return {content:`<button type="button" data-video-node="${path}" data-video-ref="${escape((node.segment_ids||[]).join(','))}">${escape(node.label)}</button>`,children:(node.children||[]).map((child,i)=>tree(child,path+'.'+i))}}
async function render(){await nextTick();if(!svg.value||!currentTree.value)return;try{nodeIndex.clear();map?.destroy();map=Markmap.create(svg.value,{autoFit:true,duration:0,color:node=>['#2a685e','#8a9e79','#bb8654'][Math.abs(node.state?.depth||0)%3],maxWidth:190,paddingX:16,spacingVertical:18},tree(currentTree.value));map.fit();failure.value=''}catch{failure.value='导图暂未绘制完成，请切换标签后重试。'}}
function select(event){const el=event.target.closest('[data-video-node]');if(el){selectedNode.value=nodeIndex.get(el.dataset.videoNode);emit('select',(selectedNode.value?.segment_ids||[]).slice(0,50))}}
function toggleExpanded(){expanded.value=!expanded.value;nextTick(()=>map?.fit())}
async function exportMap(kind){
 if(!svg.value)return
 try{
  const copy=svg.value.cloneNode(true),box=svg.value.getBoundingClientRect()
  copy.setAttribute('xmlns','http://www.w3.org/2000/svg');copy.setAttribute('width',box.width);copy.setAttribute('height',box.height)
  for(const item of copy.querySelectorAll('foreignObject')){const text=document.createElementNS('http://www.w3.org/2000/svg','text');text.setAttribute('x',item.getAttribute('x')||'0');text.setAttribute('y',String(Number(item.getAttribute('y')||0)+18));text.setAttribute('fill','#23554f');text.setAttribute('font-size','15');text.textContent=item.textContent;item.replaceWith(text)}
  const blob=new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml;charset=utf-8'})
  let output=blob
  if(kind==='png'){const url=URL.createObjectURL(blob);try{const picture=new Image();picture.src=url;await picture.decode();const canvas=document.createElement('canvas');canvas.width=Math.ceil(box.width*2);canvas.height=Math.ceil(box.height*2);const ctx=canvas.getContext('2d');ctx.fillStyle='#fffefa';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(picture,0,0,canvas.width,canvas.height);output=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!output)throw new Error('未取得导图图片。')}finally{URL.revokeObjectURL(url)}}
  const url=URL.createObjectURL(output),link=document.createElement('a');link.href=url;link.download='video-mindmap.'+kind;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
 }catch{failure.value='导出没有完成，请重试或使用另一种格式。'}
}
onMounted(()=>{if(nodeCount.value>12)branch.value='0';render();observer=new ResizeObserver(()=>map?.fit());if(svg.value)observer.observe(svg.value)})
watch(()=>props.outline,()=>{branch.value='all';selectedNode.value=null;render()})
watch(currentTree,render)
onUnmounted(()=>{observer?.disconnect();map?.destroy()})
</script>
<template><section :class="['video-map',{'map-expanded':expanded}]" :role="expanded?'dialog':'region'" :aria-modal="expanded||undefined" aria-label="视频学习思维导图" @keydown.esc="expanded&&toggleExpanded()"><div class="video-map-tools"><label>查看范围<select v-model="branch" aria-label="思维导图查看范围"><option value="all">全部模块</option><option v-for="(item,i) in branchOptions" :key="i" :value="String(i)">{{ item.label }}</option></select></label><button type="button" @click="map?.fit()">适应画布</button><button type="button" aria-label="缩小导图" @click="map?.rescale(.8)">−</button><button type="button" aria-label="放大导图" @click="map?.rescale(1.2)">＋</button><button type="button" @click="toggleExpanded">{{ expanded?'退出大图':'全屏阅读导图' }}</button><button type="button" @click="exportMap('svg')">SVG</button><button type="button" @click="exportMap('png')">PNG</button></div><svg ref="svg" aria-label="视频内容思维导图，点击节点查看来源" @click.capture="select" @keydown.enter.capture="select"/><aside v-if="selectedNode" class="video-map-detail"><header><strong>{{ selectedNode.label }}</strong><span v-if="selectedNode.start!=null">{{ clock(selectedNode.start) }}—{{ clock(selectedNode.end) }}</span><button type="button" aria-label="关闭节点说明" @click="selectedNode=null">×</button></header><p>{{ selectedDetail }}</p><button type="button" class="text-button" :disabled="!selectedNode.segment_ids?.length" @click="emit('select',selectedNode.segment_ids||[])">查看字幕依据 · {{ selectedNode.segment_ids?.length||0 }} 个片段</button></aside><p v-if="failure" class="inline-error" role="alert">{{ failure }}</p><p class="video-map-note">{{ branchOptions.length }} 个模块 · {{ nodeCount }} 个节点。{{ expandedOutline?.derived?'根据已保存章节展开；':'' }}点击查看解释与原字幕。</p></section></template>
