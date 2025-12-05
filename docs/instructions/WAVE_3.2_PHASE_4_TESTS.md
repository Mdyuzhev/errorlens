# WAVE 3.2 Phase 4: Tests & Documentation

> 🎯 **Приоритет:** P2 Medium  
> **Оценка:** 2-3 часа  
> **Цель:** Тесты для новых сервисов, актуальная документация

---

## Контекст

После Phase 2 у нас появились новые сервисы, которые нужно покрыть тестами. А также несколько устаревших документов, которые нужно удалить или обновить.

---

## Задачи

### 4.1 Тесты для новых сервисов

**Создать тесты для:**

| Service | Тест файл | Приоритет |
|---------|-----------|-----------|
| ArticleService | test_article_service.py | P1 |
| TaskService | test_task_service.py | P1 |
| SessionService | test_session_service.py | P1 (уже должен быть) |
| TestCaseService | test_testcase_service.py | P2 |

**Шаблон теста сервиса:**

```python
"""Tests for ArticleService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.article_service import ArticleService


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def article_service(mock_db):
    """Create ArticleService with mocked dependencies."""
    return ArticleService(mock_db)


class TestArticleService:
    """Tests for ArticleService."""
    
    @pytest.mark.asyncio
    async def test_create_article_success(self, article_service, mock_db):
        """Test creating article with valid data."""
        # Arrange
        mock_db.execute = AsyncMock(return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        ))
        
        # Act
        result = await article_service.create_article(
            title="Test Article",
            content="Test content",
            author="testuser"
        )
        
        # Assert
        assert result is not None
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_create_article_unique_slug(self, article_service, mock_db):
        """Test that duplicate slugs get timestamp suffix."""
        # Test implementation...
        pass
    
    @pytest.mark.asyncio
    async def test_list_articles_with_filters(self, article_service, mock_db):
        """Test listing articles with category and status filters."""
        pass
    
    @pytest.mark.asyncio
    async def test_delete_article_not_found(self, article_service, mock_db):
        """Test deleting non-existent article returns False."""
        pass
```

**Запуск:**
```bash
cd backend
pytest tests/test_article_service.py -v
pytest tests/ -v --cov=app/services
```

✅ **Done when:** Coverage сервисов >80%

---

### 4.2 Удалить устаревшие документы

**Удалить:**
```bash
rm docs/CODE_AUDIT_REPORT.md    # Заменён на TECHNICAL_AUDIT_2025-12-05.md
rm docs/AUDIT_REPORT.md          # Дубликат
```

**Переименовать:**
```bash
# AGENT_INSTRUCTIONS.md устарел, CLAUDE.md актуален
rm AGENT_INSTRUCTIONS.md  # или оставить как legacy reference
```

---

### 4.3 Обновить ROADMAP.md

**Добавить WAVE 3.2 статус:**

```markdown
## Wave 3.2: Code Refactoring ✅ DONE

- [x] Phase 1: Bookmarklet modularization
- [x] Phase 2: Backend services refactoring
- [x] Phase 3: Frontend component split
- [x] Phase 4: Tests & documentation

**Changes:**
- Bookmarklet: migrated from 2438 LOC monolith to modular ES6 structure
- Backend: all routers now use Service → Repository pattern
- Frontend: no components >500 LOC
- Docs: updated audit, removed obsolete files
```

---

### 4.4 Обновить README.md

Если нужно, обновить секции:
- Architecture (добавить Service layer)
- Development (обновить команды)
- Contributing (ссылка на CLAUDE.md)

---

## Definition of Done

- [ ] Тесты для ArticleService созданы
- [ ] Тесты для TaskService созданы
- [ ] Coverage сервисов >80%
- [ ] CODE_AUDIT_REPORT.md удалён
- [ ] ROADMAP.md обновлён
- [ ] Все тесты проходят

---

## Финальный commit

```bash
git add .
git commit -m "[Wave 3.2] Complete: tests and documentation

- Add tests for ArticleService, TaskService
- Remove obsolete CODE_AUDIT_REPORT.md
- Update ROADMAP.md with Wave 3.2 status
- Update README with new architecture"

git push origin feature/wave-3
```

---

## После Phase 4

**WAVE 3.2 завершён!** 🎉

Создать PR:
```bash
gh pr create --title "[Wave 3.2] Code Refactoring Complete" \
  --body "## Changes

### Bookmarklet
- Migrated from 2438 LOC monolith to modular ES6 structure
- Setup esbuild for bundling

### Backend
- All routers now use Service → Repository pattern
- Added ArticleService, TaskService, TestCaseService, etc.

### Frontend
- Split DashboardView.vue into smaller components
- No components >500 LOC

### Documentation
- New TECHNICAL_AUDIT_2025-12-05.md
- Removed obsolete docs
- Updated ROADMAP.md"
```

---

## Следующие шаги (WAVE 3.3+)

После merge WAVE 3.2:

| Wave | Focus | Priority |
|------|-------|----------|
| 3.3 | DOM Replay (rrweb integration) | High |
| 3.4 | Multi-project UI | Medium |
| 3.5 | Analytics Dashboard | Medium |
| 4.0 | Public Beta Release | High |

Обсудить с шефом приоритеты!
