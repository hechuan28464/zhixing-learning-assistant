import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue(), {name:'private-design-review',configureServer(server){server.middlewares.use((request,response,next)=>{if(/^\/(previews|design)(\/|$)/.test(request.url||'')){response.statusCode=404;response.setHeader('Content-Type','text/plain; charset=utf-8');response.end('页面不存在');return}next()})}}],
  server: {
    fs: { deny: ['**/.git/**','**/*.crt','.env','.env.*','**/.env*','**/backend/**','**/vendor/**','**/integrations/**','**/tests/**','**/.qa/**','**/data/**','**/deploy/**','**/design/**','**/test-reports/**','**/exports/**','**/*.pem','**/*.key'] },
    watch: { usePolling: process.platform === 'win32', interval: 300, ignored: ['**/.venv/**','**/.qa/**','**/test-reports/**','**/exports/**','**/dist/**','**/design/**'] },
    proxy: { '/api': process.env.STUDY_API_TARGET || 'http://127.0.0.1:8765' },
  },
  build: { sourcemap: false },
})
