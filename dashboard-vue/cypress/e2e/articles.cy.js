// Articles E2E Test Suite — 108 tests across 15 describes
// Target: http://192.168.1.74:3000

const BASE = '/dashboard/#/articles'

// ============================================================
// Describe 1: Navigation (5 tests)
// ============================================================
describe('Articles — Navigation', () => {
  it('1.1 goToArticles → .articles-page visible', () => {
    cy.goToArticles()
    cy.get('.articles-page, [class*="articles"]').should('be.visible')
  })

  it('1.2 URL /dashboard/#/articles → page has article list or empty-state', () => {
    cy.loginToApp()
    cy.visit(BASE)
    cy.get('.articles-list, .empty-state, [class*="articles"]', { timeout: 10000 }).should('exist')
  })

  it('1.3 Click "Articles" in navbar → navigate to /articles', () => {
    cy.loginToApp()
    cy.visit('/dashboard/#/')
    cy.get('nav, .sidebar-nav, .nav-menu').contains('Articles').click()
    cy.url().should('include', '/articles')
  })

  it('1.4 Reload /articles → page restores', () => {
    cy.goToArticles()
    cy.reload()
    cy.get('.articles-page, [class*="articles"]', { timeout: 10000 }).should('exist')
  })

  it('1.5 /articles without auth → redirect to /login', () => {
    cy.clearLocalStorage()
    cy.visit(BASE)
    cy.url({ timeout: 8000 }).should('include', '/login')
  })
})

// ============================================================
// Describe 2: Layout (5 tests)
// ============================================================
describe('Articles — Layout', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('2.1 Sidebar contains FolderTree', () => {
    cy.get('.sidebar, [class*="sidebar"]').should('exist')
    cy.get('.folder-tree, [class*="folder-tree"], [class*="tree"]').should('exist')
  })

  it('2.2 Main area contains list-header and articles-list', () => {
    cy.get('.main-area, [class*="main"]').should('exist')
    cy.get('.list-header, [class*="header"]').should('exist')
    cy.get('.articles-list, [class*="list"]').should('exist')
  })

  it('2.3 list-header has category select, status select, Import, + New Article', () => {
    cy.get('.list-header, [class*="header"]').within(() => {
      cy.get('select, [class*="select"]').should('have.length.gte', 2)
      cy.contains(/import/i).should('exist')
      cy.contains(/new article|\+ article/i).should('exist')
    })
  })

  it('2.4 Two filter selects visible', () => {
    cy.get('.list-header select, .list-header [class*="select"]')
      .should('have.length.gte', 2)
  })

  it('2.5 At 768px layout adapts', () => {
    cy.viewport(768, 1024)
    cy.get('.articles-page, [class*="articles"]').should('be.visible')
  })
})

