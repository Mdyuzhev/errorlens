# TASK: Test Cases Tree Structure — Folder Hierarchy

## Цель

Продублировать древовидную структуру папок из Articles в раздел Test Cases. Максимум 3 уровня вложенности. Тест-кейсы можно перемещать между папками. Полное копирование паттерна ArticleFolder.

```
📁 API Tests
   📁 Authentication
      📁 JWT
         📄 Login returns access token
         📄 Refresh token rotation
      📄 Registration flow
   📁 Sessions
      📄 Create session with errors
📁 UI Tests
   📄 Dashboard loading
📄 Unfoldered test case
```

## Контекст

Сейчас TestCase.folder — простая строка (`String(255)`), фильтрация через dropdown. Модель `Folder` в db_models.py существует, но НЕ связана с TestCase и не имеет нужных constraint'ов. Создаём новую модель `TestCaseFolder` по образцу `ArticleFolder`.

### Файлы-образцы (КОПИРОВАТЬ ПАТТЕРН)

| Образец (Articles) | Новый файл (TestCases) |
|---------------------|----------------------|
| `app/models/db_models.py` → ArticleFolder | → TestCaseFolder |
| `app/repositories/article_folder_repo.py` | `app/repositories/testcase_folder_repo.py` |
| `app/services/article_folder_service.py` | `app/services/testcase_folder_service.py` |
| `app/routers/article_folders.py` | `app/routers/testcase_folders.py` |
| `dashboard-vue/src/components/articles/FolderTree.vue` | `dashboard-vue/src/components/testcases/FolderTree.vue` |
| `dashboard-vue/src/components/articles/FolderNode.vue` | `dashboard-vue/src/components/testcases/FolderNode.vue` |
| `dashboard-vue/src/stores/articles.js` (folder part) | `dashboard-vue/src/stores/testcases.js` (расширить) |
| `dashboard-vue/src/views/ArticlesView.vue` (sidebar) | `dashboard-vue/src/views/TestCasesView.vue` (добавить sidebar) |

### Что НЕ менять

- Существующие testcase endpoints (GET/POST/PUT/DELETE /testcases)
- Строковое поле `TestCase.folder` — оставить для обратной совместимости, но deprecated
- Существующий `GET /testcases/folders/list` — пусть работает (старые string-folders)
- Модель `Folder` в db_models.py — не трогать

---

## P1: Backend — Database Model

### Файл: `app/models/db_models.py`

Добавить модель TestCaseFolder (копия ArticleFolder с заменой имён):

| Поле | Тип | Constraints |
|------|-----|-------------|
| id | String(36), PK | default=generate_uuid |
| name | String(200) | NOT NULL |
| parent_id | String(36), FK → testcase_folders.id | nullable, ondelete=CASCADE, index=True |
| project_id | String(36), FK → projects.id | NOT NULL, ondelete=CASCADE, index=True |
| sort_order | Integer | default=0 |
| created_at | DateTime | default=utcnow |
| updated_at | DateTime | nullable |

Table args:
```python
__table_args__ = (
    UniqueConstraint("name", "parent_id", "project_id", name="uq_testcase_folder_name_parent_project"),
)
```

Relationships:
- `parent` → self-reference (remote_side=[id])
- `children` → list[TestCaseFolder], cascade="all, delete-orphan"
- `project` → Project
- `test_cases` → list[TestCase]

### Добавить в TestCase

```python
# Tree folder (new — FK reference)
folder_id: Mapped[str | None] = mapped_column(
    String(36), ForeignKey("testcase_folders.id", ondelete="SET NULL"), nullable=True, index=True
)

# Relationship
testcase_folder: Mapped[Optional["TestCaseFolder"]] = relationship(
    "TestCaseFolder", back_populates="test_cases"
)
```

Поле `folder: Mapped[str | None]` (строковое) — ОСТАВИТЬ. Не удалять, не трогать. Новый код использует `folder_id`.

### Добавить в Project relationships

```python
testcase_folders: Mapped[list["TestCaseFolder"]] = relationship(
    "TestCaseFolder", back_populates="project", cascade="all, delete-orphan"
)
```

### Миграция

```bash
alembic revision --autogenerate -m "Add TestCaseFolder model and folder_id to TestCase"
alembic upgrade head
```

---

## P2: Backend — Repository

### Файл: `app/repositories/testcase_folder_repo.py`

