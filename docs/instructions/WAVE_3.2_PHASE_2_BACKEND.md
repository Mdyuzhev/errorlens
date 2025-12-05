# WAVE 3.2 Phase 2: Backend Services Refactoring

> 🎯 **Приоритет:** P1 High  
> **Оценка:** 6-8 часов  
> **Цель:** Все роутеры используют Service → Repository pattern

---

## Контекст проблемы

Сейчас 8 из 11 роутеров работают напрямую с моделями, обходя Service layer:

| Router | Service | Repo | Статус |
|--------|---------|------|--------|
| sessions.py | ✅ | ✅ | Образец! |
| projects.py | ✅ | ✅ | OK |
| auth.py | ✅ | ✅ | OK |
| articles.py | ❌ | ❌ | Нужен ArticleService |
| tasks.py | ❌ | ❌ | Нужен TaskService |
| testcases.py | ❌ | ⚠️ | Есть repo, нужен Service |
| testruns.py | ❌ | ❌ | Нужен TestRunService |
| tests.py | ❌ | ❌ | Нужен TestService |
| analysis.py | ❌ | — | Нужен AnalysisService |
| exports.py | ⚠️ | — | Частично, доработать |
| integrations.py | ❌ | — | Нужен IntegrationService |

---

## Образцы для копирования

**Перед началом прочитай эти файлы:**

```bash
# Образец роутера
cat backend/app/routers/sessions.py

# Образец сервиса
cat backend/app/services/session_service.py

# Образец репозитория
cat backend/app/repositories/session_repo.py
```

**Паттерн:**
```
Router (thin) → Service (business logic) → Repository (CRUD) → Model
```

---

## Задачи

### 2.1 ArticleService + ArticleRepo

**Создать `backend/app/repositories/article_repo.py`:**

```python
"""Article repository - data access layer."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository[Article]):
    """Repository for Article CRUD operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Article, db)
    
    async def get_by_slug(self, slug: str) -> Optional[Article]:
        """Get article by slug."""
        result = await self.db.execute(
            select(Article).where(Article.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def list_by_category(
        self, 
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[Article]:
        """List articles with filters."""
        query = select(Article).order_by(Article.created_at.desc())
        
        if category:
            query = query.where(Article.category == category)
        if status:
            query = query.where(Article.status == status)
            
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def increment_views(self, article: Article) -> None:
        """Increment article view counter."""
        article.views += 1
        await self.db.commit()
```

**Создать `backend/app/services/article_service.py`:**

```python
"""Article service - business logic layer."""

import re
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Article
from app.repositories.article_repo import ArticleRepository


def slugify(text: str) -> str:
    """Generate URL-friendly slug from title."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text[:200]


class ArticleService:
    """Service for article business logic."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ArticleRepository(db)
    
    async def create_article(
        self,
        title: str,
        content: str,
        author: str,
        excerpt: Optional[str] = None,
        category: Optional[str] = None,
        tags: list[str] = None,
        status: str = "draft"
    ) -> Article:
        """Create new article with unique slug."""
        slug = slugify(title)
        
        # Ensure unique slug
        existing = await self.repo.get_by_slug(slug)
        if existing:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M')}"
        
        article = Article(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt or content[:200],
            category=category,
            tags=tags or [],
            status=status,
            author=author,
            published_at=datetime.utcnow() if status == "published" else None,
        )
        
        return await self.repo.create(article)
    
    async def get_article(self, slug: str) -> Optional[Article]:
        """Get article by slug and increment views."""
        article = await self.repo.get_by_slug(slug)
        if article:
            await self.repo.increment_views(article)
        return article
    
    async def list_articles(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """List articles with filters."""
        articles = await self.repo.list_by_category(
            category=category,
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Filter by tag (post-filter for JSON field)
        if tag:
            articles = [a for a in articles if tag in (a.tags or [])]
        
        return [self._to_dict(a) for a in articles]
    
    async def update_article(
        self,
        article_id: str,
        **updates
    ) -> Optional[Article]:
        """Update article fields."""
        article = await self.repo.get(article_id)
        if not article:
            return None
        
        for key, value in updates.items():
            if value is not None:
                setattr(article, key, value)
        
        # Set published_at when publishing
        if updates.get("status") == "published" and not article.published_at:
            article.published_at = datetime.utcnow()
        
        article.updated_at = datetime.utcnow()
        await self.db.commit()
        return article
    
    async def delete_article(self, article_id: str) -> bool:
        """Delete article by ID."""
        return await self.repo.delete(article_id)
    
    def _to_dict(self, article: Article) -> dict:
        """Convert article to response dict."""
        return {
            "id": article.id,
            "title": article.title,
            "slug": article.slug,
            "excerpt": article.excerpt,
            "category": article.category,
            "tags": article.tags,
            "status": article.status,
            "author": article.author,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "views": article.views,
        }
```

