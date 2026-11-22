import test from 'node:test'
import assert from 'node:assert/strict'
import {sourcePages,sourcePageForParagraph} from '../src/sourcePages.js'
test('long single paragraphs cannot bypass source paging and no characters are lost',()=>{
 const text='长原文'.repeat(2000),pages=sourcePages(text,{maxChars:360})
 assert.ok(pages.length>10);assert.equal(pages.flat().map(r=>r.text).join(''),text)
 assert.ok(pages.every(p=>p.length<=4&&p.reduce((n,r)=>n+r.text.length,0)<=360))
 assert.ok(pages.flat().every(r=>r.number===1))
})
test('a paragraph citation selects its containing page without renumbering original paragraphs',()=>{
 const text=Array.from({length:32},(_,i)=>`原文段落${i+1} `+'文'.repeat(100)).join('\n\n')
 const pages=sourcePages(text,{maxChars:360}),page=sourcePageForParagraph(pages,27)
 assert.ok(page>1);assert.ok(pages[page-1].some(r=>r.number===27));assert.equal(pages.flat().length,32)
 assert.deepEqual(sourcePages(''),[[]])
})
