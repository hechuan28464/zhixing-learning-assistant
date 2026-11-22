<script setup>
import {ref} from 'vue'
import {useLearning} from '../useLearning.js'
import {artwork,icon} from '../assets.js'
import TutorPanel from './TutorPanel.vue'
const emit=defineEmits(['new-goal','add-material','read-material'])
const {state,openSession}=useLearning()
const tutor=ref(null),switching=ref(false)
async function changeGoal(event){
 const control=event.target
 if(switching.value)return
 switching.value=true
 try{await openSession(control.value,null,'buddy')}
 finally{control.value=state.current?.id||'';switching.value=false}
}
const prompts=[['leaf','帮我梳理一个复杂的问题','请先了解我的目标，再帮我把复杂问题拆成可以观察和核查的小问题。'],['book-open','和我一起精读一段材料','请结合当前课程与相关资料，找出主张、证据和仍需核查的地方。'],['lightbulb','给我的学习计划提建议','请读取我的实际学习记录与已确认路线，建议一个现在可以执行的小步骤。']]
</script>
<template><section class="buddy-page-live"><div class="space-selector"><label>围绕哪个目标讨论<select :value="state.current?.id||''" :disabled="switching||state.chatBusy" @change="changeGoal"><option value="" disabled>选择实际学习目标</option><option v-for="space in state.boot.sessions" :key="space.id" :value="space.id">{{ space.title }}</option></select></label><button class="secondary-button" :disabled="switching||state.chatBusy" @click="emit('new-goal')">新建目标</button></div><div class="buddy-page-grid"><TutorPanel ref="tutor" expanded :disabled="switching" @add-material="emit('add-material',$event)"/><aside><section class="buddy-profile-card"><div class="buddy-profile-portrait"><img :src="artwork.mentor" alt="林知导师"></div><div><h2>林知 <span>学习伙伴 · AI 导师</span></h2><p>和你一起把问题问清楚，把理解变成可以检查的行动。</p><div class="buddy-profile-tags"><span>跨学科思考</span><span>阅读与写作</span><span>问题探讨</span></div></div></section><section class="studio-side-card buddy-question-card"><h2>可以这样和我聊</h2><button v-for="[glyph,label,prompt] in prompts" :key="label" :disabled="switching||state.chatBusy" @click="tutor?.suggest(prompt)"><img :src="icon(glyph)" alt=""><span>{{ label }}</span><img :src="icon('chevron-right')" alt=""></button></section><section class="studio-side-card buddy-reference-card"><div class="section-heading"><h2>相关资料</h2><button class="text-button" :disabled="switching" @click="emit('add-material')">加入资料</button></div><button v-for="material in state.boot.materials.filter(m=>!m.session_id||m.session_id===state.current?.id).slice(0,3)" :key="material.id" :disabled="switching" @click="emit('read-material',material.id)"><img :src="icon('file-text')" alt=""><span><strong>{{ material.title }}</strong><small>{{ material.source }}</small></span></button><p v-if="!state.boot.materials.some(m=>!m.session_id||m.session_id===state.current?.id)">加入自己的讲义或摘录，讨论就有了可追踪的依据。</p><small v-if="state.current">当前目标：{{ state.current.title }}</small><button v-else class="secondary-button" @click="emit('new-goal')">先创建一个学习目标</button></section></aside></div></section></template>
