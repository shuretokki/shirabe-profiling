export default defineNuxtConfig({
  extends: ['docus'],
  content: {
    build: { markdown: { highlight: { langs: ['python'] } } }
  },
  ui: {
    theme: { colors: ['primary', 'info', 'success', 'warning', 'error'] }
  },
  icon: { mode: 'svg' }
})
