import './commands'
import '@testing-library/cypress/add-commands'
import '@4tw/cypress-drag-drop'

// НЕ очищать localStorage здесь — авторизация живёт на весь describe-блок

Cypress.on('uncaught:exception', (err, runnable) => {
  // Не падать на unhandled promise rejections приложения
  return false
})