Копия `article_folder_repo.py` с заменами:

| Замена | Было | Стало |
|--------|------|-------|
| Model | ArticleFolder | TestCaseFolder |
| Relationship | ArticleFolder.articles | TestCaseFolder.test_cases |
| Class | ArticleFolderRepository | TestCaseFolderRepository |

Методы (идентичны article_folder_repo):

| Метод | Логика |
|-------|--------|
| get_tree(project_id) | SELECT root folders + selectinload children (3 levels) + test_cases |
| get_children(folder_id) | SELECT WHERE parent_id = X |
| get_depth(folder_id) | Traverse parent chain, root = 1 |
| get_by_name_and_parent(name, parent_id, project_id) | Check duplicate |
| get_descendants(folder_id) | Recursive all descendant IDs |
| get_max_subtree_depth(folder_id) | Max depth below folder |

**ВАЖНО**: В `get_tree` selectinload должен загружать `TestCaseFolder.test_cases` вместо `ArticleFolder.articles`.

---

## P3: Backend — Service

### Файл: `app/services/testcase_folder_service.py`

Копия `article_folder_service.py` с заменами:

| Замена | Было | Стало |
|--------|------|-------|
| Model | ArticleFolder | TestCaseFolder |
| Repo | ArticleFolderRepository | TestCaseFolderRepository |
| Entity repo | ArticleRepository | TestCaseRepository |
| Entity field | article.folder_id | testcase.folder_id |
| Class | ArticleFolderService | TestCaseFolderService |

Методы:

| Метод | Логика |
|-------|--------|
| create_folder(name, project_id, parent_id) | Depth ≤ 3, unique name, create |
| get_tree(project_id) | Load all → nested dict |
| update_folder(folder_id, name, project_id) | Unique name check |
| delete_folder(folder_id) | test_cases.folder_id → parent_id or NULL, delete cascade |
| move_folder(folder_id, new_parent_id) | Not self, not descendant, depth ≤ 3 |
| move_testcase_to_folder(testcase_id, folder_id) | Update testcase.folder_id |

### _folder_to_tree — адаптация

Вместо articles summary, отдавать test cases summary:

```python
"test_cases": [
    {
        "id": tc.id,
        "title": tc.title,
        "status": tc.status,
        "priority": tc.priority,
        "automation_status": tc.automation_status,
        "created_at": tc.created_at.isoformat() if tc.created_at else None,
    }
    for tc in test_cases
],
"test_cases_count": len(test_cases),
```

---

## P4: Backend — API Endpoints

### Файл: `app/routers/testcase_folders.py`

Копия `article_folders.py` с prefix="/testcases/folders", tags=["testcase-folders"].

| Method | Endpoint | Request | Response |
|--------|----------|---------|----------|
| GET | /testcases/folders | query: project_id | { folders: [...tree...] } |
| POST | /testcases/folders | CreateFolderRequest | { id, name, parent_id } |
| PUT | /testcases/folders/{id} | UpdateFolderRequest | { id, name, parent_id } |
| DELETE | /testcases/folders/{id} | — | 204 |
| POST | /testcases/folders/{id}/move | MoveFolderRequest | { id, name, parent_id } |

Pydantic schemas (в том же файле):

| Schema | Fields |
|--------|--------|
| CreateFolderRequest | name: str, parent_id: str \| None, project_id: str \| None |
| UpdateFolderRequest | name: str |
| MoveFolderRequest | new_parent_id: str \| None |
| MoveTestCaseRequest | folder_id: str \| None |

### Отдельный router для move test case

```python
move_router = APIRouter(prefix="/testcases", tags=["testcase-folders"])

@move_router.post("/{testcase_id}/move-to-folder")
async def move_testcase_to_folder(...)
```

### Регистрация в main.py

```python
from app.routers import testcase_folders
app.include_router(testcase_folders.router)
app.include_router(testcase_folders.move_router)
```

### ВАЖНО: порядок роутов

`/testcases/folders` и `/testcases/folders/{id}` ДОЛЖНЫ быть зарегистрированы ДО `/testcases/{testcase_id}`. Либо зарегистрировать testcase_folders.router перед testcases.router в main.py.

### Обновить существующий `app/routers/testcases.py`

В `list_testcases` добавить query param `folder_id`:

```python
@router.get("")
async def list_testcases(
    folder: str | None = None,       # OLD string filter (backward compat)
    folder_id: str | None = None,    # NEW FK filter
    ...
):
```

