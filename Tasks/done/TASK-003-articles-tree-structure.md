# TASK: Articles Tree Structure — Folder Hierarchy

## Цель

Добавить иерархию папок в раздел Articles. Максимум 3 уровня вложенности. Статьи можно перемещать между папками. Папки можно вкладывать друг в друга.

```
📁 Getting Started
   📁 Basics
      📄 Welcome to ErrorLens
      📄 First Steps
   📄 Quick Start Guide
📁 Advanced
   📄 API Integration
📄 Uncategorized Article
```

## Контекст

Сейчас Articles — плоский список с фильтрацией по category. Папок нет. Нужно добавить модель ArticleFolder, связать с Article через folder_id, реализовать CRUD + tree + drag-and-drop.

### Существующие файлы (НЕ удалять, расширять)

| Файл | Что есть |
|------|----------|
| `app/models/db_models.py` | Article модель (без folder_id) |
| `app/repositories/article_repo.py` | ArticleRepository(BaseRepository) |
| `app/services/article_service.py` | ArticleService — CRUD + slug |
| `app/routers/articles.py` | CRUD endpoints + categories |
| `dashboard-vue/src/stores/articles.js` | Pinia store — fetch, create, update, delete |
| `dashboard-vue/src/views/ArticlesView.vue` | Grid layout + editor modal |
| `dashboard-vue/src/services/api.js` | articlesApi — list, get, create, update, delete, getCategories |

### Паттерны проекта

| Паттерн | Образец |
|---------|---------|
| Repository | `app/repositories/base.py` → BaseRepository(Generic[ModelType]) |
| Model с self-reference | `app/models/db_models.py` → Folder (parent_id FK to self) |
| Service | `app/services/article_service.py` → ArticleService(db) |
| Router | `app/routers/articles.py` → Pydantic schemas + Depends(get_db, require_auth) |
| Multi-tenancy | project_id + check_project_access() на каждом endpoint |

---

## P1: Backend — Database Model

### Файл: `app/models/db_models.py`

Добавить модель ArticleFolder:

| Поле | Тип | Constraints |
|------|-----|-------------|
| id | String(36), PK | default=generate_uuid |
| name | String(200) | NOT NULL |
| parent_id | String(36), FK → article_folders.id | nullable, ondelete=CASCADE |
| project_id | String(36), FK → projects.id | NOT NULL, ondelete=CASCADE |
| sort_order | Integer | default=0 |
| created_at | DateTime | default=utcnow |
| updated_at | DateTime | nullable |

Relationships:
- `parent` → self-reference (remote_side=[id])
- `children` → list[ArticleFolder], cascade="all, delete-orphan"
- `project` → Project
- `articles` → list[Article]

Добавить в существующую модель Article:
- `folder_id: Mapped[str | None]` → FK article_folders.id, nullable, ondelete=SET NULL
- `folder` → relationship("ArticleFolder", back_populates="articles")

Добавить в Project.relationships:
- `article_folders` → list[ArticleFolder]

### Constraints

| Constraint | Реализация |
|------------|------------|
| Unique name per parent | UniqueConstraint("name", "parent_id", "project_id") в __table_args__ |
| Max depth 3 | Валидация в service, НЕ в модели |
| Cascade delete | parent delete → children cascade → articles.folder_id = NULL |

### Миграция

Alembic revision --autogenerate:
- CREATE TABLE article_folders
- ALTER TABLE articles ADD COLUMN folder_id
- ADD FK articles.folder_id → article_folders.id
- ADD INDEX article_folders.parent_id
- ADD INDEX article_folders.project_id

---

## P2: Backend — Repository & Service

### Файл: `app/repositories/article_folder_repo.py`

Наследует BaseRepository[ArticleFolder].

| Метод | Сигнатура | SQL логика |
|-------|-----------|------------|
| get_tree | (project_id: str) → list[ArticleFolder] | SELECT * WHERE project_id=X, eager load children + articles |
| get_children | (folder_id: str) → list[ArticleFolder] | SELECT * WHERE parent_id=X |
| get_depth | (folder_id: str) → int | Рекурсивный подсчёт через parent_id (CTE или loop) |
| get_by_name_and_parent | (name: str, parent_id: str\|None, project_id: str) → ArticleFolder\|None | Проверка дубликата имени |
| get_descendants | (folder_id: str) → list[str] | Все потомки рекурсивно (для проверки move) |