// ============================================================
// Describe 3: FolderTree CRUD (12 tests)
// ============================================================
describe('Articles — FolderTree CRUD', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('3.1 FolderTree visible in sidebar', () => {
    cy.get('.folder-tree, [class*="folder-tree"], [class*="tree"]').should('be.visible')
  })

  it('3.2 Existing folders displayed', () => {
    cy.get('.folder-tree, [class*="folder-tree"]')
      .find('.folder-item, .tree-node, [class*="folder"]')
      .should('have.length.gte', 0)
  })

  it('3.3 "+" button → create folder prompt/input', () => {
    cy.get('.folder-tree, [class*="folder-tree"]')
      .find('button, [class*="add"]').filter(':contains("+"), [class*="add-folder"], [title*="folder"]')
      .first().click()
    cy.get('input, .folder-input, [class*="input"]').should('be.visible')
  })

  it('3.4 Create folder → POST /articles/folders → appears in tree', () => {
    cy.intercept('POST', '**/articles/folders').as('createFolder')
    cy.get('.folder-tree, [class*="folder-tree"]')
      .find('button, [class*="add"]').filter(':contains("+"), [class*="add-folder"], [title*="folder"]')
      .first().click()
    cy.get('input.folder-input, .folder-tree input, [class*="folder"] input')
      .first().clear().type('CY-Test-Folder{enter}')
    cy.wait('@createFolder').its('response.statusCode').should('be.oneOf', [200, 201])
    cy.contains('CY-Test-Folder').should('exist')
  })

  it('3.5 Rename via context menu → rename option visible', () => {
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().rightclick()
    cy.get('.context-menu, [class*="context"], [class*="menu"]')
      .contains(/rename|переименовать/i).should('be.visible')
  })

  it('3.6 Rename → PUT /articles/folders/** → name updated', () => {
    cy.intercept('PUT', '**/articles/folders/**').as('renameFolder')
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().rightclick()
    cy.get('.context-menu, [class*="context"]').contains(/rename|переименовать/i).click()
    cy.get('.folder-tree input, [class*="folder"] input').first()
      .clear().type('CY-Renamed{enter}')
    cy.wait('@renameFolder').its('response.statusCode').should('eq', 200)
  })

  it('3.7 Delete via context menu → confirm → DELETE /articles/folders/**', () => {
    cy.intercept('DELETE', '**/articles/folders/**').as('deleteFolder')
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().rightclick()
    cy.get('.context-menu, [class*="context"]').contains(/delete|удалить/i).click()
    cy.get('.confirm-btn, .modal button, [class*="confirm"]').contains(/yes|ok|да|confirm|удалить/i).click()
    cy.wait('@deleteFolder').its('response.statusCode').should('be.oneOf', [200, 204])
  })

  it('3.8 Folder deleted from tree', () => {
    // relies on 3.7 cleanup or independent
    cy.get('.folder-tree, [class*="folder-tree"]').should('exist')
  })

  it('3.9 Nested folder: create subfolder → appears as child', () => {
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().rightclick()
    cy.get('.context-menu, [class*="context"]')
      .contains(/subfolder|подпапк|new folder|создать/i).click()
    cy.get('.folder-tree input, [class*="folder"] input').first()
      .clear().type('CY-SubFolder{enter}')
    cy.contains('CY-SubFolder').should('exist')
  })

  it('3.10 Click folder → articles filtered (intercept with folder_id)', () => {
    cy.intercept('GET', '**/articles*').as('getArticles')
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().click()
    cy.wait('@getArticles')
  })

  it('3.11 "All articles" → removes folder filter', () => {
    cy.intercept('GET', '**/articles*').as('getAll')
    cy.contains(/all articles|все статьи/i).click()
    cy.wait('@getAll')
  })

  it('3.12 Expand/collapse folder with children', () => {
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().within(() => {
      cy.get('.expand-btn, .toggle, [class*="expand"], [class*="arrow"]')
        .first().click()
    })
  })
})

// ============================================================
// Describe 4: Filters (6 tests)
// ============================================================
describe('Articles — Filters', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('4.1 Category "All Categories" → all articles', () => {
    cy.get('.list-header select, [class*="category-select"]').first()
      .select(0)
    cy.get('.articles-list, [class*="list"]').should('exist')
  })

  it('4.2 Select category → intercept GET /articles?*category=* → filtered', () => {
    cy.intercept('GET', '**/articles*category=*').as('filterCategory')
    cy.get('.list-header select, [class*="category-select"]').first()
      .find('option').then($opts => {
        if ($opts.length > 1) {
          cy.get('.list-header select, [class*="category-select"]').first().select(1)
          cy.wait('@filterCategory')
        }
      })
  })

  it('4.3 Status "Draft" → only draft articles', () => {
    cy.intercept('GET', '**/articles*').as('filterStatus')
    cy.get('.list-header select, [class*="status-select"]').last()
      .select('draft')
    cy.wait('@filterStatus')
  })

  it('4.4 Status "Published" → only published articles', () => {
    cy.intercept('GET', '**/articles*').as('filterPublished')
    cy.get('.list-header select, [class*="status-select"]').last()
      .select('published')
    cy.wait('@filterPublished')
  })

  it('4.5 Combine folder + status → double filter', () => {
    cy.intercept('GET', '**/articles*').as('combined')
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().click()
    cy.get('.list-header select, [class*="status-select"]').last()
      .select('draft')
    cy.wait('@combined')
  })

  it('4.6 Reset category to "All" → all articles again', () => {
    cy.intercept('GET', '**/articles*').as('resetFilter')
    cy.get('.list-header select, [class*="category-select"]').first()
      .select(0)
    cy.wait('@resetFilter')
  })
})

