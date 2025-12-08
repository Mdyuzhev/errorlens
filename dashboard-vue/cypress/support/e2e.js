// Cypress E2E support file

import './commands'
import '@testing-library/cypress/add-commands'

beforeEach(() => {
  cy.clearLocalStorage()
})

Cypress.on('uncaught:exception', (err, runnable) => {
  // Prevent Cypress from failing on unhandled promise rejections
  return false
})