В `TestCaseCreate` schema добавить:

```python
folder_id: str | None = None
```

В `create_testcase` endpoint передать `folder_id`.

---

## P5: Frontend — API Client

### Файл: `dashboard-vue/src/services/api.js`

Добавить в testCasesApi:

```javascript
// Folders tree
getFoldersTree: (params) => api.get('/testcases/folders', { params }),
createFolder: (data) => api.post('/testcases/folders', data),
updateFolder: (id, data) => api.put(`/testcases/folders/${id}`, data),
deleteFolder: (id) => api.delete(`/testcases/folders/${id}`),
moveFolder: (id, data) => api.post(`/testcases/folders/${id}/move`, data),
moveTestCaseToFolder: (id, data) => api.post(`/testcases/${id}/move-to-folder`, data),
```

---

## P6: Frontend — Store

### Файл: `dashboard-vue/src/stores/testcases.js` — расширить

Добавить state (по образцу articles store):

```javascript
// Folder tree
folders: [],              // Nested tree structure
expandedFolders: new Set(),
selectedFolderId: null,
```

Добавить actions:

| Action | API | Логика |
|--------|-----|--------|
| fetchFoldersTree() | GET /testcases/folders | → this.folders = response.data.folders |
| createFolder(name, parentId) | POST | → fetchFoldersTree() |
| updateFolder(id, name) | PUT | → fetchFoldersTree() |
| deleteFolder(id) | DELETE | → fetchFoldersTree() + fetchTestCases() |
| moveFolder(id, newParentId) | POST move | → fetchFoldersTree() |
| moveTestCaseToFolder(tcId, folderId) | POST move-to-folder | → fetchFoldersTree() + fetchTestCases() |
| toggleFolder(id) | — | add/remove from expandedFolders |
| selectFolder(id) | — | this.selectedFolderId = id; fetchTestCases() |

Изменить `fetchTestCases`:
- Если `selectedFolderId` установлен → добавить `folder_id` в params
- Если null → не фильтровать (все тест-кейсы)

---

## P7: Frontend — Components

### Файл: `dashboard-vue/src/components/testcases/FolderTree.vue`

Копия `components/articles/FolderTree.vue` с заменами:

| Замена | Было | Стало |
|--------|------|-------|
| "All Articles" | → | "All Test Cases" |
| FolderNode import | @/components/articles/ | @/components/testcases/ |
| articles references | → | test cases |

### Файл: `dashboard-vue/src/components/testcases/FolderNode.vue`

Копия `components/articles/FolderNode.vue` с заменами:

| Замена | Было | Стало |
|--------|------|-------|
| folder.articles | → | folder.test_cases |
| folder.articles_count | → | folder.test_cases_count |
| article-item class | → | testcase-item |
| article.title | → | tc.title |
| onArticleDragStart | → | onTestCaseDragStart |
| itemType: 'article' | → | itemType: 'testcase' |
| 📄 icon for articles | → | 📋 icon for test cases |

Context menu items остаются те же: Rename, New Subfolder, Delete.

---

## P8: Frontend — TestCasesView Update

### Файл: `dashboard-vue/src/views/TestCasesView.vue`

Переделать layout по образцу ArticlesView:

| Зона | Содержимое |
|------|-----------|
| Left sidebar (250px) | FolderTree component |
| Main area | Test cases grid + filters |

Что добавить:
1. Import FolderTree из `@/components/testcases/FolderTree.vue`
2. `<div class="testcases-layout">` → `<aside class="sidebar">` + `<div class="main-area">`
3. CSS для sidebar (скопировать из ArticlesView)
4. Handlers: handleSelectFolder, handleCreateFolder, handleRenameFolder, handleDeleteFolder, handleDrop
5. Drag events на testcase-card: `draggable="true"`, `@dragstart="onTestCaseDragStart($event, tc)"`

Логика (идентична ArticlesView):
- При выборе папки → fetchTestCases с folder_id
- При "All Test Cases" → fetchTestCases без folder_id
- Drag testcase → folder → moveTestCaseToFolder
- Drag folder → folder → moveFolder

### Existing filters

Существующие dropdown filters (folder, status, priority) — ОСТАВИТЬ в main area. Dropdown "All Folders" (строковый) можно скрыть или оставить для обратной совместимости. При выборе папки в дереве, строковый dropdown filter сбрасывается.