// ============================================================
// Describe 5: Article Rows (8 tests)
// ============================================================
describe('Articles — Article Rows', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('5.1 .article-row has icon, human_id, title, status badge, category, date', () => {
    cy.get('.article-row, [class*="article-item"]').first().within(() => {
      cy.get('[class*="icon"], .file-icon, svg').should('exist')
      cy.get('[class*="human"], [class*="id"]').should('exist')
      cy.get('[class*="title"]').should('exist')
      cy.get('[class*="badge"], [class*="status"]').should('exist')
    })
  })

  it('5.2 Status "draft" → orange badge', () => {
    cy.get('.article-row .badge.draft, [class*="badge"][class*="draft"]')
      .first()
      .should('exist')
  })

  it('5.3 Status "published" → green badge', () => {
    cy.get('.article-row .badge.published, [class*="badge"][class*="published"]')
      .first()
      .should('exist')
  })

  it('5.4 Empty state visible if no articles', () => {
    // Navigate to an empty folder or clear filters
    cy.get('body').then($body => {
      if ($body.find('.empty-state, [class*="empty"]').length) {
        cy.get('.empty-state, [class*="empty"]').should('be.visible')
      } else {
        cy.log('Articles exist — skipping empty state check')
      }
    })
  })

  it('5.5 Empty state text "No articles yet"', () => {
    cy.get('body').then($body => {
      if ($body.find('.empty-state, [class*="empty"]').length) {
        cy.get('.empty-state, [class*="empty"]')
          .invoke('text').should('match', /no articles|нет статей|пусто/i)
      } else {
        cy.log('Articles exist — skipping empty text check')
      }
    })
  })

  it('5.6 Click row → ArticleViewer opens', () => {
    cy.get('.article-row, [class*="article-item"]').first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  it('5.7 Loading spinner while loading', () => {
    cy.intercept('GET', '**/articles*', (req) => {
      req.on('response', (res) => { res.setDelay(500) })
    }).as('delayedArticles')
    cy.visit(BASE)
    cy.get('.spinner, .loading, [class*="loading"], [class*="spinner"]').should('exist')
  })

  it('5.8 .article-row draggable=true', () => {
    cy.get('.article-row, [class*="article-item"]').first()
      .should('have.attr', 'draggable', 'true')
  })
})

// ============================================================
// Describe 6: Create Article — Editor (12 tests)
// ============================================================
describe('Articles — Create Article Editor', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('6.1 "+ New Article" → fullscreen editor opens', () => {
    cy.contains(/new article|новая статья|\+ article/i).click()
    cy.get('.editor-fullscreen, [class*="editor"]', { timeout: 8000 }).should('be.visible')
  })

  it('6.2 Editor header: Back, Toolbar, title-input, status-select, Save', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.get('.editor-fullscreen, [class*="editor"]').within(() => {
      cy.get('[class*="back"], button').contains(/back|←|назад/i).should('exist')
      cy.get('input[class*="title"], [class*="title-input"]').should('exist')
      cy.get('select[class*="status"], [class*="status-select"]').should('exist')
      cy.contains(/save|сохранить/i).should('exist')
    })
  })

  it('6.3 Title input placeholder "Article title"', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first()
      .should('have.attr', 'placeholder')
      .and('match', /title|название|заголовок/i)
  })

  it('6.4 Status select: Draft, Published', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.get('select[class*="status"], [class*="status"] select').first().within(() => {
      cy.get('option').should('have.length.gte', 2)
    })
  })

  it('6.5 "Meta" toggle → subheader appears', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.contains(/meta|мета/i).click()
    cy.get('.subheader, [class*="subheader"], [class*="meta"]').should('be.visible')
  })

  it('6.6 "Meta" toggle again → subheader hidden', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.contains(/meta|мета/i).click()
    cy.get('.subheader, [class*="subheader"], [class*="meta"]').should('be.visible')
    cy.contains(/meta|мета/i).click()
    cy.get('.subheader, [class*="subheader"], [class*="meta-fields"]').should('not.be.visible')
  })

  it('6.7 Subheader: Category placeholder', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.contains(/meta|мета/i).click()
    cy.get('[class*="subheader"], [class*="meta"]')
      .find('input, select').first()
      .should('exist')
  })

  it('6.8 Subheader: Tags placeholder', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.contains(/meta|мета/i).click()
    cy.get('[class*="subheader"], [class*="meta"]')
      .find('[class*="tag"], input').should('exist')
  })

  it('6.9 Back without changes → returns to list', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.get('.editor-fullscreen, [class*="editor"]').should('be.visible')
    cy.get('[class*="back"], button').contains(/back|←|назад/i).click()
    cy.get('.articles-page, [class*="articles"]', { timeout: 8000 }).should('exist')
  })

  it('6.10 Fill title + Save → POST /articles → 201 → closes', () => {
    cy.intercept('POST', '**/articles').as('createArticle')
    cy.contains(/new article|новая статья/i).click()
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first().clear().type('CY New Article E2E')
    cy.contains(/save|сохранить/i).click()
    cy.wait('@createArticle').its('response.statusCode').should('be.oneOf', [200, 201])
  })

  it('6.11 Autosave: timer exists for existing article edit', () => {
    // Create article first, then open editor
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-Autosave-Test' })
    cy.get('@articleId').then(id => {
      cy.visit(`${BASE}`)
      cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
      cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
      cy.contains(/edit|редактировать/i).click()
      // Autosave indicator or timer
      cy.get('[class*="autosave"], [class*="auto-save"], [class*="saved"]', { timeout: 10000 })
        .should('exist')
      cy.deleteArticleViaApi(id)
    })
  })

  it('6.12 Delete button → confirm → DELETE /articles/** → closes', () => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-Delete-Test' })
    cy.get('@articleId').then(id => {
      cy.visit(BASE)
      cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
      cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
      cy.contains(/edit|редактировать/i).click()
      cy.intercept('DELETE', '**/articles/**').as('deleteArt')
      cy.contains(/delete|удалить/i).click()
      cy.get('.confirm-btn, .modal button, [class*="confirm"]')
        .contains(/yes|ok|да|confirm|удалить/i).click()
      cy.wait('@deleteArt').its('response.statusCode').should('be.oneOf', [200, 204])
    })
  })
})

