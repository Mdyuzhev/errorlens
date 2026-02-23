# TASK-006: Article Images — MinIO Storage

> **После выполнения:** обновить TASK-005 (import DOCX) — заменить `strip=["img"]` на mammoth image handler с загрузкой в MinIO.

## Цель

Добавить поддержку изображений в статьях. Изображения хранятся в MinIO (S3-совместимый object storage). В Markdown статьи вставляется ссылка `![alt](/api/articles/images/uuid.png)`. Пользователь может загружать изображения через editor, а также вставлять drag-and-drop и paste из clipboard.

## Контекст

Сейчас статьи содержат только текст (Markdown). Изображений нигде в проекте нет — это первый file storage. MinIO выбран потому что даёт S3-совместимый API, при необходимости миграция на AWS S3 / Cloudflare R2 — замена одного endpoint URL.

### Существующая инфраструктура

| Компонент | Состояние |
|-----------|-----------|
| docker-compose.yml | 3 сервиса: postgres, backend, nginx |
| Backend config | `app/config.py` → Settings (pydantic-settings) |
| .env | POSTGRES_PASSWORD, LLM keys, TestIt |
| Articles API | CRUD + folders + import (TASK-004) |
| Article content | Plain text Markdown в PostgreSQL |
| Nginx | Раздаёт landing, dashboard, проксирует /api/ → backend:8000 |

### Что НЕ менять

- Формат content статей (Markdown text)
- Существующие CRUD endpoints
- Docker volumes для postgres

---

## P1: Infrastructure — MinIO в Docker Compose

### Файл: `docker/docker-compose.yml`

Добавить сервис minio и minio-init:

```yaml
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"     # S3 API
      - "9001:9001"     # Web Console
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-errorlens}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-errorlens_secret}
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  minio-init:
    image: minio/mc:latest
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 $${MINIO_ROOT_USER:-errorlens} $${MINIO_ROOT_PASSWORD:-errorlens_secret};
      mc mb --ignore-existing local/article-images;
      mc anonymous set download local/article-images;
      exit 0;
      "
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:-errorlens}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-errorlens_secret}
```

Добавить volume:

```yaml
volumes:
  postgres_data:
  minio_data:
```

### Пояснения

- `minio-init` — одноразовый контейнер, создаёт bucket `article-images` и устанавливает public read policy (изображения отдаются без авторизации, как и обычная статика)
- Port 9001 — MinIO Console (веб-интерфейс для отладки), можно убрать в production
- `mc ready local` — официальный healthcheck от MinIO

### Backend depends_on

Добавить в backend зависимость:

```yaml
  backend:
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
```

---

## P2: Backend — Config & Dependencies

### Файл: `backend/requirements.txt`

Добавить:

| Пакет | Назначение |
|-------|------------|
| boto3>=1.34.0 | AWS S3-совместимый SDK (работает с MinIO) |
| Pillow>=10.0.0 | Валидация изображений, resize thumbnails |

### Файл: `backend/app/config.py`

Добавить в Settings:

```python
    # MinIO / S3 Storage
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "errorlens"
    minio_secret_key: str = "errorlens_secret"
    minio_bucket: str = "article-images"
    minio_use_ssl: bool = False
    minio_public_url: str = ""  # Override for external access, empty = auto
    
    # Image limits
    max_image_size_mb: int = 10
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"]
    image_max_dimension: int = 2048  # Max width/height in px, resize if larger
```

### Файл: `.env`

Добавить:

```
MINIO_ROOT_USER=errorlens
MINIO_ROOT_PASSWORD=errorlens_secret
MINIO_ENDPOINT=minio:9000
```

### Файл: `.env.example`

Добавить те же переменные с дефолтами.

---

## P3: Backend — Storage Service

### Файл: `app/services/storage_service.py` (новый)

Абстракция над S3-совместимым хранилищем. Используем boto3 напрямую — без обёрток, минимальный код.

| Метод | Сигнатура | Логика |
|-------|-----------|--------|
| __init__ | () | Создать boto3 client с endpoint_url, credentials |
| upload_image | (file_content: bytes, filename: str, content_type: str, project_id: str) → ImageUploadResult | Validate → resize if needed → generate key → put_object → return URL |
| delete_image | (object_key: str) → bool | delete_object |
| get_image_url | (object_key: str) → str | Построить публичный URL |
| _validate_image | (content: bytes, content_type: str) → None | Проверить тип, размер, целостность через Pillow |
| _resize_if_needed | (content: bytes, max_dim: int) → bytes | Pillow resize если > max_dimension |
| _generate_key | (filename: str, project_id: str) → str | `{project_id}/{uuid}.{ext}` |

