<script setup>
import {AlertDialogRoot,AlertDialogPortal,AlertDialogOverlay,AlertDialogContent,AlertDialogTitle,AlertDialogDescription,AlertDialogCancel,AlertDialogAction} from 'reka-ui'
defineProps({open:Boolean,title:{type:String,default:'放弃未保存的修改？'},description:{type:String,default:'这些修改还没有保存。继续编辑可以保留当前内容，放弃后将关闭编辑器。'}})
const emit=defineEmits(['keep','discard'])
</script>
<template><AlertDialogRoot :open="open" @update:open="value=>{if(!value)emit('keep')}"><AlertDialogPortal to=".studio-shell"><AlertDialogOverlay class="studio-confirm-overlay"/><AlertDialogContent class="studio-confirm-content"><span class="studio-confirm-symbol" aria-hidden="true">↶</span><AlertDialogTitle class="studio-confirm-title">{{ title }}</AlertDialogTitle><AlertDialogDescription class="studio-confirm-description">{{ description }}</AlertDialogDescription><div class="dialog-actions"><AlertDialogCancel class="primary-button" @click="emit('keep')">继续编辑</AlertDialogCancel><AlertDialogAction class="secondary-button discard-button" @click="emit('discard')">放弃修改</AlertDialogAction></div></AlertDialogContent></AlertDialogPortal></AlertDialogRoot></template>
