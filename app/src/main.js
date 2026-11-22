import { createApp } from 'vue'
import { setupFocusModality } from './focusModality.js'
import App from './RootApp.vue'
import './style.css'
import './learning.css'
import './feature-pages.css'
import './knowledge-graph.css'
import './knowledge-space.css'
import './citation-page.css'
import './citation-composer.css'
import './feature-workspaces.css'
import './interaction-states.css'
import './input-focus.css'
import './interactive-components.css'
import './entry-site.css'
import './pbl-workspace.css'
import './competition-ui.css'
import './brand-logo.css'
import './video-learning.css'

setupFocusModality()
createApp(App).mount('#app')

import './source-paging.css'
