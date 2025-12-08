describe('Settings Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('view_settings', () => {
    cy.visit('/settings')
    cy.contains(/settings|настройки/i).should('be.visible')
  })

  it('theme_toggle_exists', () => {
    cy.visit('/settings')
    cy.get('[data-testid="theme-toggle"], .theme-toggle, button').contains(/theme|тема|dark|light/i).should('exist')
  })

  it('api_key_section', () => {
    cy.visit('/settings')
    cy.contains(/api key|ключ/i).should('exist')
  })

  it('profile_section', () => {
    cy.visit('/settings')
    cy.contains(/profile|профиль/i).should('exist')
  })
})