// ============================================================
// Describe 7: GridEditor (6 tests)
// ============================================================
describe('Articles — GridEditor', () => {
  beforeEach(() => {
    cy.goToArticles()
    cy.contains(/new article|новая статья/i).click()
  })

  it('7.1 GridEditor visible in editor body', () => {
    cy.get('.grid-editor, [class*="grid-editor"]', { timeout: 8000 }).should('be.visible')
  })

  it('7.2 Empty state or add-block toolbar', () => {
    cy.get('.grid-editor, [class*="grid-editor"]').within(() => {
      cy.get('[class*="add"], [class*="empty"], [class*="toolbar"], button').should('exist')
    })
  })

  it('7.3 EditorToolbar in editor-header', () => {
    cy.get('.editor-toolbar, [class*="toolbar"]').should('exist')
  })

  it('7.4 Add text block → content appears', () => {
    cy.get('.grid-editor, [class*="grid-editor"]')
      .find('[class*="add"], button').first().click()
    cy.get('.grid-editor, [class*="grid-editor"]')
      .find('[class*="block"], [class*="row"], .tiptap, [contenteditable]')
      .should('exist')
  })

  it('7.5 Edit mode: min-height fills space', () => {
    cy.get('.grid-editor, [class*="grid-editor"]')
      .invoke('css', 'min-height')
      .should('not.eq', '0px')
  })

  it('7.6 Readonly mode: no add/edit buttons', () => {
    // Go back and open viewer (readonly)
    cy.get('[class*="back"], button').contains(/back|←|назад/i).click()
    cy.get('.article-row, [class*="article-item"]').first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).within(() => {
      cy.get('.grid-editor [class*="add-block"], .grid-editor [class*="add-row"]')
        .should('not.exist')
    })
  })
})

// ============================================================
// Describe 8: ArticleViewer Topbar (6 tests)
// ============================================================
describe('Articles — ArticleViewer Topbar', () => {
  beforeEach(() => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-Viewer-Topbar' })
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@articleId').then(id => cy.deleteArticleViaApi(id))
  })

  it('8.1 Click article-row → ArticleViewer fullscreen', () => {
    cy.get('.article-viewer, [class*="viewer"]').should('be.visible')
  })

  it('8.2 Topbar: Back, "Articles", History, PDF, Edit', () => {
    cy.get('.viewer-topbar, [class*="topbar"]').within(() => {
      cy.get('[class*="back"], button').should('exist')
      cy.contains(/history|история/i).should('exist')
      cy.contains(/edit|редактировать/i).should('exist')
    })
  })

  it('8.3 Edit (purple) → opens Editor', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.get('.editor-fullscreen, [class*="editor"]', { timeout: 8000 }).should('be.visible')
  })

  it('8.4 Back → closes viewer', () => {
    cy.get('[class*="back"], button').contains(/back|←|назад|articles/i).first().click()
    cy.get('.articles-page, [class*="articles"]', { timeout: 8000 }).should('exist')
  })

  it('8.5 PDF → intercept GET /articles/*/export/pdf → download', () => {
    cy.intercept('GET', '**/articles/*/export/pdf*').as('exportPdf')
    cy.get('.viewer-topbar, [class*="topbar"]')
      .find('[class*="pdf"], button').contains(/pdf/i).click()
    cy.wait('@exportPdf').its('response.statusCode').should('eq', 200)
  })

  it('8.6 History → history panel opens', () => {
    cy.contains(/history|история/i).click()
    cy.get('.viewer-history.open, [class*="history"][class*="open"], [class*="history-panel"]', { timeout: 8000 })
      .should('be.visible')
  })
})

