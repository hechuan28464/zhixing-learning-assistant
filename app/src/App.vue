<script setup>
import { computed, ref } from 'vue'
import { artwork, icon } from './assets.js'

const query = ref('')
const preview = ref(null)
const navItems = [
  ['home', '首页'], ['book-open', '我的学习'], ['grid', '课程广场'],
  ['network', '知识图谱'], ['file-text', '阅读与思考'], ['box', '项目实践'],
  ['leaf', '灵感笔记'], ['users', '学习伙伴'],
]
const courses = [
  { id: 'mathematics', tag: '数学思维', title: '从问题到模型：\n用数学看见真实世界', subtitle: '数学思维 · 跨学科探索', next: '函数的多重视角', tint: 'apricot' },
  { id: 'programming', tag: '编程与智能', title: 'Python 与真实问题\n的 7 个小项目', subtitle: '初学者友好 · 项目制学习', next: '数据可视化入门', tint: 'lavender' },
  { id: 'reading', tag: '阅读与思考', title: '在阅读中建立\n更清晰的思考力', subtitle: '通识 · 方法 · 深度阅读', next: '如何提出一个好问题', tint: 'rose' },
]
const filteredCourses = computed(() => courses.filter(c => [c.tag,c.title,c.subtitle].join(' ').toLowerCase().includes(query.value.toLowerCase())))
const recommendations = [
  { id: 'systems', title: '用一次散步\n理解复杂系统', tag: '思维模型 · 跨学科' },
  { id: 'city', title: '城市的数学：\n从路线到可能性', tag: '数学 · 真实世界' },
  { id: 'curiosity', title: '好的提问，\n是另一种创造', tag: '阅读 · 思考力' },
]
const plans = ref([
  { title: '完成一次数学练习', duration: '30分钟', time: '先理解，再动手', done: false },
  { title: '阅读与整理一段材料', duration: '40分钟', time: '带着问题读进去', done: false },
  { title: '尝试一个 Python 小项目', duration: '40分钟', time: '让想法运行起来', done: false },
  { title: '回顾今天的一个收获', duration: '10分钟', time: '留下一点真实的进步', done: false },
])
const openAsset = (id, label) => { preview.value = { src: artwork[id], label } }
const openIcon = (id, label) => { preview.value = { src: `/assets/competition-v1/icons/png/${id}.png`, label, dark: true } }
const today = new Intl.DateTimeFormat('zh-CN', {month:'long', day:'numeric', weekday:'long'}).format(new Date())
</script>

