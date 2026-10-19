const base = process.env.NUXT_APP_BASE_URL ?? '/'
const site = process.env.NUXT_SITE_URL

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
  robots: { robotsTxt: false },
  llms: { domain: site ? `${site}${base}`.replace(/\/$/, '') : undefined },
  appConfig: {
    header: {
      logo: {
        light: '/logo/wordmark-on-light.svg',
        dark: '/logo/wordmark-on-dark.svg',
        alt: 'shirabe-profiling',
        class: 'h-8',
        favicon: `${base}favicon.ico`
      }
    }
  }
})
