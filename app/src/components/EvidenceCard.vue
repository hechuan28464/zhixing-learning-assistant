<script setup>
import {computed} from 'vue'
import {useLearning} from '../useLearning.js'
import {icon} from '../assets.js'
const {state,currentLesson,setLessonTab,fetchLearningContext}=useLearning()
const entries=[['independent','独立表现','target'],['help','帮助程度','headphones'],['coverage','目标覆盖','layers'],['retention','保持','clock']]
const dimensions=computed(()=>state.evidence?.lessons?.[currentLesson.value?.id]?.dimensions||state.current?.states?.[currentLesson.value?.id]?.dimensions||{})
</script>
<template><section class="learning-evidence-card" aria-label="四维学习依据" :aria-busy="state.evidenceBusy"><header><h2>这次学习的依据</h2><button class="text-button" @click="setLessonTab('history')">查看依据 <img :src="icon('chevron-right')" alt=""></button></header><div class="evidence-four"><article v-for="[key,label,glyph] in entries" :key="key"><h3><img :src="icon(glyph)" alt="">{{ label }}</h3><strong>{{ dimensions[key]?.label||(key==='retention'?'未检查':'等待记录同步') }}</strong><p>{{ dimensions[key]?.basis||(key==='retention'?'尚无间隔后的复核记录':'当前尚未取得这一维度的记录') }}</p></article></div><p v-if="state.evidenceError" class="evidence-sync-error" role="status">学习依据暂未同步。<button class="text-button" @click="fetchLearningContext()">重新读取</button></p></section></template>
