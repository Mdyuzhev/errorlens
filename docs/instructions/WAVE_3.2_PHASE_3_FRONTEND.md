# WAVE 3.2 Phase 3: Frontend Component Split

> 🎯 **Приоритет:** P2 Medium  
> **Оценка:** 3-4 часа  
> **Цель:** Нет компонентов >500 LOC

---

## Контекст проблемы

Два Vue компонента переросли оптимальный размер:

| Component | LOC | Проблема |
|-----------|-----|----------|
| DashboardView.vue | 687 | Слишком много ответственностей |
| ResultsView.vue | 521 | На грани, можно разбить |

---

## Задачи

### 3.1 Split DashboardView.vue

**Текущая структура (687 LOC):**
- Список сессий (table)
- Фильтры и поиск
- Modal с деталями сессии
- Кнопки действий
- Статистика

**Целевая структура:**

```
dashboard-vue/src/
├── views/
│   └── DashboardView.vue           # ~120 LOC (container only)
└── components/
    └── dashboard/
        ├── SessionsTable.vue       # ~180 LOC (table + pagination)
        ├── SessionFilters.vue      # ~80 LOC (search, filters)
        ├── SessionDetailModal.vue  # ~200 LOC (modal content)
        └── SessionActions.vue      # ~100 LOC (action buttons)
```

**Шаги:**

1. Создать папку `components/dashboard/`

2. Вынести `SessionsTable.vue`:
   - Template: таблица сессий
   - Props: `sessions`, `loading`
   - Emits: `select`, `delete`, `quick-test`

3. Вынести `SessionFilters.vue`:
   - Template: поиск, фильтры по типу
   - Props: `modelValue` (текущие фильтры)
   - Emits: `update:modelValue`

4. Вынести `SessionDetailModal.vue`:
   - Template: модальное окно с деталями
   - Props: `session`, `visible`
   - Emits: `close`, `export`, `run-test`

5. Вынести `SessionActions.vue`:
   - Template: grid кнопок
   - Props: `session`, `loading`
   - Emits: действия

6. Обновить `DashboardView.vue`:
   - Импорт компонентов
   - Оставить только state и orchestration

**Пример DashboardView.vue после рефакторинга:**

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { useSessionsStore } from '@/stores/sessions'
import SessionsTable from '@/components/dashboard/SessionsTable.vue'
import SessionFilters from '@/components/dashboard/SessionFilters.vue'
import SessionDetailModal from '@/components/dashboard/SessionDetailModal.vue'

const sessionsStore = useSessionsStore()
const filters = ref({ search: '', type: 'all' })
const selectedSession = ref(null)
const showModal = ref(false)

onMounted(() => {
  sessionsStore.fetchSessions()
})

function handleSelect(session) {
  selectedSession.value = session
  showModal.value = true
}
</script>

<template>
  <div class="dashboard">
    <h1>Sessions</h1>
    
    <SessionFilters v-model="filters" />
    
    <SessionsTable
      :sessions="sessionsStore.filteredSessions(filters)"
      :loading="sessionsStore.loading"
      @select="handleSelect"
      @delete="sessionsStore.deleteSession"
    />
    
    <SessionDetailModal
      v-if="showModal"
      :session="selectedSession"
      @close="showModal = false"
    />
  </div>
</template>
```

✅ **Done when:** DashboardView.vue ≤150 LOC, все компоненты работают

---

### 3.2 Split ResultsView.vue

**Текущая структура (521 LOC):**
- Результаты анализа
- Генерация тестов
- Экспорт
- Timeline событий

**Целевая структура:**

```
components/
└── results/
    ├── AnalysisPanel.vue      # ~150 LOC (AI analysis display)
    ├── EventsTimeline.vue     # ~120 LOC (console logs, network)
    ├── TestGenerator.vue      # ~150 LOC (export buttons)
    └── ExportActions.vue      # ~80 LOC (download buttons)
```

**Принцип разделения:**
- Один компонент = одна ответственность
- Props down, Events up
- Логика в родителе или store

---

### 3.3 Тестирование

После split проверить:

```bash
cd dashboard-vue
npm run dev
```

- [ ] Dashboard загружается
- [ ] Список сессий отображается
- [ ] Фильтры работают
- [ ] Модальное окно открывается
- [ ] Все кнопки работают
- [ ] Нет ошибок в console

---

## Definition of Done

- [ ] DashboardView.vue ≤150 LOC
- [ ] ResultsView.vue ≤300 LOC
- [ ] Новые компоненты в `components/dashboard/` и `components/results/`
- [ ] Все функции работают как раньше
- [ ] Нет ошибок в консоли

---

## Commit

```bash
git add .
git commit -m "[Wave 3.2] Frontend: split large Vue components

- Extract SessionsTable, SessionFilters, SessionDetailModal from DashboardView
- Extract AnalysisPanel, EventsTimeline from ResultsView
- Each component now <300 LOC
- No functional changes"

git push origin feature/wave-3
```

---

## Следующий шаг

После завершения Phase 3 → переходим к **Phase 4: Tests & Docs**

Прочитай `docs/instructions/WAVE_3.2_PHASE_4_TESTS.md`
