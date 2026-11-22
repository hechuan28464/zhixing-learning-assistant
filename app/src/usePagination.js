import {computed,ref,toValue,watch} from 'vue'

export const PAGE_SIZE=10
export function pageNumbers(page,count){
  if(count<=7)return Array.from({length:count},(_,i)=>i+1)
  return [...new Set([1,...Array.from({length:5},(_,i)=>page-2+i).filter(n=>n>1&&n<count),count])].sort((a,b)=>a-b)
}
export function usePagination(source,resetKey=()=>null){
  const page=ref(1)
  const total=computed(()=>toValue(source)?.length||0)
  const count=computed(()=>Math.max(1,Math.ceil(total.value/PAGE_SIZE)))
  watch(count,n=>{page.value=Math.min(page.value,n)},{flush:'sync'})
  watch(resetKey,()=>{page.value=1})
  const items=computed(()=>(toValue(source)||[]).slice((page.value-1)*PAGE_SIZE,page.value*PAGE_SIZE))
  return {page,total,items}
}
