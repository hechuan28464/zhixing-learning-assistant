<script setup>
import RecordPagination from './ui/RecordPagination.vue'
import {usePagination} from '../usePagination.js'
import {computed,nextTick,onMounted,ref} from 'vue'
import {ComboboxRoot,ComboboxAnchor,ComboboxInput,ComboboxContent,ComboboxViewport,ComboboxItem} from 'reka-ui'
import {icon} from '../assets.js'
const props=defineProps({items:Array,selectedKeys:Array,loading:Boolean,error:String,canRetry:Boolean})
const emit=defineEmits(['select','close','attach','retry'])
const query=ref(''),input=ref(null)
const visible=computed(()=>props.items.filter(item=>(item.title+' '+item.source).toLowerCase().includes(query.value.trim().toLowerCase())))
function focusSearch(){nextTick(()=>{const el=input.value?.$el||input.value;el?.focus()})}
defineExpose({focusSearch})
onMounted(focusSearch)
const {page:referencePage,items:referenceRows}=usePagination(visible,()=>query.value)
</script>
<template><ComboboxRoot class="citation-reference-picker reference-combobox" :model-value="selectedKeys" :multiple="true" :open="true" :ignore-filter="true" :reset-search-term-on-blur="false" :reset-search-term-on-select="false" @update:model-value="emit('select',$event)" @update:open="value=>{if(!value)emit('close','outside')}"><header><strong>选择引用资料 <small>{{ selectedKeys.length }}/3</small></strong><button type="button" aria-label="关闭资料选择" @click="emit('close','trigger')">×</button></header><ComboboxAnchor as-child><label class="reference-search-surface"><img :src="icon('search')" alt=""><ComboboxInput ref="input" v-model="query" aria-label="筛选可引用资料" placeholder="搜索标题或来源…" autocomplete="off"/></label></ComboboxAnchor><p v-if="error" class="inline-error" role="alert">{{ error }} <button v-if="canRetry" type="button" class="text-button" @click="emit('retry')">重新读取</button></p><ComboboxContent position="inline" class="citation-reference-options" @escape-key-down.prevent="emit('close','trigger')"><p v-if="loading" role="status">正在读取可用资料…</p><ComboboxViewport v-else><ComboboxItem v-for="item in referenceRows" :key="item.key" :value="item.key" :text-value="item.title" class="reference-select-item"><img :src="icon(selectedKeys.includes(item.key)?'check':'file-text')" alt=""><span><strong>{{ item.title }}</strong><small>{{ item.source }}</small></span></ComboboxItem><p v-if="!visible.length" role="status">{{ query?'没有匹配的资料，可以换个关键词。':'当前空间还没有资料，可以先导入一份。' }}</p></ComboboxViewport></ComboboxContent><RecordPagination v-model="referencePage" :total="visible.length" label="可引用资料"/><p class="reference-keyboard-help">↑ ↓ 移动 · Enter 选择 · Esc 收起；最多引用 3 份。</p><footer><button type="button" class="text-button" @click="emit('attach')">导入 TXT / Markdown 资料</button><button type="button" class="secondary-button" @click="emit('close','composer')">完成选择</button></footer></ComboboxRoot></template>
