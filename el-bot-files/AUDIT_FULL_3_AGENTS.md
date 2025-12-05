# 🔍 AGENT TASK: Full Project Audit (3 Parallel Agents)

## Контекст агента

```json
{
  "permissions": {
    "allow": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch", "Task", "TodoWrite", "NotebookEdit"]
  },
  "preferences": {
    "language": "russian",
    "communication_style": "friendly_professional",
    "naming": {
      "claude_opus": "шеф",
      "claude_code": "коллега",
      "reference": "Следствие ведут Колобки"
    },
    "humor": {
      "enabled": true,
      "style": "добрый сарказм, айтишные шутки",
      "when": "в начале задачи, при успехе, при ошибках"
    },
    "formatting": {
      "emoji": true,
      "tables": true,
      "tree_diagrams": true,
      "code_comments": "на английском",
      "commits": "[Audit] description in English"
    }
  },
  "memory": {
    "project": "ErrorLens - AI-powered QA platform с bookmarklet записью сессий",
    "stack": {
      "backend": "Python/FastAPI + PostgreSQL + Alembic + SQLAlchemy",
      "frontend": "Vue 3 + Vite dashboard",
      "bookmarklet": "Vanilla JS IIFE",
      "llm": "Groq (primary) + Gemini (fallback)",
      "integrations": "TestIt, YouGile"
    },
    "hosting": {
      "production": "Railway (errorlens-production.up.railway.app)",
      "repo": "github.com/Mdyuzhev/errorlens (private)"
    }
  },
  "github": {
    "token": "${GITHUB_TOKEN}",
    "repo": "Mdyuzhev/errorlens"
  }
}
```

---

## 🎯 Общая задача

Провести **полный аудит** проекта ErrorLens силами **3 параллельных агентов**.

Каждый агент:
1. Клонирует репо
2. Создаёт свою ветку
3. Проводит аудит своей области
4. Формирует отчёт
5. Создаёт PR

---

## Распределение работы

| Агент | Область | Ветка | Отчёт |
|-------|---------|-------|-------|
| 1 | Backend (API, Services, Auth) | `audit/agent-1-backend` | `TEST_AUDIT_AGENT_1_BACKEND.md` |
| 2 | Database (Models, Migrations) | `audit/agent-2-database` | `TEST_AUDIT_AGENT_2_DATABASE.md` |
| 3 | Frontend (Vue, Bookmarklet) | `audit/agent-3-frontend` | `TEST_AUDIT_AGENT_3_FRONTEND.md` |

---

# 📦 AGENT 1: Backend Audit

## Подготовка

```bash
cd /app/projects
rm -rf errorlens-audit-backend
git clone https://github.com/Mdyuzhev/errorlens.git errorlens-audit-backend
cd errorlens-audit-backend
git checkout -b audit/agent-1-backend
```

## Области аудита

### 1.1 API Endpoints (`src/api/`)
- [ ] Все роуты и HTTP методы
- [ ] Валидация входных данных (Pydantic schemas)
- [ ] Обработка ошибок и HTTP статусы
- [ ] Документация OpenAPI/Swagger

### 1.2 Services (`src/services/`)
- [ ] Бизнес-логика и организация
- [ ] Dependency Injection
- [ ] Обработка исключений
- [ ] Логирование

### 1.3 Repositories (`src/repositories/`)
- [ ] CRUD операции
- [ ] Транзакции
- [ ] Оптимизация запросов

### 1.4 Authentication & Authorization
- [ ] JWT токены
- [ ] Middleware авторизации
- [ ] Защита endpoints

### 1.5 Configuration
- [ ] Переменные окружения
- [ ] CORS настройки
- [ ] Logging

## Формат отчёта Agent 1

Создать `TEST_AUDIT_AGENT_1_BACKEND.md`:

```markdown
# Backend Audit Report

## Summary
- Файлов проверено: X
- Критических проблем: X
- Предупреждений: X

## API Endpoints
| Endpoint | Method | Auth | Issues |
|----------|--------|------|--------|

## Security Findings
### Critical
### Warnings

## Code Quality
### Good Practices
### Improvements Needed

## Recommendations
1. ...

## Agent Info
- Agent: 1/3 (Backend)
- Branch: audit/agent-1-backend
- Date: $(date)
```

## Commit и PR Agent 1

```bash
git add TEST_AUDIT_AGENT_1_BACKEND.md
git commit -m "[Audit] Backend security and code quality audit

🤖 Generated with Claude Code Agent 1/3"
git push -u origin audit/agent-1-backend
gh pr create --title "[Audit] Agent 1: Backend Analysis" --body "Backend audit from Agent 1/3" --base main
```

---

# 📦 AGENT 2: Database Audit

## Подготовка

```bash
cd /app/projects
rm -rf errorlens-audit-database
git clone https://github.com/Mdyuzhev/errorlens.git errorlens-audit-database
cd errorlens-audit-database
git checkout -b audit/agent-2-database
```

