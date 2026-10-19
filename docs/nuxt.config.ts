export default defineNuxtConfig({
  extends: ['docus'],
  content: {
    build: { markdown: { highlight: { langs: ['python'] } } }
  },
  ui: {
    theme: { colors: ['primary', 'info', 'success', 'warning', 'error'] }
  },
  icon: { mode: 'svg' },
  image: { provider: 'none' },
  appConfig: {
    header: {
      logo: {
        light: '/logo/wordmark-on-light.svg',
        dark: '/logo/wordmark-on-dark.svg',
        alt: 'shirabe-profiling',
        class: 'h-8'
      }
    }
  }
})
