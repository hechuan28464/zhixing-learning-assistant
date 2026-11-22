<script setup>
import RecordPagination from './ui/RecordPagination.vue'
import {usePagination} from '../usePagination.js'
import {computed} from 'vue'
import {useLearning} from '../useLearning.js'
defineProps({expanded:Boolean})
const {state,currentLesson}=useLearning()
const history=computed(()=>(state.current?.attempts||[]).filter(a=>a.result.lesson_id===currentLesson.value?.id))
const purpose={diagnostic:'诊断题',practice:'学习练习',review:'复核题',remediation:'补救题',bridge_demo:'跨科任务'}
function answer(attempt){const l=currentLesson.value;const t=[...(l?.tasks||[]),l?.practice,l?.review].find(t=>t?.id===attempt.task_id);return t?.options?.find(o=>o.id===attempt.response)?.text||attempt.response}
const time=v=>new Intl.DateTimeFormat('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(v))
const {page:historyPage,items:historyRows}=usePagination(history,()=>currentLesson.value?.id)
</script>
<template><details v-if="history.length" :open="expanded" class="attempt-history"><summary>本单元作答记录 · {{ history.length }} 次</summary><article v-for="attempt in historyRows" :key="attempt.id" :id="'evidence-'+attempt.id"><header><strong>{{ purpose[attempt.result.purpose]||'任务' }} · {{ attempt.result.label }}</strong><span>{{ time(attempt.created_at) }}</span></header><p><span>你的作答</span>{{ answer(attempt) }}</p><p class="history-feedback">{{ attempt.result.feedback }}</p><small>{{ attempt.result.independent?'依据当前题族规则有一次未受助复核表现，长期保持未检查。':attempt.result.assistance==='none'?'本次未记录帮助；独立性还需结合题族和暴露情况。':'存在已送达或送达状态未确认的帮助，不计为独立表现。' }}</small><p v-if="attempt.result.diagnosis" class="history-feedback">候选解释：{{ attempt.result.diagnosis.label }}</p><code class="attempt-identifier">记录编号：{{ attempt.id }}</code></article><RecordPagination v-model="historyPage" :total="history.length" label="作答记录"/></details><div v-else class="study-history-empty"><h3>还没有本单元的作答记录</h3><p>完成一次练习后，可以在这里核对当时的题目、结果与帮助条件。</p></div></template>