<template>
  <div class="studio-shell">
    <aside class="sidebar" :style="{ backgroundImage: `url(${artwork.sidebar})` }">
      <a class="brand-lockup" href="/" aria-label="知行伴学首页"><img :src="artwork.logo" alt="知行伴学书本Logo"><div><strong>知行伴学</strong><span>让好奇，慢慢成为能力</span></div></a>
      <nav aria-label="主导航"><button v-for="([id,label],index) in navItems" :key="id" :class="['nav-item',{active:index===0}]" @click="openIcon(id,label)"><img :src="icon(id,'white')" alt=""><span>{{ label }}</span></button></nav>
      <div class="sidebar-secondary"><button class="nav-item" @click="openIcon('bell','消息')"><img :src="icon('bell','white')" alt=""><span>消息</span><i></i></button><button class="nav-item" @click="openIcon('settings','设置')"><img :src="icon('settings','white')" alt=""><span>设置</span></button></div>
      <div class="sidebar-quote">在更大的世界里<br>成为更好的自己。<span></span></div>
    </aside>
    <div class="workspace">
      <header class="topbar"><label class="top-search"><img :src="icon('search')" alt=""><input v-model="query" aria-label="搜索课程封面" placeholder="搜索课程、主题或你感兴趣的问题…"><kbd>⌘ K</kbd></label><div class="top-actions"><span><img :src="icon('calendar')" alt="">{{ today }}</span><button class="icon-button" aria-label="查看通知图标" @click="openIcon('bell','消息')"><img :src="icon('bell')" alt=""></button><button class="avatar-button" aria-label="查看学习者头像" @click="openAsset('learner','学习者头像')"><img :src="artwork.learner" alt="虚构学习者头像"></button></div></header>
      <div class="dashboard-grid">
        <main class="main-column">
          <section class="hero" :style="{ backgroundImage: `url(${artwork.hero})` }"><div class="hero-copy"><p>你好，<br>欢迎来到知行伴学。</p><h1>让好奇，慢慢成为能力。</h1><label class="hero-search"><img :src="icon('search')" alt=""><input v-model="query" aria-label="探索课程素材" placeholder="今天想探索什么？从一个问题开始…"><a href="/assets/library/index.html" aria-label="探索全部素材"><img :src="icon('arrow-right','white')" alt=""></a></label><div class="topic-links"><button @click="query='数学'">数学思维</button><button @click="query='Python'">Python 入门</button><button @click="query='阅读'">阅读与写作</button><button @click="query=''">跨学科思考</button></div></div></section>
          <section class="courses-section"><div class="section-heading"><h2>继续学习 <img :src="icon('chevron-right')" alt=""></h2><a href="/assets/library/index.html#courses">查看全部</a></div><p class="section-description">从一个具体的问题出发，保持探索的节奏。</p><div class="course-grid"><button v-for="course in filteredCourses" :key="course.id" class="course-card" @click="openAsset(course.id,course.tag+'课程封面')"><div class="course-art" :style="{backgroundImage:`url(${artwork[course.id]})`}"><span :class="['course-tag',course.tint]">{{ course.tag }}</span><h3>{{ course.title }}</h3><p>{{ course.subtitle }}</p></div><div class="course-footer"><span :class="['progress-dot',course.tint]"></span><div><strong>{{ course.next }}</strong><small>课程封面应用示例</small></div><img :src="icon('chevron-right')" alt=""></div></button></div><p v-if="!filteredCourses.length" class="empty-state">暂时没有匹配的封面，试试“数学”“Python”或“阅读”。</p></section>
          <section class="recommendations"><div class="section-heading"><h2><img :src="icon('leaf')" alt="">为你推荐</h2><a href="/assets/library/index.html#recommendations">查看配图</a></div><div class="recommendation-grid"><button v-for="item in recommendations" :key="item.id" @click="openAsset(item.id,item.title.replace('\n',''))"><img class="recommendation-art" :src="artwork[item.id]" :alt="item.title.replace('\n','')"><div><h3>{{ item.title }}</h3><span>{{ item.tag }}</span></div><img class="chevron" :src="icon('chevron-right')" alt=""></button></div></section>
          <p class="preview-note">首页素材应用预览 · 课程与计划为界面示例，点击图片可查看独立素材。</p>
        </main>
        <aside class="right-column"><section class="plan-panel"><div class="section-heading"><h2>今日计划</h2><span>组件示例</span></div><button v-for="plan in plans" :key="plan.title" class="plan-row" @click="plan.done=!plan.done"><span :class="['plan-check',{done:plan.done}]"><img v-if="plan.done" :src="icon('check','white')" alt="已完成"></span><div><strong>{{ plan.title }}</strong><small>{{ plan.time }}</small></div><span class="duration">{{ plan.duration }}</span></button></section>
          <section class="mentor-panel"><div class="section-heading"><h2>学习伙伴 · AI 导师</h2><button class="text-button" @click="openAsset('mentor','林知导师头像')">查看头像</button></div><div class="mentor-intro"><button @click="openAsset('mentor','林知导师头像')"><img :src="artwork.mentor" alt="林知，虚构AI导师形象"></button><div><h3>林知</h3><p>我在这里，陪你把好奇一点点<br>变成真实的能力。</p></div></div><div class="mentor-prompts"><a href="/assets/library/index.html#avatars">我有一个想法，帮我梳理一下<img :src="icon('arrow-right')" alt=""></a><a href="/assets/library/index.html#courses">这段内容我不太理解<img :src="icon('arrow-right')" alt=""></a><a href="/assets/library/index.html">帮我找到合适的学习材料<img :src="icon('arrow-right')" alt=""></a></div></section>
          <button class="growth-banner" :style="{backgroundImage:`url(${artwork.growth})`}" @click="openAsset('growth','成长寄语背景')"><span>真正的成长，<br>是把好奇变成一次次微小的行动。</span><small>—— 知行伴学</small></button>
        </aside>
      </div>
    </div>
    <div v-if="preview" class="modal-backdrop" @click.self="preview=null" @keydown.esc="preview=null"><section :class="['asset-modal',{dark:preview.dark}]" role="dialog" aria-modal="true" :aria-label="preview.label"><button class="modal-close" aria-label="关闭预览" autofocus @click="preview=null">×</button><img :src="preview.src" :alt="preview.label"><div class="modal-footer"><span>{{ preview.label }}</span><a :href="preview.src" download>下载独立素材</a></div></section></div>
  </div>
</template>