### ImageUploadResult (dataclass или Pydantic)

| Поле | Тип | Пример |
|------|-----|--------|
| object_key | str | "proj-abc/a1b2c3d4.png" |
| url | str | "/api/articles/images/proj-abc/a1b2c3d4.png" |
| filename | str | "screenshot.png" (original) |
| size_bytes | int | 245760 |
| width | int | 1024 |
| height | int | 768 |
| content_type | str | "image/png" |

### S3 Key Structure

```
article-images/          ← bucket
  {project_id}/          ← изоляция по проекту
    {uuid}.{ext}         ← файл
```

UUID в имени файла гарантирует уникальность и предотвращает перезапись. Оригинальное имя файла сохраняется в response (filename), но не используется как ключ.

### Инициализация boto3 client

```python
import boto3
from botocore.config import Config

class StorageService:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=f"http{'s' if settings.minio_use_ssl else ''}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",  # MinIO default
        )
        self.bucket = settings.minio_bucket
```

### Публичный URL

Изображения отдаются через backend endpoint (а не напрямую из MinIO), чтобы:
1. Не выставлять MinIO порт наружу
2. Сохранить единый URL паттерн через nginx `/api/`
3. Контролировать доступ при необходимости

URL формат: `/api/articles/images/{project_id}/{uuid}.{ext}`

Backend endpoint стримит файл из MinIO → клиенту. Nginx кэширует через proxy_cache при необходимости.

---

## P4: Backend — Database Model

### Файл: `app/models/db_models.py`

Добавить модель ArticleImage — метаданные об изображениях:

| Поле | Тип | Constraints |
|------|-----|-------------|
| id | String(36), PK | default=generate_uuid |
| object_key | String(500) | NOT NULL, unique — ключ в MinIO |
| original_filename | String(500) | NOT NULL — имя загруженного файла |
| content_type | String(100) | NOT NULL |
| size_bytes | Integer | NOT NULL |
| width | Integer | nullable |
| height | Integer | nullable |
| project_id | String(36), FK → projects.id | NOT NULL, ondelete=CASCADE |
| article_id | String(36), FK → articles.id | nullable, ondelete=SET NULL |
| uploaded_by | String(36), FK → users.id | nullable, ondelete=SET NULL |
| created_at | DateTime | default=utcnow |

### Зачем таблица если файлы в MinIO?

- Связь image ↔ article для cleanup (удалил статью → удалить orphan images)
- Multi-tenancy: project_id для изоляции и квот
- Аудит: кто загрузил, когда
- Поиск: все изображения проекта/статьи
- Orphan cleanup: images не привязанные к статьям (загружены но не вставлены)

### Relationship

Article → images: `images: Mapped[list["ArticleImage"]] = relationship("ArticleImage", back_populates="article")`

### Миграция

Alembic revision --autogenerate → CREATE TABLE article_images.

---

## P5: Backend — API Endpoints

### Файл: `app/routers/article_images.py` (новый)

| Method | Endpoint | Content-Type | Response |
|--------|----------|-------------|----------|
| POST | /articles/images/upload | multipart/form-data | ImageUploadResponse |
| GET | /articles/images/{project_id}/{filename} | — | StreamingResponse (image bytes) |
| DELETE | /articles/images/{image_id} | — | 204 |
| GET | /articles/{article_id}/images | — | list[ImageInfo] |

### POST /articles/images/upload

Request (multipart/form-data):

| Field | Type | Required |
|-------|------|----------|
| file | UploadFile | да |
| article_id | str (Form) | нет (можно загрузить до привязки к статье) |

Логика:
1. require_auth → user
2. get_default_project → project_id
3. Прочитать file.read() (в memory)
4. StorageService.upload_image(content, filename, content_type, project_id)
5. Создать ArticleImage запись в БД
6. Вернуть { id, url, filename, width, height }

Возвращаемый `url` — это то, что фронт вставит в Markdown: `![filename](url)`

### GET /articles/images/{project_id}/{filename}

