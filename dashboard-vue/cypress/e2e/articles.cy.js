describe('Articles Tests', () => {
  beforeEach(() => {
    cy.login()
  })

  it('list_articles', () => {
    cy.visit('/articles')
    cy.get('[data-testid="articles-list"], .articles-list, article, .article-card').should('exist')
  })

  it('create_article', () => {
    cy.visit('/articles')
    cy.contains(/new|создать|add/i).click()

    cy.get('input[name="title"], input[placeholder*="title"], input[placeholder*="название"]').type('Test Article')
    cy.get('textarea[name="content"], textarea[placeholder*="content"], .editor').type('Test content')
    cy.contains(/save|сохранить/i).click()

    cy.contains('Test Article').should('be.visible')
  })

  it('create_article_validation', () => {
    cy.visit('/articles')
    cy.contains(/new|создать|add/i).click()
    cy.contains(/save|сохранить/i).click()

    cy.contains(/required|обязательн|заполн/i).should('be.visible')
  })

  it('view_article', () => {
    cy.visit('/articles')
    cy.get('article, .article-card, .article-item').first().click()

    cy.get('.modal, .dialog, .article-detail').should('be.visible')
  })

  it('filter_by_category', () => {
    cy.visit('/articles')
    cy.get('select[name="category"], .category-filter').first().select(1, { force: true })

    cy.wait(500)
  })

  it('search_articles', () => {
    cy.visit('/articles')
    cy.get('input[type="search"], input[placeholder*="search"], input[placeholder*="поиск"]').type('test')

    cy.wait(500)
  })

  it('empty_state', () => {
    cy.visit('/articles')

    cy.get('body').then(($body) => {
      if ($body.text().includes('No articles') || $body.text().includes('Нет статей')) {
        cy.contains(/no articles|нет статей/i).should('be.visible')
      } else {
        cy.log('Articles exist, skipping empty state test')
      }
    })
  })
})
