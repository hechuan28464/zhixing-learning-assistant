import test from 'node:test'
import assert from 'node:assert/strict'
import {effectScope,ref,nextTick} from 'vue'
import {usePagination,pageNumbers} from '../src/usePagination.js'
import {readLibraryMetadata} from '../src/libraryQuery.js'

test('ten-row boundaries, final page, deletion clamping and scope reset',async()=>{
 const scope=effectScope(),rows=ref(Array.from({length:21},(_,i)=>i)),filter=ref('all')
 const paging=scope.run(()=>usePagination(rows,()=>filter.value))
 assert.deepEqual(paging.items.value,[0,1,2,3,4,5,6,7,8,9])
 paging.page.value=3;assert.deepEqual(paging.items.value,[20])
 rows.value=rows.value.slice(0,10);assert.equal(paging.page.value,1)
 rows.value=Array.from({length:11},(_,i)=>i);paging.page.value=2;assert.deepEqual(paging.items.value,[10])
 filter.value='notes';await nextTick();assert.equal(paging.page.value,1)
 rows.value=[];assert.equal(paging.page.value,1);assert.deepEqual(paging.items.value,[])
 scope.stop()
})
test('large history exposes first/last pages without hundreds of buttons',()=>{
 assert.deepEqual(pageNumbers(2,3),[1,2,3])
 const pages=pageNumbers(50,100);assert.equal(pages[0],1);assert.equal(pages.at(-1),100);assert.ok(pages.includes(50));assert.ok(pages.length<=7)
})
test('reading and citation pickers can reach records beyond the original 100-record cap',async()=>{
 const calls=[],rows=Array.from({length:205},(_,i)=>({key:'note:'+i}))
 const result=await readLibraryMetadata(async url=>{const query=new URL(url,'http://test').searchParams;calls.push(Number(query.get('offset')));return {items:rows.slice(Number(query.get('offset')),Number(query.get('offset'))+100),total:205}},{kind:'material'})
 assert.deepEqual(calls,[0,100,200]);assert.equal(result.items.length,205);assert.equal(result.items.at(-1).key,'note:204')
})
