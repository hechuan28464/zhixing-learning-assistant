<!-- legacy: 当前已由AttemptHistoryV3取代，仅为旧记录回查保留。 -->
<script setup>
// legacy: v1 作答记录，当前界面使用 AttemptHistoryV3。
import { computed } from 'vue'
import { useLearning } from '../useLearning.js'
const { state, currentLesson } = useLearning()
const history = computed(() => (state.current?.attempts || []).filter(a => a.result.lesson_id === currentLesson.value?.id))
function answer(attempt) {
  const lesson=currentLesson.value
  const task=[lesson?.practice,lesson?.review].find(t=>t?.id===attempt.task_id)
  return task?.options?.find(o=>o.id===attempt.response)?.text || attempt.response
}
const time=value=>new Intl.DateTimeFormat('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'}).format(new Date(value))
</script>
<template><details v-if="history.length" class="attempt-history"><summary>本单元作答记录 · {{ history.length }} 次</summary><article v-for="attempt in history" :key="attempt.id"><header><strong>{{ attempt.result.purpose==='review'?'新题复核':'学习练习' }} · {{ attempt.result.label }}</strong><span>{{ time(attempt.created_at) }}</span></header><p><span>你的作答</span>{{ answer(attempt) }}</p><p class="history-feedback">{{ attempt.result.feedback }}</p><small>{{ attempt.result.independent ? '本次新题未记录帮助；延迟保持仍未验证。' : attempt.result.assistance==='none' ? '本次没有记录帮助，独立证据还需结合题目用途与暴露情况。' : '包含已交付或交付状态未确认的帮助，不计为独立证据。' }}</small></article></details></template>
