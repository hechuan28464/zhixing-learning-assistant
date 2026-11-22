<script setup>
import {defineAsyncComponent,onMounted} from 'vue'
import AuthDialog from './components/AuthDialog.vue'
import {refreshAuthentication} from './authState.js'
const StudioApp=defineAsyncComponent(()=>import('./StudioApp.vue'))
const EntryWebsite=defineAsyncComponent(()=>import('./components/entry/EntryWebsite.vue'))
const studio = location.pathname === '/app' || location.pathname.startsWith('/app/')
onMounted(refreshAuthentication)
</script>
<template><StudioApp v-if="studio"/><EntryWebsite v-else/><AuthDialog/></template>