### В editor modal

В форме редактора, поле `folder` (строковое input) — заменить на hidden `folder_id` из selectedFolderId. Или добавить dropdown с tree-папками. Простой вариант: убрать текстовое поле folder, при создании тест-кейса автоматически присваивать folder_id = selectedFolderId.

---

## P9: Frontend — Drag & Drop

Идентично Articles:

| Источник | Цель | Action |
|----------|------|--------|
| TestCase card | Folder | moveTestCaseToFolder(tcId, folderId) |
| TestCase card | Root ("All Test Cases") | moveTestCaseToFolder(tcId, null) |
| Folder | Folder | moveFolder(folderId, targetId) |
| Folder | Root | moveFolder(folderId, null) |

Валидация: folder в себя, folder в потомка, depth > 3 — всё как в Articles.

---

## Порядок выполнения

```
P1 (model+migration) → P2 (repo) → P3 (service) → P4 (endpoints) → P5 (api.js) → P6 (store) → P7 (components) → P8 (view) → P9 (drag&drop)
```

---

## Тесты

### Backend: `backend/tests/test_testcase_folders.py`

| Тест | Assertion |
|------|-----------|
| test_create_folder_root | POST → 200, folder created |
| test_create_folder_nested | parent_id set correctly |
| test_create_folder_depth_3_ok | Third level → 200 |
| test_create_folder_depth_4_rejected | Fourth level → 400 "Maximum nesting depth is 3" |
| test_create_folder_duplicate_name | Same name+parent → 400 |
| test_create_folder_same_name_different_parent | OK |
| test_get_tree | Nested structure with children and test_cases |
| test_update_folder_name | PUT → name updated |
| test_delete_folder_moves_testcases | test_cases.folder_id → parent_id or NULL |
| test_delete_folder_cascades_children | Children deleted |
| test_move_folder_valid | parent_id updated |
| test_move_folder_to_root | parent_id = NULL |
| test_move_folder_to_self | 400 "Cannot move folder into itself" |
| test_move_folder_to_descendant | 400 "Cannot move folder into its descendant" |
| test_move_folder_exceeds_depth | 400 depth |
| test_move_testcase_to_folder | folder_id updated |
| test_move_testcase_to_root | folder_id = NULL |
| test_list_testcases_by_folder_id | GET /testcases?folder_id=X → filtered |
| test_create_testcase_with_folder_id | POST /testcases with folder_id → saved |
| test_folder_multi_tenancy | Isolation check |
| test_empty_name | 422 |
| test_nonexistent_folder_id | 404 |

---

## Запрещено

- Удалять поле `TestCase.folder` (строковое) — обратная совместимость
- Удалять endpoint `/testcases/folders/list` (старый string-based)
- Удалять или модифицировать модель `Folder` в db_models.py
- Ломать существующие testcase endpoints
- In-memory кэш
- Файлы > 500 LOC

---

## Критерии готовности

| Проверка | Как убедиться |
|----------|--------------|
| Модель создана | `alembic upgrade head` без ошибок |
| CRUD folders | POST/GET/PUT/DELETE через Swagger |
| Depth ≤ 3 | POST depth=4 → 400 |
| Move validation | self → 400, descendant → 400 |
| Tree endpoint | GET /testcases/folders → nested JSON с test_cases |
| Filter by folder_id | GET /testcases?folder_id=X → filtered |
| Vue sidebar | Дерево папок слева, тест-кейсы справа |
| Drag testcase → folder | Тест-кейс перемещён |
| Drag folder → folder | Папка перемещена (depth ≤ 3) |
| Context menu | Right-click → Rename, Delete, New Subfolder |
| Old endpoints work | /testcases/folders/list, folder string filter — не сломаны |
| Все тесты | pytest — all pass |

---

## Коммиты

```
[backend] Add TestCaseFolder model and migration
[backend] Add testcase folder repository and service
[backend] Add testcase folder API endpoints
[backend] Add folder_id support to testcase CRUD
[frontend] Add testcase folder API methods and store actions
[frontend] Add testcase FolderTree and FolderNode components
[frontend] Update TestCasesView with sidebar layout and drag-drop
[test] Add testcase folder backend tests
```

---

## Время: 4-5 часов

Большая часть — copy-paste из Articles с заменой имён. Основное время на адаптацию Vue и тесты.
