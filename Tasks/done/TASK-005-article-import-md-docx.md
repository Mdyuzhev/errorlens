# TASK: Import MD/DOCX Files into Articles

## Цель

Добавить возможность импортировать `.md` и `.docx` файлы как статьи с сохранением форматирования. Файл загружается через UI, парсится на бэкенде, создаётся статья с содержимым в Markdown.

## Контекст

Статьи хранят content как plain text (Markdown). При просмотре Vue рендерит Markdown → HTML через regex-замены в `ArticlesView.vue` (renderedContent computed). Импорт должен конвертировать загруженный файл в Markdown и создать статью через существующий `ArticleService.create_article()`.

### Существующие файлы

| Файл | Роль |
|------|------|
| `app/routers/articles.py` | CRUD endpoints, ArticleCreate schema |
| `app/services/article_service.py` | create_article(title, content, ...) |
| `app/models/db_models.py` | Article модель, content: Text |
| `dashboard-vue/src/services/api.js` | articlesApi — list, get, create, ... |
| `dashboard-vue/src/stores/articles.js` | Pinia store |
| `dashboard-vue/src/views/ArticlesView.vue` | Editor modal + viewer |
| `backend/requirements.txt` | python-multipart уже есть |

### Что НЕ менять

- Формат хранения content (остаётся Markdown plain text)
- Существующие CRUD endpoints
- Логику ArticleService.create_article — использовать as-is

---

## P1: Backend — Dependencies

### Файл: `backend/requirements.txt`

Добавить:

| Пакет | Версия | Назначение |
|-------|--------|------------|
| mammoth | >=1.6.0 | DOCX → HTML конвертация (сохраняет структуру: headings, lists, bold, italic, tables) |
| markdownify | >=0.11.0 | HTML → Markdown конвертация (обратная от markdown→html) |

Почему mammoth, а не python-docx:
- python-docx даёт доступ к XML-структуре, но парсить стили вручную — сотни строк кода
- mammoth конвертирует DOCX → чистый HTML за один вызов, маппит стили на семантические теги
- markdownify конвертирует этот HTML → Markdown

Pipeline: `.docx` → mammoth → HTML → markdownify → Markdown → article.content

Для `.md` файлов pipeline не нужен — читаем файл как текст.

---

## P2: Backend — Import Service

### Файл: `app/services/article_import_service.py` (новый)

| Метод | Сигнатура | Логика |
|-------|-----------|--------|
| import_from_file | (file: UploadFile, folder_id: str\|None, project_id: str, author: str, created_by: str) → Article | Определить тип → парсить → create_article |
| _parse_markdown | (content: bytes) → tuple[str, str] | Decode UTF-8, извлечь title из первого `# heading`, вернуть (title, content) |
| _parse_docx | (content: bytes) → tuple[str, str] | mammoth → HTML → markdownify → (title, markdown) |
| _extract_title | (markdown: str) → str | Первый `# ...` heading или первая непустая строка |
| _sanitize_content | (markdown: str) → str | Убрать потенциально опасный HTML, нормализовать переносы строк |

### Детали парсинга DOCX

```python
import mammoth
import markdownify
from io import BytesIO

def _parse_docx(content: bytes) -> tuple[str, str]:
    result = mammoth.convert_to_html(BytesIO(content))
    html = result.value
    # messages = result.messages  — warnings, можно логировать
    
    markdown = markdownify.markdownify(
        html,
        heading_style="ATX",        # # heading вместо underline
        bullets="-",                 # - list item
        code_language="",            # ```code blocks```
        strip=["img"],               # убрать images (нет storage для них)
        convert=["table"],           # сохранить таблицы
    )
    
    title = _extract_title(markdown)
    return title, markdown
```

### Детали парсинга MD

```python
def _parse_markdown(content: bytes) -> tuple[str, str]:
    # Try UTF-8, fallback to latin-1
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    
    # Remove BOM if present
    if text.startswith("\ufeff"):
        text = text[1:]
    
    title = _extract_title(text)
    return title, text
```

### Ограничения

| Ограничение | Значение | Обработка |
|-------------|----------|-----------|
| Max file size | 5 MB | HTTPException 413 |
| Allowed extensions | .md, .docx | HTTPException 400 |
| Empty file | 0 bytes | HTTPException 400 "File is empty" |
| Encoding | UTF-8, fallback latin-1 | Auto-detect |
| Images в DOCX | Не импортируются | strip, warning в response |