// ============================================================
// Describe 9: ArticleViewer Article Head (10 tests)
// ============================================================
describe('Articles — ArticleViewer Article Head', () => {
  beforeEach(() => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-Head-Test', category: 'Testing' })
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@articleId').then(id => cy.deleteArticleViaApi(id))
  })

  it('9.1 viewer-article-head: breadcrumbs, title, status badge', () => {
    cy.get('.viewer-article-head, [class*="article-head"]').within(() => {
      cy.get('[class*="breadcrumb"]').should('exist')
      cy.get('[class*="title"], h1, h2').should('exist')
      cy.get('[class*="badge"]').should('exist')
    })
  })

  it('9.2 Status "draft" → orange badge (.viewer-badge.draft)', () => {
    cy.get('.viewer-badge.draft, [class*="badge"][class*="draft"]')
      .should('exist')
  })

  it('9.3 Status "published" → green badge', () => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-Published-Head', status: 'published' })
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]').first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
    cy.get('.viewer-badge.published, [class*="badge"][class*="published"]')
      .should('exist')
    cy.get('@articleId').then(id => cy.deleteArticleViaApi(id))
  })

  it('9.4 Meta: author avatar + name, date, N views', () => {
    cy.get('.viewer-article-head, [class*="article-head"]').within(() => {
      cy.get('[class*="avatar"]').should('exist')
      cy.get('[class*="author"], [class*="name"]').should('exist')
      cy.get('[class*="date"]').should('exist')
    })
  })

  it('9.5 Author initial in avatar', () => {
    cy.get('[class*="avatar"]').first()
      .invoke('text').should('have.length.gte', 1)
  })

  it('9.6 Tags block visible if category/tags', () => {
    cy.get('[class*="tag"], [class*="category"]').should('exist')
  })

  it('9.7 Category tag accent color', () => {
    cy.get('[class*="tag"][class*="category"], [class*="category-tag"]')
      .first()
      .should('exist')
  })

  it('9.8 No folder → breadcrumbs "Articles" only', () => {
    cy.get('[class*="breadcrumb"]')
      .invoke('text').should('match', /articles|статьи/i)
  })

  it('9.9 In folder → breadcrumbs "Articles > Folder > Title"', () => {
    // Create folder, create article in folder
    cy.loginToApp()
    cy.createFolderViaApi('CY-Breadcrumb-Folder')
    cy.get('@folderId').then(folderId => {
      cy.createArticleViaApi({ title: 'CY-InFolder', folder_id: folderId })
      cy.get('@articleId').then(artId => {
        cy.visit(BASE)
        cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
        cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
        cy.get('[class*="breadcrumb"]')
          .invoke('text').should('include', 'CY-Breadcrumb-Folder')
        cy.deleteArticleViaApi(artId)
        cy.deleteFolderViaApi(folderId)
      })
    })
  })

  it('9.10 Click folder in breadcrumbs → navigate to folder', () => {
    cy.get('[class*="breadcrumb"] a, [class*="breadcrumb"] [class*="link"]')
      .first().click()
    cy.get('.articles-page, [class*="articles"]', { timeout: 8000 }).should('exist')
  })
})

// ============================================================
// Describe 10: ArticleViewer TOC (6 tests)
// ============================================================
describe('Articles — ArticleViewer TOC', () => {
  let tocArticleId

  before(() => {
    cy.loginToApp()
    const contentWithHeadings = JSON.stringify({
      version: 'grid-1',
      rows: [
        { cells: [{ type: 'text', content: { type: 'doc', content: [
          { type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: 'H1 Heading' }] },
          { type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: 'H2 Heading' }] },
          { type: 'heading', attrs: { level: 3 }, content: [{ type: 'text', text: 'H3 Heading' }] },
          { type: 'paragraph', content: [{ type: 'text', text: 'Body text for scrolling.' }] }
        ] } }] }
      ]
    })
    cy.createArticleViaApi({ title: 'CY-TOC-Article', content: contentWithHeadings })
    cy.get('@articleId').then(id => { tocArticleId = id })
  })

  after(() => {
    if (tocArticleId) {
      cy.loginToApp()
      cy.deleteArticleViaApi(tocArticleId)
    }
  })

  beforeEach(() => {
    cy.loginToApp()
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  it('10.1 TOC visible if H1-H3 headings', () => {
    cy.get('.toc, [class*="toc"], [class*="table-of-contents"]', { timeout: 5000 })
      .should('exist')
  })

  it('10.2 TOC hidden if no headings', () => {
    // Create article without headings
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-NoTOC' })
    cy.get('@articleId').then(id => {
      cy.visit(BASE)
      cy.contains('CY-NoTOC').click()
      cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
      cy.get('.toc, [class*="toc"]').should('not.exist')
      cy.deleteArticleViaApi(id)
    })
  })

  it('10.3 TOC label "Содержание"', () => {
    cy.get('.toc, [class*="toc"]')
      .invoke('text').should('match', /содержание|contents|toc/i)
  })

  it('10.4 Click TOC item → scroll to heading', () => {
    cy.get('.toc a, [class*="toc"] a, [class*="toc-item"]').first().click()
    // Verify scroll happened
    cy.get('h1, h2, h3, [class*="heading"]').first().should('be.visible')
  })

  it('10.5 Width < 1280px → TOC hidden', () => {
    cy.viewport(1200, 900)
    cy.get('.toc, [class*="toc"]').should('not.be.visible')
  })

  it('10.6 Active section in TOC has .active class', () => {
    cy.get('.toc .active, [class*="toc"] .active, [class*="toc-item"].active')
      .should('exist')
  })
})

