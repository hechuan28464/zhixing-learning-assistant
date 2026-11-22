<script setup>
import { computed,ref,watch } from 'vue'
import RecordPagination from './ui/RecordPagination.vue'
const props = defineProps({ text: { type: String, default: '' } })
const blocks = computed(() => props.text.split(/(```[\s\S]*?```)/g).filter(Boolean).map(part =>
  part.startsWith('```') ? { code: true, text: part.replace(/^```[^\n]*\n?/, '').replace(/```$/, '') }
    : { code: false, text: part.replace(/^#{1,6}\s+/gm, '') }))
const page=ref(1)
const pages=computed(()=>{
 const result=[];let rows=[],size=0
 for(const block of blocks.value){
  const pieces=block.code?[block.text]:Array.from({length:Math.ceil(block.text.length/800)},(_,i)=>block.text.slice(i*800,(i+1)*800))
  for(const text of pieces){if(rows.length&&size+text.length>900){result.push(rows);rows=[];size=0}rows.push({...block,text});size+=text.length}
 }
 if(rows.length)result.push(rows)
 return result.length?result:[[]]
})
const visibleBlocks=computed(()=>pages.value[page.value-1]||[])
watch(()=>props.text,()=>page.value=1)
const tokens = text => text.split(/(\*\*[^*]+\*\*)/g)
</script>
<template><div class="message-body"><template v-for="(block,index) in visibleBlocks" :key="index"><pre v-if="block.code"><code>{{ block.text }}</code></pre><div v-else class="message-paragraph"><template v-for="(token,i) in tokens(block.text)" :key="i"><strong v-if="token.startsWith('**') && token.endsWith('**')">{{ token.slice(2,-2) }}</strong><template v-else>{{ token }}</template></template></div></template><RecordPagination v-model="page" :total="pages.length" :page-size="1" :summary="'回答第 '+page+' / '+pages.length+' 页'" label="回答内容"/></div></template>