---

## P3: Backend — API Endpoint

### Файл: `app/routers/articles.py` — добавить endpoint

| Method | Endpoint | Content-Type | Response |
|--------|----------|-------------|----------|
| POST | /articles/import | multipart/form-data | ImportArticleResponse |

Request — multipart/form-data:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | UploadFile | да | .md или .docx файл |
| folder_id | str (Form) | нет | ID папки для размещения |
| category | str (Form) | нет | Категория статьи |
| status | str (Form) | нет | draft (default) или published |
| tags | str (Form) | нет | Comma-separated: "api,testing" |

Response — ImportArticleResponse:

| Field | Type |
|-------|------|
| id | str |
| title | str (extracted from file) |
| slug | str |
| content_length | int (characters) |
| warnings | list[str] (e.g., "Images were skipped") |

### Код endpoint (сигнатура)

```python
from fastapi import UploadFile, File, Form

@router.post("/import")
async def import_article(
    file: UploadFile = File(...),
    folder_id: str | None = Form(default=None),
    category: str | None = Form(default=None),
    status: str = Form(default="draft"),
    tags: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
```

### ВАЖНО: порядок роутов

Endpoint `/articles/import` ДОЛЖЕН быть зарегистрирован ВЫШЕ `/{article_id}`, иначе FastAPI перехватит "import" как article_id. Разместить после `/articles/categories/list` и перед `/{article_id}`.

---

## P4: Frontend — API Client

### Файл: `dashboard-vue/src/services/api.js`

Добавить в articlesApi:

```javascript
importFile: (formData) => api.post('/articles/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
}),
```

---

## P5: Frontend — Import UI

### Вариант реализации: кнопка "Import" рядом с "+ New Article"

В `ArticlesView.vue` добавить:

1. **Кнопка "Import" в page-header** — рядом с "+ New Article"
2. **Hidden file input** — `<input type="file" accept=".md,.docx" ref="fileInput" @change="handleFileImport">`
3. **Кнопка вызывает** `fileInput.click()`

### Логика handleFileImport

```
1. Получить file из event.target.files[0]
2. Проверить расширение (.md, .docx)
3. Проверить размер (< 5MB)
4. Показать loading state
5. Создать FormData:
   - file: File
   - folder_id: store.selectedFolderId (текущая выбранная папка)
   - status: "draft"
6. Вызвать articlesApi.importFile(formData)
7. При успехе:
   - Показать notification "Article imported: {title}"
   - Если есть warnings — показать их
   - Refresh articles list + folders tree
8. При ошибке — показать error
9. Сбросить file input value
```

### Визуал кнопки Import

| Элемент | Стиль |
|---------|-------|
| Кнопка | `btn btn-secondary`, текст "📥 Import" |
| Расположение | Слева от "+ New Article" в page-header |
| Drag & drop | НЕ реализовывать в первой версии (усложняет без пользы) |

### Также: добавить кнопку Import в Editor Modal

В форме редактора (showEditor modal), над textarea content, добавить:
- Маленькая кнопка "📎 Import from file" 
- При клике — тот же file input
- Заполняет form.title и form.content из файла (не создаёт статью, а заполняет форму)
- Пользователь может отредактировать перед сохранением

Два сценария использования:
1. **Quick import** (кнопка в header) → сразу создаёт статью как draft
2. **Import into editor** (кнопка в modal) → заполняет форму, пользователь редактирует и сохраняет

Для варианта 2 нужен отдельный backend endpoint или клиентский парсинг. Проще — отдельный endpoint:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /articles/import/preview | Парсит файл, возвращает title + content, НЕ создаёт статью |

Response preview:

| Field | Type |
|-------|------|
| title | str |
| content | str (markdown) |
| warnings | list[str] |

---

## P6: Backend — Preview Endpoint

### Файл: `app/routers/articles.py`

| Method | Endpoint | Response |
|--------|----------|----------|
| POST | /articles/import/preview | { title, content, warnings } |

Тот же парсинг что и /articles/import, но без создания статьи. Возвращает title + content для заполнения формы на фронте.

Разместить ВЫШЕ `/{article_id}`.

---

## Порядок выполнения

```
P1 (deps) → P2 (service) → P3 (endpoint import) → P6 (endpoint preview) → P4 (api.js) → P5 (UI)
```

---

## Тесты

### Backend: `backend/tests/test_article_import.py`