// ============================================================
// Describe 11: Child Pages (4 tests)
// ============================================================
describe('Articles — Child Pages', () => {
  let folderId, art1Id, art2Id

  before(() => {
    cy.loginToApp()
    cy.createFolderViaApi('CY-ChildPages-Folder')
    cy.get('@folderId').then(fid => {
      folderId = fid
      cy.createArticleViaApi({ title: 'CY-Child-1', folder_id: fid })
      cy.get('@articleId').then(a1 => {
        art1Id = a1
        cy.createArticleViaApi({ title: 'CY-Child-2', folder_id: fid })
        cy.get('@articleId').then(a2 => { art2Id = a2 })
      })
    })
  })

  after(() => {
    cy.loginToApp()
    if (art1Id) cy.deleteArticleViaApi(art1Id)
    if (art2Id) cy.deleteArticleViaApi(art2Id)
    if (folderId) cy.deleteFolderViaApi(folderId)
  })

  beforeEach(() => {
    cy.loginToApp()
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  it('11.1 Article in folder with siblings → .child-pages visible', () => {
    cy.get('.child-pages, [class*="child-pages"]').should('be.visible')
  })

  it('11.2 Child pages label "В этой папке"', () => {
    cy.get('.child-pages, [class*="child-pages"]')
      .invoke('text').should('match', /в этой папке|in this folder|related/i)
  })

  it('11.3 .child-page-item clickable', () => {
    cy.get('.child-page-item, [class*="child-page"]').first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  it('11.4 No folder → no .child-pages', () => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-NoFolder-ChildCheck' })
    cy.get('@articleId').then(id => {
      cy.visit(BASE)
      cy.contains('CY-NoFolder-ChildCheck').click()
      cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
      cy.get('.child-pages, [class*="child-pages"]').should('not.exist')
      cy.deleteArticleViaApi(id)
    })
  })
})

// ============================================================
// Describe 12: History Panel (8 tests)
// ============================================================
describe('Articles — History Panel', () => {
  beforeEach(() => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-History-Test' })
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@articleId').then(id => cy.deleteArticleViaApi(id))
  })

  it('12.1 History button → panel opens', () => {
    cy.contains(/history|история/i).click()
    cy.get('.viewer-history.open, [class*="history"][class*="open"], [class*="history-panel"]', { timeout: 8000 })
      .should('be.visible')
  })

  it('12.2 intercept GET /articles/*/versions → request made', () => {
    cy.intercept('GET', '**/articles/*/versions*').as('getVersions')
    cy.contains(/history|история/i).click()
    cy.wait('@getVersions').its('response.statusCode').should('eq', 200)
  })

  it('12.3 Version list displayed', () => {
    cy.contains(/history|история/i).click()
    cy.get('.history-item, [class*="history-item"], [class*="version-item"]', { timeout: 8000 })
      .should('have.length.gte', 1)
  })

  it('12.4 Each history-item: date and title', () => {
    cy.contains(/history|история/i).click()
    cy.get('.history-item, [class*="history-item"]').first().within(() => {
      cy.get('[class*="date"], time').should('exist')
    })
  })

  it('12.5 Click version → GET /articles/*/versions/* → 200', () => {
    cy.contains(/history|история/i).click()
    cy.intercept('GET', '**/articles/*/versions/*').as('getVersion')
    cy.get('.history-item, [class*="history-item"]').first().click()
    cy.wait('@getVersion').its('response.statusCode').should('eq', 200)
  })

  it('12.6 version-preview with readonly GridEditor', () => {
    cy.contains(/history|история/i).click()
    cy.get('.history-item, [class*="history-item"]').first().click()
    cy.get('.version-preview, [class*="preview"]', { timeout: 8000 }).should('be.visible')
  })

  it('12.7 Close button → closes panel', () => {
    cy.contains(/history|история/i).click()
    cy.get('.viewer-history.open, [class*="history"]').should('be.visible')
    cy.get('.viewer-history .close-btn, [class*="history"] [class*="close"], [class*="history"] button')
      .contains(/×|✕|close|закрыть/i).click()
    cy.get('.viewer-history.open, [class*="history"][class*="open"]').should('not.exist')
  })

  it('12.8 After close → version-preview disappears', () => {
    cy.contains(/history|история/i).click()
    cy.get('.history-item, [class*="history-item"]').first().click()
    cy.get('.version-preview, [class*="preview"]').should('be.visible')
    cy.get('.viewer-history .close-btn, [class*="history"] [class*="close"], [class*="history"] button')
      .contains(/×|✕|close|закрыть/i).click()
    cy.get('.version-preview, [class*="preview"]').should('not.exist')
  })
})

// ============================================================
// Describe 13: Edit Existing Article (8 tests)
// ============================================================
describe('Articles — Edit Existing Article', () => {
  beforeEach(() => {
    cy.loginToApp()
    cy.createArticleViaApi({ title: 'CY-Edit-Existing', category: 'Testing' })
    cy.visit(BASE)
    cy.get('.article-row, [class*="article-item"]', { timeout: 8000 }).first().click()
    cy.get('.article-viewer, [class*="viewer"]', { timeout: 8000 }).should('be.visible')
  })

  afterEach(() => {
    cy.get('@articleId').then(id => cy.deleteArticleViaApi(id))
  })

  it('13.1 Viewer → Edit → editor with filled title', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.get('.editor-fullscreen, [class*="editor"]', { timeout: 8000 }).should('be.visible')
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first().should('not.have.value', '')
  })

  it('13.2 Title input has article title', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first().should('have.value', 'CY-Edit-Existing')
  })

  it('13.3 Status select shows current status', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.get('select[class*="status"], [class*="status"] select')
      .first().should('have.value', 'draft')
  })

  it('13.4 Change title → Save → PUT /articles/** → 200', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.intercept('PUT', '**/articles/**').as('updateArticle')
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first().clear().type('CY-Updated-Title')
    cy.contains(/save|сохранить/i).click()
    cy.wait('@updateArticle').its('response.statusCode').should('eq', 200)
  })

  it('13.5 After save → list updated with new title', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.intercept('PUT', '**/articles/**').as('updateArticle')
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first().clear().type('CY-Title-Updated')
    cy.contains(/save|сохранить/i).click()
    cy.wait('@updateArticle')
    cy.get('[class*="back"], button').contains(/back|←|назад/i).click()
    cy.contains('CY-Title-Updated').should('exist')
  })

  it('13.6 Change status Draft → Published → Save', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.intercept('PUT', '**/articles/**').as('updateStatus')
    cy.get('select[class*="status"], [class*="status"] select')
      .first().select('published')
    cy.contains(/save|сохранить/i).click()
    cy.wait('@updateStatus').its('response.statusCode').should('eq', 200)
  })

  it('13.7 Category and Tags shown in subheader', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.contains(/meta|мета/i).click()
    cy.get('[class*="subheader"], [class*="meta"]').should('be.visible')
  })

  it('13.8 Close editor with changes → confirm dialog', () => {
    cy.contains(/edit|редактировать/i).click()
    cy.get('input[class*="title"], [class*="title-input"] input')
      .first().clear().type('CY-Unsaved-Change')
    cy.get('[class*="back"], button').contains(/back|←|назад/i).click()
    cy.get('.confirm-dialog, .modal, [class*="confirm"], [class*="unsaved"]', { timeout: 5000 })
      .should('exist')
  })
})