Публичный endpoint (без авторизации — изображения в статьях видны всем у кого есть ссылка):
1. StorageService.client.get_object(bucket, key)
2. StreamingResponse с правильным Content-Type
3. Cache-Control: public, max-age=86400

### DELETE /articles/images/{image_id}

Требует авторизации + check_project_access(member):
1. Найти ArticleImage по id
2. StorageService.delete_image(object_key)
3. Удалить запись из БД

### GET /articles/{article_id}/images

Список всех изображений привязанных к статье. Для UI — показать gallery/manage images.

### Регистрация роутера

В `app/main.py`:
```python
from app.routers import article_images
app.include_router(article_images.router)  # Before articles router
```

---

## P6: Frontend — Image Upload в Editor

### Файл: `dashboard-vue/src/services/api.js`

Добавить в articlesApi:

```javascript
uploadImage: (formData) => api.post('/articles/images/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
}),
deleteImage: (imageId) => api.delete(`/articles/images/${imageId}`),
getArticleImages: (articleId) => api.get(`/articles/${articleId}/images`),
```

### Файл: `dashboard-vue/src/views/ArticlesView.vue`

Модифицировать Editor Modal. Над textarea добавить toolbar:

| Кнопка | Действие |
|--------|----------|
| 📎 Upload Image | Открыть file picker, загрузить, вставить `![filename](url)` в cursor position |

### Логика Upload Image

```
1. Клик → открыть <input type="file" accept="image/*">
2. Выбран файл → показать loading на кнопке
3. FormData: { file, article_id (если editing) }
4. POST /articles/images/upload
5. Получить { url, filename }
6. Вставить в textarea на позиции курсора: ![filename](url)\n
7. Убрать loading
```

### Вставка в cursor position

```javascript
function insertAtCursor(textarea, text) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const before = textarea.value.substring(0, start)
    const after = textarea.value.substring(end)
    textarea.value = before + text + after
    // Update v-model
    form.value.content = textarea.value
    // Set cursor after inserted text
    textarea.selectionStart = textarea.selectionEnd = start + text.length
}
```

### Paste из Clipboard (бонус, но ценный)

На textarea повесить @paste handler:

```
1. event.clipboardData.items → найти item с type.startsWith('image/')
2. Если есть → item.getAsFile() → upload → insert markdown
3. Если нет → стандартное поведение paste (текст)
```

Это позволяет Ctrl+V скриншот прямо в editor — очень удобно для bug reports.

### Drag & Drop на textarea (бонус)

На textarea повесить @drop handler:

```
1. event.dataTransfer.files → фильтр по image/*
2. Для каждого файла → upload → insert markdown
```

---

## P7: Frontend — Рендеринг изображений в Viewer

### Файл: `dashboard-vue/src/views/ArticlesView.vue`

Текущий renderedContent computed использует regex для markdown→HTML. Нужно добавить обработку изображений.

Сейчас НЕ обрабатывается:
```markdown
![alt text](/api/articles/images/proj/uuid.png)
```

Добавить regex в renderedContent:

```javascript
// Markdown images: ![alt](url) → <img>
.replace(/!\[([^\]]*)\]\(([^)]+)\)/gim, '<img src="$2" alt="$1" class="article-image" loading="lazy">')
```

### CSS для изображений

```css
.article-content :deep(.article-image) {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    margin: 16px 0;
    cursor: pointer;  /* для lightbox в будущем */
}
```

---

## Порядок выполнения

```
P1 (docker) → P2 (config + deps) → P3 (storage service) → P4 (model + migration) → P5 (endpoints) → P6 (upload UI) → P7 (render)
```

---

## Тесты

### Backend: `backend/tests/test_article_images.py`