### Файл: `app/services/article_folder_service.py`

| Метод | Логика | Ошибки |
|-------|--------|--------|
| create_folder(name, parent_id, project_id) | Проверить depth ≤ 3, unique name, создать | 400 depth, 400 duplicate |
| get_tree(project_id) | Загрузить все folders + articles, собрать nested dict | — |
| update_folder(folder_id, name) | Проверить unique name в том же parent | 400 duplicate |
| delete_folder(folder_id) | articles.folder_id → parent_id или NULL, удалить folder + children | 404 not found |
| move_folder(folder_id, new_parent_id) | Проверить: not self, not descendant, new depth ≤ 3 | 400 self, 400 descendant, 400 depth |
| move_article_to_folder(article_id, folder_id) | Обновить article.folder_id | 404 article, 404 folder |

### Валидация глубины

```
get_depth(folder_id) — считает уровни вверх до root:
  root folder → depth 1
  child of root → depth 2
  grandchild → depth 3
  
move_folder → новая depth = get_depth(new_parent_id) + 1 + max_subtree_depth(folder_id)
  Если > 3 → 400
```

---

## P3: Backend — API Endpoints

### Файл: `app/routers/article_folders.py`

Новый роутер, prefix="/articles/folders", tags=["article-folders"].

| Method | Endpoint | Request Body | Response | Auth |
|--------|----------|-------------|----------|------|
| GET | /articles/folders | query: project_id | FolderTreeResponse | require_auth + check_project_access |
| POST | /articles/folders | CreateFolderRequest | FolderResponse | require_auth + check_project_access(member) |
| PUT | /articles/folders/{id} | UpdateFolderRequest | FolderResponse | require_auth + check_project_access(member) |
| DELETE | /articles/folders/{id} | — | 204 | require_auth + check_project_access(admin) |
| POST | /articles/folders/{id}/move | MoveFolderRequest | FolderResponse | require_auth + check_project_access(member) |
| POST | /articles/{id}/move-to-folder | MoveArticleRequest | {"message": "ok"} | require_auth + check_project_access(member) |

### Pydantic Schemas (в том же файле или отдельный schemas)

| Schema | Fields |
|--------|--------|
| CreateFolderRequest | name: str, parent_id: str \| None = None, project_id: str \| None = None |
| UpdateFolderRequest | name: str |
| MoveFolderRequest | new_parent_id: str \| None = None (None = move to root) |
| MoveArticleRequest | folder_id: str \| None = None (None = move to root) |
| FolderResponse | id, name, parent_id, articles_count: int, children_count: int |
| FolderWithChildren | id, name, children: list[FolderWithChildren], articles: list[ArticleSummary] |
| FolderTreeResponse | folders: list[FolderWithChildren] |
| ArticleSummary | id, title, slug, status, created_at |

### Регистрация роутера

В `app/main.py` добавить:
```python
from app.routers import article_folders
app.include_router(article_folders.router)
```

### Обновить существующий `app/routers/articles.py`

В endpoints list_articles и create_article добавить поддержку folder_id:
- GET /articles → query param `folder_id` (optional) для фильтрации
- POST /articles → поле `folder_id` в ArticleCreate schema

---

## P4: Frontend — Store

### Файл: `dashboard-vue/src/stores/articles.js` — расширить

Новый state:

| Поле | Тип | Назначение |
|------|-----|------------|
| folders | Array | Дерево папок |
| expandedFolders | Set | ID развёрнутых папок |
| selectedFolderId | String\|null | Текущая выбранная папка (фильтр) |

Новые actions:

