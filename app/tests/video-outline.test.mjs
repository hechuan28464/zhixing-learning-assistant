import test from 'node:test'
import assert from 'node:assert/strict'
import {studyOutline} from '../src/videoOutline.js'
test('legacy outline expands only saved chapter sentences with original evidence ids',()=>{
 const old={label:'函数',children:[{label:'调用',children:[]}]},section={title:'调用函数',body:'print接收文字。括号表示调用。',segment_ids:['s1','s2']}
 const result=studyOutline(old,[section])
 assert.equal(result.children[0].children.length,2)
 assert.equal(result.children[0].children[0].detail,'print接收文字。')
 assert.deepEqual(result.children[0].children[1].segment_ids,['s1','s2'])
 assert.equal(old.children[0].children.length,0)
 assert.equal(result.derived,'saved_sections')
})
test('a sufficiently detailed generated hierarchy is kept unchanged',()=>{
 const tree={label:'主题',children:[{label:'模块',children:[{label:'实例',children:[]}]}]}
 assert.equal(studyOutline(tree,[{title:'其他',body:'不应插入。'}]),tree)
})
