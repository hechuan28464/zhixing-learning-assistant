// Public, authored walkthroughs. These are never learner records or model replies.
export const entryArt = Object.freeze({
  question:'/assets/entry/elements/step-question.compact.webp',
  discussion:'/assets/entry/elements/step-discussion.compact.webp',
  practice:'/assets/entry/elements/step-practice.compact.webp',
  reflection:'/assets/entry/elements/step-reflection.compact.webp',
  arch:'/assets/entry/elements/guide-arch.compact.webp',
  knowledge:'/assets/entry/scenes/knowledge-stilllife.png.webp',
  footer:'/assets/entry/scenes/footer-landscape.png.webp',
})
export const walkthroughSteps = [
  {id:'1',title:'提出问题',art:entryArt.question,heading:'先说说，你想弄懂什么？',text:'可以是一道题、一段没读懂的材料，或一个跨学科问题。'},
  {id:'2',title:'带着资料讨论',art:entryArt.discussion,heading:'带上资料，让讨论有依据。',text:'先区分原文、自己的理解和仍不确定的地方，再向林知提问。'},
  {id:'3',title:'解释与练习',art:entryArt.practice,heading:'试着解释，看看哪里还需要再想。',text:'练习的价值在于留下具体表现。一次答对，并不自动代表长期掌握。'},
  {id:'4',title:'回看与调整',art:entryArt.reflection,heading:'回到记录，自己决定下一步。',text:'在知识空间中检索资料、笔记与讨论。学习记忆展示来源，等你确认。'},
]
export const learningExamples = [
  {id:'mathematics',tag:'数学思维',lesson:'math-reference',art:entryArt.practice,title:'百分比的基准量',heading:'百分比相对于谁？',question:'涨了25%，再降25%，会回到原价吗？',context:'一件物品原价80元，上涨25%后是100元；再降低25%，价格变为75元。',formulas:['80 × 1.25 = 100','100 × 0.75 = 75'],takeaway:'两次变化的基准量不同，不能直接抵消。',prompt:'第二次的25%，是相对于哪个数？',options:['80','100','还不确定'],answer:'100',hint:'先写出第一次上涨后的价格。第二次降价是从哪个价格开始的？',reason:'第二次降价以100元为基准，降去25元，因此剩下75元。第一次上涨以80元为基准，上涨20元。两个25%对应的具体数量不同。',explanation:['先找到原价80元，算出上涨量80 × 25% = 20元。','上涨后的价格为100元，第二次降价就以100元为基准。','降价量100 × 25% = 25元，所以最终75元，比原价少5元。'],practice:'原价100元先上涨10%，再下调10%，最终是多少？',practiceOptions:['100元','99元','90元'],practiceAnswer:'99元',practiceReason:'先得到110元，再计算110 × 0.9 = 99元。两次10%的基准量仍不同。',seed:'为什么同样涨跌25%，最后没有回到原价？'},
  {id:'reading',tag:'阅读与思考',lesson:'reading-fact',art:'/assets/competition-v1/pbl/books.png.webp',title:'区分事实与判断',heading:'一句话里，哪些可以核查？',question:'新增了长椅，就能证明“全市最舒适”吗？',context:'这座公园本周新增了12张长椅，因此它是全市最舒适的公园。这是一段自编情境，不是对真实公园的报道。',formulas:[],takeaway:'把可以核查的事实，与需要评价标准的判断分开。',prompt:'“全市最舒适的公园”属于哪一种陈述？',options:['可直接核查的事实','包含评价的判断','还不确定'],answer:'包含评价的判断',hint:'先想想：“最舒适”采用了什么比较标准，又比较了哪些公园？',reason:'“新增12张长椅”可以查阅记录。“全市最舒适”还需要评价标准与同类比较，不能只由长椅增加推出。',explanation:['把句子分成“新增12张长椅”和“全市最舒适”两部分。','第一部分可以查阅新增长椅记录；第二部分需要先说明“舒适”的标准。','补充绿荫、噪声、可用长椅等比较证据，再给出范围合适的结论。'],practice:'“图书馆周日开放到18点”最适合怎样核查？',practiceOptions:['查看开放公告','只看个人喜好','由说话语气判断'],practiceAnswer:'查看开放公告',practiceReason:'开放公告可以支持这个具体时间陈述；个人喜欢和语气不能作为开放时间证据。',seed:'如何区分材料中的事实陈述、评价和缺少依据的推断？'},
  {id:'programming',tag:'编程与智能',lesson:'python-loop',art:'/assets/competition-v1/pbl/laptop.png.webp',title:'看懂一段 Python 循环',heading:'累加，还是覆盖？',question:'循环结束后，total 会变成多少？',context:'下面是自编的代码阅读示例。这里不运行输入代码，只跟随每一行检查变量变化。',code:'total = 0\nfor value in [3, 6, 9]:\n    if value > 4:\n        total = value',formulas:['开始：total = 0','遇到6：total = 6','遇到9：total = 9'],takeaway:'total = value 会覆盖旧值；total += value 才会累加。',prompt:'这段循环最后的 total 是多少？',options:['15','9','还不确定'],answer:'9',hint:'注意更新语句有没有加号。每次符合条件时，它把哪个值存进 total？',reason:'3不符合条件；遇到6时把total改成6，遇到9时再改成9。它没有保留之前的6，因此不是15。',explanation:['初始total为0；3不大于4，所以本轮不更新。','6大于4，执行覆盖赋值，total变为6。','9大于4，再次覆盖赋值，total变为9。'],practice:'如果把最后一行改为 total += value，最终是多少？',practiceOptions:['9','15','18'],practiceAnswer:'15',practiceReason:'只有6和9符合条件，将它们累加到初始值0，结果为15。这里只检查阅读理解，并未执行代码。',seed:'怎样逐行检查 Python 循环中累加与覆盖赋值的区别？'},
]
export const sampleById = id => learningExamples.find(item=>item.id===id)||learningExamples[0]