| Action | API call | Что делает |
|--------|----------|------------|
| fetchFoldersTree() | GET /articles/folders | Загрузить дерево, положить в folders |
| createFolder(name, parentId) | POST /articles/folders | Создать → fetchFoldersTree() |
| updateFolder(id, name) | PUT /articles/folders/{id} | Обновить → fetchFoldersTree() |
| deleteFolder(id) | DELETE /articles/folders/{id} | Удалить → fetchFoldersTree() + fetchArticles() |
| moveFolder(id, newParentId) | POST /articles/folders/{id}/move | Переместить → fetchFoldersTree() |
| moveArticleToFolder(articleId, folderId) | POST /articles/{id}/move-to-folder | Переместить → fetchFoldersTree() + fetchArticles() |
| toggleFolder(id) | — | Add/remove из expandedFolders |
| selectFolder(id) | — | Установить selectedFolderId, вызвать fetchArticles с folder_id |

### Файл: `dashboard-vue/src/services/api.js` — расширить articlesApi

Добавить методы:

| Метод | Вызов |
|-------|-------|
| getFoldersTree(params) | GET /articles/folders |
| createFolder(data) | POST /articles/folders |
| updateFolder(id, data) | PUT /articles/folders/{id} |
| deleteFolder(id) | DELETE /articles/folders/{id} |
| moveFolder(id, data) | POST /articles/folders/{id}/move |
| moveArticleToFolder(id, data) | POST /articles/{id}/move-to-folder |

---

## P5: Frontend — Components

### Файл: `dashboard-vue/src/components/articles/FolderTree.vue`

Компонент-контейнер для дерева папок.

| Prop | Тип |
|------|-----|
| folders | Array (nested tree) |
| selectedFolderId | String\|null |
| expandedIds | Set |

| Emit | Payload |
|------|---------|
| select | folderId\|null |
| toggle | folderId |
| create | parentId\|null |
| rename | { id, name } |
| delete | folderId |
| drop | { itemId, itemType: 'article'\|'folder', targetFolderId } |

Содержит:
- Кнопка "All Articles" (select(null))
- Кнопка "+ New Folder"
- Рекурсивный рендер FolderNode для каждой root folder

### Файл: `dashboard-vue/src/components/articles/FolderNode.vue` (рекурсивный)

| Prop | Тип |
|------|-----|
| folder | Object |
| depth | Number |
| expanded | Boolean |
| selected | Boolean |

| Визуал | Правило |
|--------|---------|
| Indent | depth * 16px padding-left |
| Arrow | ▶ collapsed, ▼ expanded (только если есть children или articles) |
| Icon | 📁 |
| Highlight | Выделение при selected |
| Drop zone | CSS highlight при drag over |
| Context menu | Правый клик → Rename, Delete, New subfolder |

Рекурсивно рендерит `<FolderNode>` для каждого child + `<ArticleTreeItem>` для articles.

### Файл: `dashboard-vue/src/components/articles/ArticleTreeItem.vue`

| Prop | Тип |
|------|-----|
| article | Object (ArticleSummary) |
| depth | Number |

| Функция | Описание |
|---------|----------|
| Click | Emit open-article |
| Draggable | HTML5 drag с dataTransfer {type: 'article', id} |
| Indent | depth * 16px + 24px (для иконки папки) |

---

## P6: Frontend — ArticlesView Update

### Файл: `dashboard-vue/src/views/ArticlesView.vue` — переработать layout

Текущий: grid layout на всю ширину.
Новый: sidebar (250px) + main area.

| Зона | Содержимое |
|------|-----------|
| Left sidebar (250px) | FolderTree component |
| Main area | Articles grid (filtered by selectedFolderId) |

Логика:
- При выборе папки → fetchArticles с folder_id query param
- При выборе "All" → fetchArticles без folder_id
- Существующие модалки (editor, viewer) — оставить как есть
- В ArticleCreate form добавить поле folder_id (hidden, from selectedFolderId)

---

## P7: Frontend — Drag & Drop

### Требования

| Источник | Цель | Действие |
|----------|------|----------|
| Article | Folder | moveArticleToFolder(articleId, folderId) |
| Article | Root ("All Articles") | moveArticleToFolder(articleId, null) |
| Folder | Folder | moveFolder(folderId, targetFolderId) |
| Folder | Root | moveFolder(folderId, null) |

### Валидация на фронте (перед отправкой)