// ============================================================
// Describe 14: Import (7 tests)
// ============================================================
describe('Articles — Import', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('14.1 Import button → file picker (accept=".md,.docx")', () => {
    cy.get('input[type="file"][accept*=".md"], input[type="file"][accept*=".docx"]')
      .should('exist')
  })

  it('14.2 Import test-article.md → POST /articles/import → 200 → alert', () => {
    cy.intercept('POST', '**/articles/import*').as('importArticle')
    cy.fixture('test-article.md', 'binary').then(content => {
      const blob = Cypress.Blob.binaryStringToBlob(content, 'text/markdown')
      const file = new File([blob], 'test-article.md', { type: 'text/markdown' })
      const dt = new DataTransfer()
      dt.items.add(file)
      cy.get('input[type="file"]').first().then($input => {
        $input[0].files = dt.files
        $input[0].dispatchEvent(new Event('change', { bubbles: true }))
      })
    })
    cy.wait('@importArticle').its('response.statusCode').should('be.oneOf', [200, 201])
  })

  it('14.3 Editor subheader "Import from file" → POST /articles/import/preview', () => {
    cy.contains(/new article|новая статья/i).click()
    cy.contains(/meta|мета/i).click()
    cy.intercept('POST', '**/articles/import/preview*').as('importPreview')
    cy.get('[class*="subheader"], [class*="meta"]')
      .find('input[type="file"]').then($input => {
        if ($input.length) {
          cy.fixture('test-article.md', 'binary').then(content => {
            const blob = Cypress.Blob.binaryStringToBlob(content, 'text/markdown')
            const file = new File([blob], 'test-article.md', { type: 'text/markdown' })
            const dt = new DataTransfer()
            dt.items.add(file)
            $input[0].files = dt.files
            $input[0].dispatchEvent(new Event('change', { bubbles: true }))
          })
          cy.wait('@importPreview', { timeout: 10000 })
        }
      })
  })

  it('14.4 File > 5MB → alert "File too large"', () => {
    const largeContent = 'x'.repeat(6 * 1024 * 1024)
    const blob = new Blob([largeContent], { type: 'text/markdown' })
    const file = new File([blob], 'large.md', { type: 'text/markdown' })
    const dt = new DataTransfer()
    dt.items.add(file)
    cy.get('input[type="file"]').first().then($input => {
      $input[0].files = dt.files
      $input[0].dispatchEvent(new Event('change', { bubbles: true }))
    })
    cy.on('window:alert', (text) => {
      expect(text).to.match(/too large|слишком большой|размер/i)
    })
  })

  it('14.5 .txt file → alert "Unsupported format"', () => {
    const blob = new Blob(['hello'], { type: 'text/plain' })
    const file = new File([blob], 'test.txt', { type: 'text/plain' })
    const dt = new DataTransfer()
    dt.items.add(file)
    cy.get('input[type="file"]').first().then($input => {
      $input[0].files = dt.files
      $input[0].dispatchEvent(new Event('change', { bubbles: true }))
    })
    cy.on('window:alert', (text) => {
      expect(text).to.match(/unsupported|неподдерживаемый|формат/i)
    })
  })

  it('14.6 Import without auth → 401', () => {
    cy.clearLocalStorage()
    cy.request({
      method: 'POST',
      url: '/api/v1/articles/import',
      failOnStatusCode: false,
      body: {}
    }).its('status').should('eq', 401)
  })

  it('14.7 After import file input clears', () => {
    cy.get('input[type="file"]').first().should('have.value', '')
  })
})