## Области аудита

### 2.1 SQLAlchemy Models (`src/models/`)
- [ ] Структура таблиц
- [ ] Связи между моделями
- [ ] Индексы и constraints
- [ ] Nullable поля

### 2.2 Alembic Migrations (`alembic/versions/`)
- [ ] История миграций
- [ ] Корректность up/down
- [ ] Breaking changes

### 2.3 Database Queries
- [ ] N+1 проблемы
- [ ] JOIN vs lazy loading
- [ ] Пагинация

### 2.4 Data Integrity
- [ ] Foreign keys
- [ ] Unique constraints
- [ ] Soft delete

### 2.5 Performance
- [ ] Индексы
- [ ] Connection pooling
- [ ] Query optimization

## Формат отчёта Agent 2

Создать `TEST_AUDIT_AGENT_2_DATABASE.md`:

```markdown
# Database Audit Report

## Summary
- Таблиц: X
- Миграций: X
- Проблем: X

## Schema Overview
(ASCII диаграмма связей таблиц)

## Tables Analysis
| Table | Columns | Indexes | FK | Issues |
|-------|---------|---------|-----|--------|

## Migrations Review
| Version | Description | Status |

## Performance
### Missing Indexes
### N+1 Problems

## Recommendations
1. ...

## Agent Info
- Agent: 2/3 (Database)
- Branch: audit/agent-2-database
- Date: $(date)
```

## Commit и PR Agent 2

```bash
git add TEST_AUDIT_AGENT_2_DATABASE.md
git commit -m "[Audit] Database schema and migrations audit

🤖 Generated with Claude Code Agent 2/3"
git push -u origin audit/agent-2-database
gh pr create --title "[Audit] Agent 2: Database Analysis" --body "Database audit from Agent 2/3" --base main
```

---

# 📦 AGENT 3: Frontend & Bookmarklet Audit

## Подготовка

```bash
cd /app/projects
rm -rf errorlens-audit-frontend
git clone https://github.com/Mdyuzhev/errorlens.git errorlens-audit-frontend
cd errorlens-audit-frontend
git checkout -b audit/agent-3-frontend
```

## Области аудита

### 3.1 Vue Dashboard (`dashboard/`)
- [ ] Компонентная структура
- [ ] State management
- [ ] Роутинг
- [ ] API интеграция

### 3.2 Bookmarklet (`static/recorder.js`)
- [ ] IIFE структура
- [ ] Event listeners
- [ ] DOM манипуляции
- [ ] Отправка данных

### 3.3 UI/UX
- [ ] Responsive design
- [ ] Accessibility
- [ ] Error states
- [ ] Loading states

### 3.4 Security
- [ ] XSS защита
- [ ] Token storage
- [ ] Input sanitization

### 3.5 Performance
- [ ] Bundle size
- [ ] Lazy loading
- [ ] Network requests

### 3.6 Integrations
- [ ] TestIt API
- [ ] YouGile API
- [ ] Groq/Gemini LLM

## Формат отчёта Agent 3

Создать `TEST_AUDIT_AGENT_3_FRONTEND.md`:

```markdown
# Frontend & Bookmarklet Audit Report

## Summary
- Vue компонентов: X
- Bookmarklet LOC: X
- Проблем: X

## Dashboard Structure
(Tree diagram)

## Vue Components
| Component | Props | Events | Issues |

## Bookmarklet Analysis
### Structure
### Data Flow
### Issues

## Security
### XSS Risks
### Token Handling

## Performance
### Bundle Size
### Network

## Integrations
| Integration | Status | Issues |

## Recommendations
1. ...

## Agent Info
- Agent: 3/3 (Frontend)
- Branch: audit/agent-3-frontend
- Date: $(date)
```

## Commit и PR Agent 3

```bash
git add TEST_AUDIT_AGENT_3_FRONTEND.md
git commit -m "[Audit] Frontend and Bookmarklet audit

🤖 Generated with Claude Code Agent 3/3"
git push -u origin audit/agent-3-frontend
gh pr create --title "[Audit] Agent 3: Frontend Analysis" --body "Frontend audit from Agent 3/3" --base main
```

---

# 📨 Уведомления

После завершения каждый агент отправляет:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "'"${TELEGRAM_ADMIN_ID}"'",
    "text": "✅ AGENT X/3 COMPLETED\n\n📋 [Area] Audit\n🌿 Branch: audit/agent-X-[area]\n🔀 PR created"
  }'
```

---

# ✅ Критерии успеха

По завершению должно быть:
- [ ] 3 ветки в репо
- [ ] 3 отчёта (TEST_AUDIT_AGENT_*.md)
- [ ] 3 PR в main
- [ ] 3 уведомления в Telegram
- [ ] Все PR можно смержить без конфликтов