| Проверка | Действие |
|----------|----------|
| Folder в себя | Запретить drop, показать ❌ cursor |
| Folder в потомка | Запретить drop |
| Depth > 3 при drop | Запретить drop |

### HTML5 Drag and Drop events

| Event | Обработчик |
|-------|-----------|
| dragstart | setData {type, id}, добавить class .dragging |
| dragover | preventDefault, проверить valid target, показать .drop-target |
| dragleave | Убрать .drop-target |
| drop | Вызвать moveArticle или moveFolder |
| dragend | Cleanup всех классов |

---

## Порядок выполнения

```
P1 → P2 → P3 → P4 → P5 → P6 → P7
```

Каждая фаза — отдельный коммит. Тесты после каждой фазы.

---

## Тесты

### Backend тесты: `backend/tests/test_article_folders.py`

| Тест | Assertion |
|------|-----------|
| test_create_folder_root | POST /articles/folders → 200, folder создана |
| test_create_folder_nested | POST с parent_id → folder.parent_id == parent_id |
| test_create_folder_depth_3 | Третий уровень → 200 OK |
| test_create_folder_depth_4_rejected | Четвёртый уровень → 400 "Maximum nesting depth is 3" |
| test_create_folder_duplicate_name | Та же name + parent → 400 "Folder with this name already exists" |
| test_create_folder_same_name_different_parent | OK — разные parent допустимы |
| test_get_tree | GET /articles/folders → nested structure с children и articles |
| test_update_folder_name | PUT → name обновлено |
| test_delete_folder_moves_articles | DELETE folder → articles.folder_id = parent_id или NULL |
| test_delete_folder_cascades_children | DELETE parent → children удалены |
| test_move_folder_valid | POST move → folder.parent_id обновлён |
| test_move_folder_to_root | POST move с null → folder.parent_id = NULL |
| test_move_folder_to_self | POST move в себя → 400 "Cannot move folder into itself" |
| test_move_folder_to_descendant | POST move в потомка → 400 "Cannot move folder into its descendant" |
| test_move_folder_exceeds_depth | POST move → depth > 3 → 400 |
| test_move_article_to_folder | POST /articles/{id}/move-to-folder → article.folder_id обновлён |
| test_move_article_to_root | POST с null → article.folder_id = NULL |
| test_folder_multi_tenancy | owner1 не видит folders owner2 |
| test_empty_input | Пустое name → 422 |
| test_none_handling | несуществующий folder_id → 404 |

---

## Запрещено

- Менять существующие API контракты (GET /articles должен работать как раньше)
- Удалять category из Article (folders дополняют, не заменяют)
- Делать depth > 3
- Добавлять in-memory кэш для дерева
- Файлы > 500 LOC

---

## Критерии готовности

| Проверка | Как убедиться |
|----------|--------------|
| Модель создана | `alembic upgrade head` без ошибок |
| CRUD folders работает | POST/GET/PUT/DELETE через Swagger |
| Depth ≤ 3 enforced | POST с depth=4 → 400 |
| Move folder | move to self → 400, move to descendant → 400 |
| Tree endpoint | GET /articles/folders → nested JSON |
| Articles filter | GET /articles?folder_id=X → только статьи из папки |
| Vue sidebar | Дерево папок слева, статьи справа |
| Drag article → folder | Статья перемещена |
| Drag folder → folder | Папка перемещена (если depth ≤ 3) |
| Context menu | Правый клик → rename, delete, new subfolder |
| Все тесты | pytest tests/test_article_folders.py — all pass |
| Обратная совместимость | Существующие тесты не сломаны |

---

## Коммиты

```
[backend] P1: Add ArticleFolder model and migration
[backend] P2: Add folder repository and service with depth validation
[backend] P3: Add folder API endpoints
[frontend] P4: Update articles store with folder actions
[frontend] P5: Add FolderTree, FolderNode, ArticleTreeItem components
[frontend] P6: Update ArticlesView with sidebar layout
[frontend] P7: Add drag & drop for articles and folders
[test] Add article folders backend tests
```

---

## Время: 6-8 часов (все фазы)
