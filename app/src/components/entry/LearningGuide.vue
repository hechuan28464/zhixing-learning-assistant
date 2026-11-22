<script setup>
import {computed,onUnmounted,ref,watch} from 'vue'
import {TabsRoot,TabsList,TabsTrigger,TabsContent} from 'reka-ui'
import {artwork,icon} from '../../assets.js'
import {entryArt,walkthroughSteps,learningExamples} from '../../entryContent.js'
const emit=defineEmits(['new-goal'])
const initial=new URLSearchParams(location.search).get('step')
const step=ref(walkthroughSteps.some(s=>s.id===initial)?initial:'1'),question=ref(''),objective=ref(''),material=ref(null),fileError=ref(''),readingFile=ref(false),fileInput=ref(null),error=ref(''),practice=ref('')
const selected=computed(()=>walkthroughSteps.find(s=>s.id===step.value))
const math=learningExamples[0]
const topics=['数学思维','阅读与写作','编程入门','自己的问题']
const seeds={'数学思维':math.seed,'阅读与写作':learningExamples[1].seed,'编程入门':learningExamples[2].seed,'自己的问题':''}
let fileVersion=0
watch(step,value=>history.replaceState(null,'','/how-it-works?step='+value))
onUnmounted(()=>++fileVersion)
async function chooseFile(event){
 const version=++fileVersion,file=event.target.files?.[0];material.value=null;fileError.value='';readingFile.value=false;event.target.value=''
 if(!file)return
 if(!/\.(md|txt)$/i.test(file.name)){fileError.value='请选择 TXT 或 Markdown 资料。';return}
 if(file.size>1024*1024){fileError.value='请选择 1MB 以内的资料。';return}
 readingFile.value=true
 try{const text=await file.text();if(version!==fileVersion)return;if(!text.trim())throw new Error('这份资料没有可读取的文字。');if(text.length>120000)throw new Error('资料超过12万字元，请分段整理。');material.value={title:file.name.replace(/\.(md|txt)$/i,'').slice(0,150)||'学习资料',text,source:file.name.slice(0,200)}}catch(e){if(version===fileVersion)fileError.value=e.message}finally{if(version===fileVersion)readingFile.value=false}
}
function setFileInput(element){fileInput.value=element}
function start(optional=false){error.value='';if(!question.value.trim()&&!optional){error.value='先写下一个想弄懂的问题。';return}const seed=question.value.trim()+(objective.value.trim()?'\n希望学到：'+objective.value.trim():'');emit('new-goal',seed,material.value)}
</script>
<template>
<main id="entry-content" class="entry-guide entry-container" tabindex="-1"><header class="entry-page-title"><a class="entry-breadcrumb" href="/">首页</a><span class="entry-breadcrumb"> / 学习方式</span><h1>从一个问题开始，走到自己的理解。</h1><p>不必先安排好所有步骤。先找到想弄懂的事，<br>再带着资料、问题和练习，逐步往前。</p><img class="entry-page-art" :src="entryArt.arch" alt=""></header>
  <TabsRoot v-model="step" class="entry-guide-tabs"><TabsList class="entry-guide-steps" aria-label="学习流程"><TabsTrigger v-for="item in walkthroughSteps" :key="item.id" :value="item.id"><img :src="item.art" alt=""><span><b>{{ item.id.padStart(2,'0') }}</b>{{ item.title }}</span></TabsTrigger></TabsList>
    <TabsContent v-for="item in walkthroughSteps" :key="item.id" :value="item.id" class="entry-guide-panel"><div class="entry-guide-copy"><h2><span>{{ item.id.padStart(2,'0') }}</span>{{ item.heading }}</h2><p>{{ item.text }}</p><template v-if="item.id==='1'"><div class="entry-topic-pills"><button v-for="topic in topics" :key="topic" @click="question=seeds[topic]">{{ topic }}</button></div><ul class="entry-checklist"><li><img :src="icon('file-text')" alt="">写清想解决的问题</li><li><img :src="icon('book-open')" alt="">带上已有的资料</li><li><img :src="icon('check')" alt="">给自己留一个可检查的小目标</li></ul><blockquote>{{ math.seed }}</blockquote></template><template v-else-if="item.id==='2'"><blockquote>“这句话的依据是什么？”<br>“能不能换一个生活中的例子？”</blockquote><p>先读原文，再分清哪些内容来自资料，哪些是自己的解释。引用会随讨论保留，方便回看。</p><a class="entry-text-link" href="/app?view=reading&import=1">到阅读空间导入资料<img :src="icon('arrow-right')" alt=""></a></template><template v-else-if="item.id==='3'"><blockquote>先留下自己的解释，再看讲解。</blockquote><p>这里的示例练习只用于体验。正式学习会保留作答与所获帮助，避免把看过答案当成独立掌握。</p><a class="entry-text-link" href="/examples?course=mathematics">体验完整示例</a></template><template v-else><blockquote>真正的成长，是把好奇变成一次次微小的行动。</blockquote><p>学习记录来自实际保存的资料、笔记、讨论与作答。没有记录时，先完成一个小动作。</p><a class="entry-text-link" href="/app?view=graph">打开自己的知识空间<img :src="icon('arrow-right')" alt=""></a></template></div>
      <form v-if="item.id==='1'" class="entry-goal-form" @submit.prevent="start"><header><h2>开始一个学习目标</h2><span class="entry-demo-label">填写后再确认创建</span></header><label>想弄懂的问题<textarea v-model="question" required rows="3" maxlength="1000" placeholder="例如：为什么同样涨跌25%，最后没有回到原价？"></textarea></label><label>希望学到什么<input v-model="objective" maxlength="500" placeholder="例如：说清百分比的基准量，并用一个例子解释"></label><input :ref="setFileInput" class="entry-visually-hidden" tabindex="-1" type="file" accept=".txt,.md,text/plain,text/markdown" aria-label="选择学习资料" @change="chooseFile"><button class="entry-button secondary" type="button" :disabled="readingFile" @click="fileInput?.click()"><img :src="icon('paperclip')" alt="">{{ readingFile?'正在读取资料…':'添加自己的资料（可选）' }}</button><div v-if="material" class="entry-staged-file"><img :src="icon('file-text')" alt=""><span>{{ material.title }}</span><button type="button" aria-label="移除待加入资料" @click="material=null;++fileVersion">×</button></div><p v-if="fileError" role="alert" class="entry-field-error">{{ fileError }}</p><p v-if="error" role="alert" class="entry-field-error">{{ error }}</p><p class="entry-field-hint">先预览填写内容，确认创建后才保存；资料将关联到新目标。</p><button class="entry-button" :disabled="readingFile||!question.trim()">创建学习目标</button></form>
      <section v-else-if="item.id==='2'" class="entry-guide-demo"><div class="entry-guide-demo-title"><img :src="artwork.mentor" alt="林知"><div><h2>带着一个具体问题讨论</h2><span class="entry-demo-label">对话示例</span></div></div><div class="entry-demo-source"><strong>引用：{{ math.question }}</strong><p>{{ math.context }}</p></div><p><strong>林知想问你：</strong>{{ math.prompt }}</p><p>{{ math.hint }}</p><div class="entry-action-row"><a class="entry-button" href="/examples?course=mathematics">先体验一个示例</a><a class="entry-button secondary" href="/app?view=buddy">打开学习伙伴</a></div></section>
      <section v-else-if="item.id==='3'" class="entry-guide-demo"><span class="entry-demo-label">示例练习 · 不保存为作答</span><h2>{{ math.practice }}</h2><fieldset class="entry-practice-options"><legend>选择你的答案</legend><label v-for="option in math.practiceOptions" :key="option" :class="{selected:practice===option}"><input v-model="practice" type="radio" name="guide-practice" :value="option">{{ option }}</label></fieldset><p v-if="practice" class="entry-demo-answer" role="status">{{ practice===math.practiceAnswer?math.practiceReason:'先算出第一次上涨后的价格，再以这个价格计算下调量。' }}</p><a class="entry-button secondary" href="/examples?course=mathematics">查看讲解与另一种提问</a></section>
      <section v-else class="entry-guide-demo entry-review-demo"><img :src="entryArt.reflection" alt=""><h2>留下真实发生的学习过程</h2><a class="entry-review-link" href="/app?view=notes"><span>灵感笔记</span>回看自己的解释<img :src="icon('chevron-right')" alt=""></a><a class="entry-review-link" href="/app?view=graph"><span>知识空间</span>检索资料、对话与记忆<img :src="icon('chevron-right')" alt=""></a><a class="entry-review-link" href="/app?view=messages"><span>学习动态</span>查看实际保存的学习记录<img :src="icon('chevron-right')" alt=""></a></section>
    </TabsContent>
  </TabsRoot>
  <section class="entry-guide-summary"><a href="/how-it-works?step=2"><img :src="entryArt.discussion" alt=""><div><h3>讨论时，先找依据</h3><p>围绕资料澄清概念，卡住时请林知换一种讲法。</p></div></a><a href="/how-it-works?step=3"><img :src="entryArt.question" alt=""><div><h3>练习后，留下表现</h3><p>通过作答和自己的解释，发现需要再看的地方。</p></div></a><a href="/how-it-works?step=4"><img :src="entryArt.reflection" alt=""><div><h3>回看时，自己做选择</h3><p>检索笔记与讨论；学习记忆由你确认后使用。</p></div></a></section>
  <div class="entry-guide-bottom"><button class="entry-button" @click="start(true)">带着自己的问题开始<img :src="icon('arrow-right','white')" alt=""></button><a class="entry-button secondary" href="/examples">先体验一个示例</a></div>
</main>
</template>
