import test from 'node:test'
import assert from 'node:assert/strict'
import { buildHomeCards, buildNextActions } from '../src/homeLayout.js'

test('no learner goals means no continue-learning placeholders',()=>{
  assert.deepEqual(buildHomeCards([]),[])
  assert.equal(buildNextActions([]).length,1)
  assert.equal(buildNextActions([])[0].kind,'create')
})
test('one or two goals remain one or two real records',()=>{
  const original=[{id:'one',title:'自己的目标',domain:'跨学科'}]
  assert.equal(buildHomeCards(original).length,1)
  assert.equal(original[0].cardType,undefined)
  assert.equal(buildHomeCards([...original,{id:'two',title:'第二个目标'}]).length,2)
  assert.equal(buildHomeCards([...original,{id:'two'},{id:'three'},{id:'four'}]).length,3)
})
test('search does not pad results with invented learner records',()=>{
  assert.deepEqual(buildHomeCards([{id:'one',title:'数学'}],'不存在的主题'),[])
})
test('next step uses the selected space and its actual assistance evidence',()=>{
  const spaces=[{id:'new',title:'新目标'},{id:'active',title:'当前目标',course_id:'math',current_lesson:'lesson',states:{lesson:{status:'assisted',attempts:1}}}]
  const actions=buildNextActions(spaces,[],'active')
  assert.equal(actions.length,1)
  assert.equal(actions[0].sessionId,'active')
  assert.equal(actions[0].kind,'review')
})
test('unconfirmed route is not presented as a completed learning step',()=>{
  const action=buildNextActions([{id:'one',title:'目标',plan:{draft:{nodes:[]}}}])[0]
  assert.equal(action.kind,'route')
  assert.match(action.title,/确认/)
})

test('backend next action opens the exact task instead of only navigating to a page',()=>{
  const action=buildNextActions([{id:'space',title:'目标',course_id:'mathematics',next:{task_id:'remedy',lesson_id:'math-reference',kind:'remedy',title:'补上这一小步',reason:'来自实际错选'}}])[0]
  assert.equal(action.taskId,'remedy')
  assert.equal(action.lessonId,'math-reference')
  assert.equal(action.sessionId,'space')
  assert.equal(action.reason,'来自实际错选')
})
