# dashboard-vue — Правила дизайна и темизации

## Дизайн-система

Все токены определены в `src/style.css` как CSS Custom Properties.

- Dark theme — значения по умолчанию в `:root`
- Light theme — переопределения в `body.theme-light`

Переключение темы: класс `theme-light` на `<body>`. Компоненты **не должны**
знать о текущей теме — только использовать `var(--token)`.

---

## Токены — полный словарь

### Фоны

| Токен | Dark | Light | Назначение |
|-------|------|-------|------------|
| `--bg-primary` | `#0f0a1a` | `#f0f4f8` | Основной фон страницы |
| `--bg-secondary` | `#1a1225` | `#e8edf2` | Сайдбары, инпуты, вложенные области |
| `--bg-card` | `#231a33` | `#ffffff` | Карточки, модальные окна, viewer |
| `--bg-tertiary` | `#2d2040` | `#d8dde6` | Разделители, hover-строки таблиц |

### Текст

| Токен | Dark | Light | Назначение |
|-------|------|-------|------------|
| `--text-primary` | `#f3e8ff` | `#172b4d` | Основной текст |
| `--text-secondary` | `#a78bfa` | `#5e6c84` | Подписи, метаданные, placeholder |

### Акценты

| Токен | Dark | Light | Назначение |
|-------|------|-------|------------|
| `--accent` | `#7c3aed` | `#0052cc` | Кнопки, ссылки, активные элементы |
| `--accent-hover` | `#8b5cf6` | `#0065ff` | Hover-состояние accent |
| `--accent-muted` | `rgba(124,58,237,0.1)` | `rgba(0,82,204,0.08)` | Badge-info, подсветка |
| `--accent-subtle` | `rgba(124,58,237,0.15)` | `rgba(0,82,204,0.14)` | Фоновая подсветка |

### Границы и тени

| Токен | Dark | Light |
|-------|------|-------|
| `--border-color` | `rgba(255,255,255,0.1)` | `#dfe1e6` |
| `--shadow` | `0 4px 24px rgba(0,0,0,0.3)` | `0 1px 3px rgba(0,0,0,0.12)` |
| `--shadow-dropdown` | `0 8px 24px rgba(0,0,0,0.4)` | `0 4px 16px rgba(0,0,0,0.12)` |

### Семантические

| Токен | Dark | Light |
|-------|------|-------|
| `--success` | `#10b981` | `#00875a` |
| `--error` | `#ef4444` | `#de350b` |
| `--warning` | `#f59e0b` | `#ff8b00` |

---

## Запрещено: hardcoded цвета

Нельзя использовать hex/rgb-литералы в `<style>` компонентов. Только `var(--token)`.

```css
/* WRONG */
.panel { background: #16152a; color: #e8e6f0; }

/* RIGHT */
.panel { background: var(--bg-card); color: var(--text-primary); }
```

### Маппинг старых hardcoded значений

| Hardcoded | Заменять на |
|-----------|-------------|
| `#0f0e17`, `#0f0a1a` | `var(--bg-primary)` |
| `#16152a`, `#1a1225` | `var(--bg-secondary)` |
| `#22203a`, `#231a33` | `var(--bg-card)` |
| `#2d2040` | `var(--bg-tertiary)` |
| `#f3e8ff`, `#e8e6f0` | `var(--text-primary)` |
| `#a78bfa` | `var(--text-secondary)` |
| `#7c3aed` | `var(--accent)` |

---

## Chart.js

Chart.js не поддерживает CSS-переменные напрямую. Использовать хелпер:

```js
function getCssVar(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name).trim()
}
```

Для реакции на смену темы — `MutationObserver` на `document.body`:

```js
const observer = new MutationObserver(() => {
  // перечитать getCssVar() и обновить chart.options / chart.data
  chart.update()
})
observer.observe(document.body, {
  attributes: true,
  attributeFilter: ['class']
})
```

---

## Sticky-колонки

В таблицах с горизонтальным скроллом sticky-колонки (`position: sticky; left: 0`)
должны использовать `background: var(--bg-secondary)` чтобы перекрывать контент.

Для light theme добавлять `box-shadow` на правую сторону sticky-колонки:

```css
body.theme-light .sticky-col {
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.08);
}
```

---

## Чеклист нового компонента

- [ ] Все цвета — только `var(--token)`, ни одного hex/rgb литерала
- [ ] Проверить в обеих темах (dark и light)
- [ ] Sticky-колонки — `var(--bg-secondary)` + box-shadow для light
- [ ] Chart.js — `getCssVar()` + MutationObserver
- [ ] Файл < 500 LOC, иначе разбить на подкомпоненты
- [ ] API-вызовы через Pinia store, не напрямую