**Обновить `backend/app/routers/articles.py`:**

```python
"""Articles/Knowledge base CRUD router - thin controller."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.jwt_auth import require_auth
from app.models.user import User
from app.services.article_service import ArticleService


router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleCreate(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    category: Optional[str] = None
    tags: list[str] = []
    status: str = "draft"


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


@router.get("")
async def list_articles(
    category: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """List articles with filters."""
    service = ArticleService(db)
    return await service.list_articles(
        category=category,
        status=status,
        tag=tag
    )


@router.get("/{slug}")
async def get_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get article by slug (public for published)."""
    service = ArticleService(db)
    article = await service.get_article(slug)
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return service._to_dict(article)


@router.post("")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Create new article."""
    service = ArticleService(db)
    article = await service.create_article(
        title=data.title,
        content=data.content,
        author=user.username,
        excerpt=data.excerpt,
        category=data.category,
        tags=data.tags,
        status=data.status
    )
    return {"id": article.id, "slug": article.slug}


@router.put("/{article_id}")
async def update_article(
    article_id: str,
    data: ArticleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Update article."""
    service = ArticleService(db)
    article = await service.update_article(
        article_id,
        **data.model_dump(exclude_unset=True)
    )
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {"message": "Article updated"}


@router.delete("/{article_id}")
async def delete_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_auth),
):
    """Delete article."""
    service = ArticleService(db)
    deleted = await service.delete_article(article_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return {"message": "Article deleted"}
```

**Тест:**
```bash
cd backend && pytest tests/ -v -k article
```

✅ **Done when:** Articles работают через Service → Repository

---

### 2.2 TaskService + TaskRepo

**По аналогии с ArticleService создать:**

- `backend/app/repositories/task_repo.py`
- `backend/app/services/task_service.py`
- Обновить `backend/app/routers/tasks.py`

**Специфика:**
- Tasks имеют status (todo, in_progress, done)
- Tasks привязаны к session_id (опционально)
- Kanban операции: move between columns

---

### 2.3 TestCaseService

**Репозиторий уже есть:** `backend/app/repositories/testcase_repo.py`

**Создать:** `backend/app/services/testcase_service.py`

**Обновить:** `backend/app/routers/testcases.py`

---

### 2.4 TestRunService + TestRunRepo

**Создать:**
- `backend/app/repositories/testrun_repo.py`
- `backend/app/services/testrun_service.py`

**Обновить:** `backend/app/routers/testruns.py`

---

### 2.5 AnalysisService

**Вынести логику из:** `backend/app/analyzer.py` и `backend/app/session_analyzer.py`

**Создать:** `backend/app/services/analysis_service.py`

**Обновить:** `backend/app/routers/analysis.py`

---

### 2.6 Финальная проверка

```bash
# Запустить все тесты
cd backend && pytest tests/ -v

# Проверить что нет прямых импортов моделей в роутерах
grep -r "from app.models.db_models import" backend/app/routers/
# Должно быть пусто (кроме User для auth)
```

---

## Definition of Done

- [ ] ArticleService + ArticleRepo созданы
- [ ] TaskService + TaskRepo созданы
- [ ] TestCaseService создан (repo уже есть)
- [ ] TestRunService + TestRunRepo созданы
- [ ] AnalysisService создан
- [ ] Все роутеры используют сервисы
- [ ] Тесты проходят
- [ ] Нет прямых импортов моделей в роутерах

---

## Commit

```bash
git add .
git commit -m "[Wave 3.2] Backend: implement Service layer for all routers

- Add ArticleService, TaskService, TestCaseService
- Add TestRunService, AnalysisService
- Refactor routers to use services
- Follow Router → Service → Repository pattern"

git push origin feature/wave-3
```

---

## Следующий шаг

После завершения Phase 2 → переходим к **Phase 3: Frontend Split**

Прочитай `docs/instructions/WAVE_3.2_PHASE_3_FRONTEND.md`