| Тест | Assertion |
|------|-----------|
| test_upload_png | POST multipart .png → 200, { id, url, width, height } |
| test_upload_jpeg | POST .jpg → 200 |
| test_upload_webp | POST .webp → 200 |
| test_upload_gif | POST .gif → 200 |
| test_upload_svg | POST .svg → 200 |
| test_upload_returns_markdown_url | url начинается с /api/articles/images/ |
| test_get_image | GET /articles/images/{key} → 200, Content-Type = image/png |
| test_get_image_not_found | GET несуществующий → 404 |
| test_delete_image | DELETE → 204, повторный GET → 404 |
| test_upload_too_large | >10MB → 413 |
| test_upload_wrong_type | .pdf → 400 "Unsupported image format" |
| test_upload_corrupted | Invalid bytes с content_type image/png → 400 "Invalid image file" |
| test_upload_unauthorized | Без токена → 401 |
| test_list_article_images | GET /articles/{id}/images → list |
| test_upload_with_article_id | article_id в form → image.article_id set |
| test_upload_without_article_id | Нет article_id → image создана (orphan) |
| test_image_multi_tenancy | owner1 upload → owner2 не видит в list |
| test_resize_large_image | 4000x3000 px → resized to max 2048 |
| test_none_handling | file=None → 422 |
| test_empty_file | 0 bytes → 400 |
| test_concurrent_upload | 3 upload одновременно → все 200, разные URLs |

### Тестовые fixtures

```python
@pytest.fixture
def sample_png() -> bytes:
    """1x1 red pixel PNG."""
    from PIL import Image
    from io import BytesIO
    img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@pytest.fixture
def large_png() -> bytes:
    """Large image exceeding max dimension."""
    from PIL import Image
    from io import BytesIO
    img = Image.new("RGB", (4000, 3000), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

---

## Диаграмма потоков

### Upload Flow

```
User (Editor) → POST /api/articles/images/upload (multipart)
    → Backend: validate type, size
    → Backend: Pillow validate + resize if > 2048px
    → Backend: StorageService.upload_image() → MinIO PUT object
    → Backend: CREATE ArticleImage record in PostgreSQL
    → Response: { id, url: "/api/articles/images/proj/uuid.png", filename, width, height }
    → Frontend: insert ![filename](url) into textarea
```

### View Flow

```
User opens article → renderedContent parses markdown
    → <img src="/api/articles/images/proj/uuid.png">
    → Browser GET /api/articles/images/proj/uuid.png
    → Nginx proxy → Backend GET → MinIO get_object → StreamingResponse
```

### Paste Screenshot Flow

```
User Ctrl+V в editor textarea
    → @paste handler detects image in clipboard
    → Creates File from clipboard data
    → FormData → POST /api/articles/images/upload
    → Insert markdown into cursor position
```

---

## Запрещено

- Выставлять MinIO порт (9000) наружу для клиентов — только через backend
- Хранить images в PostgreSQL (BYTEA) 
- Хардкодить MinIO credentials — через config/env
- Давать пользователю прямой MinIO URL — всегда через /api/articles/images/
- Файлы > 500 LOC
- Синхронные вызовы к MinIO (boto3 sync OK — он не блокирует event loop надолго для single file ops, но если нужно — обернуть в run_in_executor)

---

## Критерии готовности

| Проверка | Как убедиться |
|----------|--------------|
| MinIO запускается | `docker compose up` → minio healthy, bucket создан |
| MinIO Console | http://localhost:9001 → логин errorlens/errorlens_secret |
| Upload через Swagger | POST /articles/images/upload → 200, файл в MinIO |
| View через browser | GET /api/articles/images/{key} → изображение отображается |
| Upload в editor | Кнопка 📎 → файл загружен → markdown вставлен |
| Paste screenshot | Ctrl+V скриншот в textarea → загружен и вставлен |
| Render в viewer | Открыть статью с `![](url)` → изображение видно |
| Resize | Загрузить 4000x3000 → в MinIO сохранено ≤2048 по большей стороне |
| Delete | DELETE image → файл удалён из MinIO и из БД |
| Все тесты pass | pytest tests/test_article_images.py |
| Обратная совместимость | Существующие тесты не сломаны |

---

## Коммиты

```
[docker] Add MinIO service with auto-init bucket
[backend] Add boto3 + Pillow dependencies
[backend] Add storage service (S3-compatible)
[backend] Add ArticleImage model and migration
[backend] Add image upload/serve/delete endpoints
[frontend] Add image upload button + paste + drag-drop in editor
[frontend] Add image rendering in article viewer
[test] Add article images tests
```

---

## Будущие улучшения (НЕ в этой задаче)

- Thumbnails (resize до 300px для preview в grid)
- Image gallery в editor (показать уже загруженные)
- Orphan cleanup job (удалять images не привязанные к статьям старше 24ч)
- CDN/proxy cache на nginx для images
- Image compression (webp auto-convert)
- Lightbox при клике на изображение в viewer

---

## Время: 5-6 часов
