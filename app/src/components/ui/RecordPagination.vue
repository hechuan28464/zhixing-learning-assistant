<script setup>
import {computed,watch} from 'vue'
import {PAGE_SIZE,pageNumbers} from '../../usePagination.js'
const props=defineProps({modelValue:{type:Number,default:1},total:{type:Number,default:0},label:{type:String,default:'记录'},pageSize:{type:Number,default:PAGE_SIZE},summary:{type:String,default:''},disabled:Boolean})
const emit=defineEmits(['update:modelValue'])
const count=computed(()=>Math.max(1,Math.ceil(props.total/props.pageSize)))
const pages=computed(()=>pageNumbers(props.modelValue,count.value))
watch(count,n=>{if(props.modelValue>n)emit('update:modelValue',n)})
function change(n){if(!props.disabled&&n>=1&&n<=count.value&&n!==props.modelValue)emit('update:modelValue',n)}
</script>
<template><nav v-if="total>pageSize" class="record-pagination" :aria-label="label+'分页'" :aria-busy="disabled"><span class="record-page-summary">{{ summary||('共 '+total+' 条 · 每页 '+pageSize+' 条') }}</span><div><button type="button" :disabled="disabled||modelValue<=1" aria-label="上一页" @click="change(modelValue-1)">上一页</button><template v-for="(number,index) in pages" :key="number"><span v-if="index&&number>pages[index-1]+1" class="page-ellipsis" aria-hidden="true">…</span><button type="button" :disabled="disabled" :aria-label="'第 '+number+' 页'" :aria-current="modelValue===number?'page':undefined" @click="change(number)">{{ number }}</button></template><button type="button" :disabled="disabled||modelValue>=count" aria-label="下一页" @click="change(modelValue+1)">下一页</button></div><span class="sr-only" aria-live="polite">{{ label }}，第 {{ modelValue }} 页，共 {{ count }} 页</span></nav></template>
<style scoped>
.record-pagination{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:18px;padding:16px 0 4px;border-top:1px solid #e0eae5;font-size:13px;color:#607d77}.record-pagination>div{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.record-pagination button{min-width:34px;min-height:34px;border:1px solid #d8e5df;border-radius:8px;background:#fff;color:#235e59;padding:5px 9px;font:inherit;cursor:pointer}.record-pagination button[aria-current=page]{background:#20645e;border-color:#20645e;color:#fff}.record-pagination button:disabled{opacity:.45;cursor:default}.record-pagination button:focus-visible{outline:2px solid #318b7e;outline-offset:3px}.page-ellipsis{padding:0 3px}
</style>