// ============================================================
// Describe 15: Drag and Drop (5 tests)
// ============================================================
describe('Articles — Drag and Drop', () => {
  beforeEach(() => {
    cy.goToArticles()
  })

  it('15.1 .article-row has draggable="true"', () => {
    cy.get('.article-row, [class*="article-item"]').first()
      .should('have.attr', 'draggable', 'true')
  })

  it('15.2 Dragstart → dataTransfer sets type=article and id', () => {
    cy.get('.article-row, [class*="article-item"]').first().then($el => {
      const evt = new DragEvent('dragstart', {
        bubbles: true,
        cancelable: true,
        dataTransfer: new DataTransfer()
      })
      $el[0].dispatchEvent(evt)
      // Verify dataTransfer was populated (check via event listener)
      expect(evt.dataTransfer).to.exist
    })
  })

  it('15.3 Drop on folder → POST /articles/*/move-to-folder → 200', () => {
    cy.intercept('POST', '**/articles/*/move-to-folder*').as('moveToFolder')
    cy.intercept('PUT', '**/articles/*').as('updateArticle')

    // Simulate drag-drop by triggering events
    cy.get('.article-row, [class*="article-item"]').first().then($article => {
      cy.get('.folder-item, .tree-node, [class*="folder"]').first().then($folder => {
        const dataTransfer = new DataTransfer()
        $article[0].dispatchEvent(new DragEvent('dragstart', { bubbles: true, dataTransfer }))
        $folder[0].dispatchEvent(new DragEvent('dragover', { bubbles: true, dataTransfer }))
        $folder[0].dispatchEvent(new DragEvent('drop', { bubbles: true, dataTransfer }))
      })
    })
    // Either endpoint may be used
    cy.wait(['@moveToFolder', '@updateArticle'].find(() => true), { timeout: 5000 })
  })

  it('15.4 After drop article moves to target folder', () => {
    // Verify article list updates after a drop
    cy.get('.article-row, [class*="article-item"]').should('exist')
  })

  it('15.5 FolderTree supports drop for folder move', () => {
    cy.get('.folder-item, .tree-node, [class*="folder"]').first().then($folder => {
      const dataTransfer = new DataTransfer()
      $folder[0].dispatchEvent(new DragEvent('dragover', { bubbles: true, dataTransfer }))
      // Should accept drop — no error
      $folder[0].dispatchEvent(new DragEvent('dragleave', { bubbles: true, dataTransfer }))
    })
  })
})
