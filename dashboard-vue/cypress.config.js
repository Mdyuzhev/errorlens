import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    baseUrl: 'http://192.168.1.74:3000',
    viewportWidth: 1600,
    viewportHeight: 900,
    video: false,
    screenshotOnRunFailure: true,

    // Реальные таймауты для async UI
    defaultCommandTimeout: 10000,
    requestTimeout: 30000,
    responseTimeout: 30000,
    pageLoadTimeout: 60000,

    retries: {
      runMode: 1,
      openMode: 0
    },

    // Reporter для сбора результатов в JSON
    reporter: 'cypress-multi-reporters',
    reporterOptions: {
      reporterEnabled: 'mochawesome',
      mochawesomeReporterOptions: {
        reportDir: 'cypress/reports',
        overwrite: false,
        html: false,
        json: true,
      }
    },

    setupNodeEvents(on, config) {
      // nothing
    },
  },
})
