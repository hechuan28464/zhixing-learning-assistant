<script setup>
import {useDialogFocus} from '../useDialogFocus.js'
import { computed,onMounted,ref } from 'vue'
const props=defineProps({entry:Object,action:String,busy:Boolean,error:String})
const emit=defineEmits(['close','confirm'])
const dialog=ref(null)
const copy=computed(()=>({confirm:{title:'确认保存这条学习记忆？',impact:'保存后，导师可据此调整讲解方式。你随时可以撤回。',button:'确认保存'},ignore:{title:'确认忽略这条记忆建议？',impact:'忽略后不作为学习记忆使用，原始对话仍保留。',button:'确认忽略'},revoke:{title:'确认撤回这条学习记忆？',impact:'撤回后，后续辅导不再使用这条记忆。原始对话和历史辅导仍保留。',button:'确认撤回'}}[props.action]))
useDialogFocus(dialog)
</script>
<template><dialog ref="dialog" class="memory-confirm-dialog" aria-labelledby="memory-confirm-title" @cancel.prevent="!busy&&emit('close')"><button class="dialog-close" aria-label="关闭记忆确认" :disabled="busy" @click="emit('close')">×</button><img class="memory-dialog-art" src="/assets/split-elements/elements/memory-sprout.compact.webp" alt="" @error="$event.target.hidden=true"><span class="knowledge-type">{{ entry.status==='confirmed'?'已确认记忆':'待确认记忆' }}</span><h2 id="memory-confirm-title">{{ copy.title }}</h2><p class="memory-full-text">{{ entry.text }}</p><div class="memory-source-quote"><strong>对话原文</strong><blockquote>{{ entry.quote }}</blockquote><small>{{ entry.source_title }}</small></div><p class="memory-impact">{{ copy.impact }}</p><p v-if="error" class="inline-error" role="alert">{{ error }}</p><div class="dialog-actions"><button class="secondary-button" :disabled="busy" autofocus @click="emit('close')">{{ action==='ignore'?'返回':'取消' }}</button><button class="primary-button" :disabled="busy" @click="emit('confirm')">{{ busy?'正在保存…':copy.button }}</button></div></dialog></template>
