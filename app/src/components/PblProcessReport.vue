<script setup>
import RecordPagination from './ui/RecordPagination.vue'
import {usePagination} from '../usePagination.js'
import {computed,ref,onMounted,onUnmounted,watch} from 'vue'
import {api} from '../useLearning.js'
const props=defineProps({study:Object})
const emit=defineEmits(['refresh','artifact'])
const report=ref(null),error=ref(''),busy=ref(false)
let version=0,timer
function schedule(){clearTimeout(timer);if(report.value?.busy)timer=setTimeout(load,2500)}
async function load(){const id=props.study?.id;if(!id)return;const rev=++version;busy.value=true;error.value='';try{const data=await api('/pbl/studies/'+id+'/report');if(rev===version&&props.study?.id===id){report.value=data;schedule()}}catch(e){if(rev===version)error.value=e.message}finally{if(rev===version)busy.value=false}}
watch(()=>[props.study?.id,props.study?.revision],load)
onMounted(load)
onUnmounted(()=>{++version;clearTimeout(timer)})
const checks=computed(()=>[...(report.value?.checks||[])].reverse())
const artifacts=computed(()=>[...(report.value?.artifacts||[])].reverse())
const {page:checkPage,items:checkRows}=usePagination(checks,()=>props.study?.id)
const {page:artifactPage,items:artifactRows}=usePagination(artifacts,()=>props.study?.id)
</script>
<template><section class="pbl-process-report" :aria-busy="busy"><p v-if="error" role="alert">{{ error }} <button class="text-button" @click="load">重新读取报告</button></p><p v-if="busy&&!report" role="status">正在读取保存的项目过程…</p><template v-if="report"><dl><dt>已提交阶段</dt><dd>{{ report.committed_steps }} / {{ report.stage_count }}</dd><dt>保存产物</dt><dd>{{ report.artifacts.length }} 个保存版本</dd><dt>检查回执</dt><dd>{{ report.runs.total }} 次（通过 {{ report.runs.passed }} 次，未通过 {{ report.runs.failed }} 次，结果未知 {{ report.runs.unknown }} 次，排队 {{ report.runs.pending||0 }} 次，进行中 {{ report.runs.running||0 }} 次，已停止等待 {{ report.runs.cancelled||0 }} 次）</dd><dt>概念说明</dt><dd>{{ report.concepts_practiced.length?report.concepts_practiced.join('、'):'尚未提交概念说明' }}</dd></dl><p v-if="report.busy" role="status">本次检查仍在进行，状态会自动更新。</p><p v-if="report.current_source_sha&&!report.current_version_checked">当前保存代码尚无匹配的检查回执。历史结果不会认证新版本。</p><details v-if="report.artifacts.length" class="pbl-artifact-history"><summary>保存版本 · {{ report.artifacts.length }} 个</summary><ul><li v-for="item in artifactRows" :key="item.kind+item.revision"><button class="text-button" @click="emit('artifact',item)">{{ item.kind==='plan'?'PLAN.md':'main.py' }} · 第 {{ item.revision }} 版 · {{ item.sha256.slice(0,8) }}</button></li></ul><RecordPagination v-model="artifactPage" :total="report.artifacts.length" label="保存版本"/></details><ul v-if="report.checks.length" class="pbl-report-checks"><li v-for="check in checkRows" :key="check.id">{{ check.current_version?'当前版本':'历史版本' }} · {{ check.source_sha?.slice(0,10) }} · {{ ({passed:'检查通过',failed:'需要修正',unknown:'结果未知',pending:'排队中',running:'正在检查',cancelled:'已停止等待'})[check.state]||'结果待确认' }}<small>{{ check.feedback }}</small></li></ul><RecordPagination v-model="checkPage" :total="report.checks.length" label="检查回执"/><p>{{ report.note }}</p><div class="pbl-report-actions"><button class="secondary-button" :disabled="busy" @click="load();emit('refresh')">{{ busy?'正在查询…':'查询当前状态' }}</button></div></template></section></template>
