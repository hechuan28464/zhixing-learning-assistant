<script setup>
import {computed,nextTick,ref,watch} from 'vue'
import {useDialogFocus} from '../../useDialogFocus.js'
const props=defineProps({space:Object,busy:Boolean,error:String})
const emit=defineEmits(['retry'])
const dialog=ref(null)
const destination=computed(()=>'/app?'+new URLSearchParams({space:props.space.id,view:'lesson'}))
useDialogFocus(dialog)
watch(()=>props.error,message=>{if(message)nextTick(()=>dialog.value?.querySelector('button[autofocus]')?.focus())})
</script>
<template><dialog ref="dialog" class="form-dialog entry-handoff-dialog" @cancel.prevent><div class="dialog-intro"><span>接续你的学习</span><h2>{{ error?'目标已创建，资料还需要处理':'正在打开你的学习目标…' }}</h2><p v-if="!error" role="status">正在关联资料，请稍候。</p><p v-else>资料仍在当前页面。你可以重试保存，也可以先进入已经创建好的目标。</p></div><p v-if="error" class="inline-error" role="alert">{{ error }}</p><div v-if="error" class="dialog-actions"><button autofocus class="primary-button" :disabled="busy" @click="emit('retry')">{{ busy?'正在重试…':'重试保存资料' }}</button><a class="secondary-button" :href="destination">跳过资料，先进入目标</a></div></dialog></template>
