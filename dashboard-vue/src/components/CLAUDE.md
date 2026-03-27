# components/ — правила работы с Vue-компонентами

## Организация по доменам

Компоненты организованы по доменным папкам. При создании нового компонента —
помещать в соответствующую папку, не в `common/`.

| Папка | Что хранит |
|-------|-----------|
| `qa/` | QATree, QATestCaseViewer, StepsEditor, QAPlans, QARuns, QADashboard |
| `tasks/` | TaskViewer, TaskDetailView, JQLBar, TaskFilterPanel, TaskActivityFeed |
| `articles/` | ArticleViewer, GridEditor, FolderTree, CalloutBlock, CodeBlock, ExpandBlock |
| `issues/` | IssueDetailView, BacklogView, AttachmentsBlock, WorkLogBlock |
| `common/` | RichEditor, AppIcon, Navbar, Toasts, EditorToolbar (переиспользуемые везде) |

## CSS-переменные — строго обязательно

Все цвета только через CSS-переменные. Хардкод hex-значений — запрещён.

```css
/* ✅ правильно */
.my-component { background: var(--bg-card); color: var(--text-primary); }

/* ❌ запрещено */
.my-component { background: #16152a; color: #e8e6f0; }
```

Ключевые переменные: `--bg-primary`, `--bg-secondary`, `--bg-card`, `--bg-tertiary`,
`--text-primary`, `--text-secondary`, `--accent`, `--accent-muted`, `--border-color`,
`--shadow-dropdown`. Обе темы (dark/light) определены в `style.css`.

## Паттерн Viewer/Editor split

Все разделы с контентом используют разделение: read-only viewer (fullscreen, position: fixed)
отдельно от editor. Viewer открывается по клику строки, кнопка Edit переключает в editor.
Не смешивать режимы просмотра и редактирования в одном компоненте.

## TipTap JSON

Rich-content передаётся как объект `{type:"doc",content:[...]}`.
Никакого HTML или Markdown внутри компонентов — только TipTap JSON.
GridEditor использует формат `{version:"grid-1",rows:[...]}`.

## Emit > Props drilling

Если нужно передать событие через несколько уровней — использовать emit вверх
или Pinia store, не прокидывать props через промежуточные компоненты.

## Store actions для API-вызовов

Компонент не вызывает `api.js` напрямую — только через action Pinia store.

## Известные нарушения

Все ранее известные нарушения исправлены. Следовать правилам в `dashboard-vue/CLAUDE.md`.

## Запрещено

- Хардкод hex-цветов и пиксельных значений вне CSS-переменных
- Прямые вызовы `api.js` из компонента (только через store)
- Смешивание viewer/editor режимов в одном компоненте
- Компоненты >500 строк (разбивать на подкомпоненты)
