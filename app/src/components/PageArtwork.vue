<script setup>
import { computed } from 'vue'
import { pageArtwork } from '../pageArtwork.js'
import { splitArtwork,splitAsset } from '../splitArtwork.js'
const props=defineProps({page:String,title:String,description:String,motif:Boolean})
const art=computed(()=>pageArtwork[props.page])
</script>
<template>
  <div v-if="motif && art" :class="['lesson-visual-band','theme-'+page]" aria-hidden="true"><img class="motif-scene" :src="art.scene" alt=""><img class="motif-element" :src="art.element" alt=""></div>
  <header v-else-if="!motif" :class="['page-heading','feature-heading','theme-'+page,{illustrated:!!art,compact:['settings','messages','buddy'].includes(page)}]">
    <img v-if="art" class="feature-scene" :src="art.scene" alt="" aria-hidden="true">
    <div class="feature-heading-copy"><h1>{{ title }}</h1><p>{{ description }}</p><div v-if="$slots.default" class="feature-heading-actions"><slot/></div></div>
    <div v-if="splitArtwork[page]" class="feature-composition" aria-hidden="true"><img v-for="(id,index) in splitArtwork[page]" :key="id" :class="'feature-piece piece-'+index" :src="splitAsset(id)" alt=""></div>
    <img v-else-if="art" class="feature-element" :src="art.element" alt="" aria-hidden="true">
  </header>
</template>