| Тест | Assertion |
|------|-----------|
| test_import_md_file | POST /articles/import с .md → 200, article создана, content = file content |
| test_import_md_extracts_title | Файл с `# My Title` → article.title == "My Title" |
| test_import_md_no_heading | Файл без `#` → title = первая строка |
| test_import_md_utf8 | Кириллица в файле → content сохранён корректно |
| test_import_md_bom | Файл с BOM → BOM убран из content |
| test_import_docx_file | POST с .docx → 200, article создана |
| test_import_docx_preserves_headings | `## Heading` → сохранён в markdown |
| test_import_docx_preserves_bold_italic | **bold** и *italic* → сохранены |
| test_import_docx_preserves_lists | Numbered + bulleted → markdown lists |
| test_import_docx_tables | Таблица → markdown table |
| test_import_docx_images_warning | DOCX с картинкой → warnings содержит "images skipped" |
| test_import_with_folder_id | folder_id в form → article.folder_id == folder_id |
| test_import_with_category_tags | category + tags → сохранены |
| test_import_wrong_extension | .txt файл → 400 "Unsupported file format" |
| test_import_empty_file | 0 bytes → 400 "File is empty" |
| test_import_too_large | >5MB → 413 "File too large" |
| test_import_unauthorized | Без токена → 401 |
| test_import_preview_md | POST /articles/import/preview → 200, {title, content}, статья НЕ создана |
| test_import_preview_docx | POST preview с .docx → 200, markdown content |
| test_import_multi_tenancy | owner1 import → owner2 не видит |
| test_none_handling | file=None → 422 |
| test_duplicate_title_slug | Импорт файла с тем же title → slug с timestamp суффиксом |

### Тестовые файлы

Создать `backend/tests/fixtures/` (или использовать tmpfile):

| Файл | Содержимое |
|------|-----------|
| sample_article.md | `# Test Article\n\nSome **bold** and *italic* content.\n\n## Section\n\n- item 1\n- item 2` |
| sample_article.docx | Сгенерировать через python-docx в fixture (heading + paragraph + bold + list) |
| empty.md | Пустой файл |
| cyrillic.md | `# Тестовая статья\n\nСодержимое на русском.` |

Генерация .docx fixture:

```python
@pytest.fixture
def sample_docx(tmp_path) -> Path:
    from docx import Document
    doc = Document()
    doc.add_heading("Test DOCX Article", level=1)
    doc.add_paragraph("This is a bold paragraph.", style=None)
    run = doc.paragraphs[-1].runs[0]
    run.bold = True
    doc.add_heading("Sub Section", level=2)
    doc.add_paragraph("Item one", style="List Bullet")
    doc.add_paragraph("Item two", style="List Bullet")
    path = tmp_path / "sample.docx"
    doc.save(str(path))
    return path
```

Для генерации docx fixture нужен python-docx в dev dependencies:

### Файл: `backend/requirements.txt` — добавить в секцию Testing

```
python-docx>=1.1.0    # For generating test DOCX fixtures
```

---

## Запрещено

- Хранить загруженные файлы на диске (парсим в memory, сохраняем только content в БД)
- Менять формат хранения content (остаётся plain text Markdown)
- Ломать существующие CRUD endpoints
- Файлы > 500 LOC
- Inline images из DOCX (нет image storage)

---

## Критерии готовности

| Проверка | Как убедиться |
|----------|--------------|
| Import .md | Загрузить .md → статья создана, content = содержимое файла |
| Import .docx | Загрузить .docx с headings + bold + lists → markdown корректный |
| Title extraction | Заголовок из файла → title статьи |
| Folder placement | Import при выбранной папке → статья в этой папке |
| Preview mode | Кнопка в editor → файл парсится, форма заполняется, статья НЕ создана |
| Quick import | Кнопка в header → статья создана как draft |
| Кириллица | .md с русским текстом → content корректный |
| Wrong format | .txt / .pdf → 400 error |
| Large file | >5MB → 413 error |
| Swagger | POST /articles/import — file upload работает через Swagger UI |
| Все тесты | pytest tests/test_article_import.py — all pass |
| Обратная совместимость | Существующие тесты не сломаны |

---

## Коммиты

```
[backend] Add mammoth + markdownify dependencies
[backend] Add article import service (MD + DOCX parsing)
[backend] Add /articles/import and /articles/import/preview endpoints
[frontend] Add import file button and editor integration
[test] Add article import tests with MD and DOCX fixtures
```

---

## Время: 3-4 часа
