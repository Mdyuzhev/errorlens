# WAVE 3.2 Phase 1: Bookmarklet Refactoring

> 🎯 **Приоритет:** P0 Critical  
> **Оценка:** 4-6 часов  
> **Цель:** Один source of truth — модульная структура `src/`

---

## Контекст проблемы

У нас есть **дублирование кода**:

```
bookmarklet/
├── recorder.js          # 2438 LOC — LEGACY, используется в production!
├── recorder.dev.js      # 1019 LOC — dev версия legacy
├── recorder.min.js      # 281 LOC — minified legacy
│
└── src/                 # НОВАЯ структура — НЕ используется!
    ├── index.js         # 43 LOC
    ├── core/            # config, state, api
    ├── interceptors/    # console, fetch, xhr, errors
    ├── ui/              # widget, styles
    └── utils/           # helpers
```

**Проблема:** Production использует монолит `recorder.js`, а модульная `src/` простаивает.

---

## Задачи

### 1.1 Setup esbuild

**Цель:** Настроить сборку `src/` → `dist/`

```bash
cd bookmarklet
npm init -y  # если нет package.json с dependencies
npm install --save-dev esbuild
```

**Создать `esbuild.config.js`:**

```javascript
const esbuild = require('esbuild');

const isWatch = process.argv.includes('--watch');
const isMinify = process.argv.includes('--minify');

const config = {
  entryPoints: ['src/index.js'],
  bundle: true,
  format: 'iife',
  globalName: 'ErrorLens',
  outfile: isMinify ? 'dist/recorder.min.js' : 'dist/recorder.js',
  minify: isMinify,
  sourcemap: !isMinify,
  target: ['es2020'],
  banner: {
    js: `/* ErrorLens Bookmarklet v1.0.0 - ${new Date().toISOString().split('T')[0]} */`
  }
};

if (isWatch) {
  esbuild.context(config).then(ctx => {
    ctx.watch();
    console.log('Watching for changes...');
  });
} else {
  esbuild.build(config).then(() => {
    console.log(`Built: ${config.outfile}`);
  });
}
```

**Добавить в `package.json`:**

```json
{
  "scripts": {
    "build": "node esbuild.config.js",
    "build:min": "node esbuild.config.js --minify",
    "watch": "node esbuild.config.js --watch",
    "build:all": "npm run build && npm run build:min"
  }
}
```

**Проверка:**
```bash
npm run build:all
ls -la dist/
```

✅ **Done when:** `dist/recorder.js` и `dist/recorder.min.js` созданы

---

### 1.2 Анализ функций legacy vs src/

**Цель:** Убедиться что `src/` содержит всё из legacy

**Выполнить:**
```bash
# Извлечь имена функций из legacy
grep -oE "function [a-zA-Z_][a-zA-Z0-9_]*" bookmarklet/recorder.js | sort -u > /tmp/legacy_functions.txt

# Извлечь имена функций из src/
grep -rE "function [a-zA-Z_][a-zA-Z0-9_]*|export (function|const) [a-zA-Z_]+" bookmarklet/src/ | sort -u > /tmp/src_functions.txt

# Сравнить
diff /tmp/legacy_functions.txt /tmp/src_functions.txt
```

**Критические функции (проверить вручную):**

| Функция | Legacy | src/ | Статус |
|---------|--------|------|--------|
| `init()` | ✅ | ? | |
| `createWidget()` | ✅ | ? | |
| `startRecording()` | ✅ | ? | |
| `stopRecording()` | ✅ | ? | |
| `interceptConsole()` | ✅ | ? | |
| `interceptFetch()` | ✅ | ? | |
| `interceptXHR()` | ✅ | ? | |
| `loadHtml2Canvas()` | ✅ | ? | |
| `showResult()` | ✅ | ? | |
| `sendToBackend()` | ✅ | ? | |

**Если чего-то нет в src/:**
1. Перенести из legacy
2. Адаптировать под модульную структуру
3. Добавить export

✅ **Done when:** Все критические функции есть в `src/`

---

### 1.3 Функциональное тестирование

**Цель:** Убедиться что собранный bundle работает как legacy

**Тестовый сценарий:**

1. Открыть https://errorlens-production.up.railway.app
2. Залогиниться: demo / ErrorLenseTest
3. Открыть новую вкладку с тестовым сайтом (например httpbin.org)
4. В DevTools Console выполнить собранный `dist/recorder.js`
5. Проверить:
   - [ ] Виджет появился
   - [ ] Запись стартует по клику
   - [ ] Console logs перехватываются
   - [ ] Fetch/XHR перехватываются
   - [ ] Скриншот делается
   - [ ] Данные отправляются на backend
   - [ ] Результат показывается

**Если что-то не работает:**
1. Проверить console на ошибки
2. Сравнить с поведением legacy
3. Исправить в `src/`
4. Пересобрать

✅ **Done when:** Все чекбоксы пройдены

---

### 1.4 Замена production файлов

**Цель:** Заменить legacy на bundled версию

```bash
cd bookmarklet

# Бэкап (на всякий случай)
cp recorder.js recorder.legacy.backup.js

# Замена
cp dist/recorder.js recorder.js
cp dist/recorder.min.js recorder.min.js

# Удалить dev версию
rm recorder.dev.js
```

**Обновить `.gitignore`:**
```
# Bookmarklet build artifacts
bookmarklet/dist/
bookmarklet/*.legacy.backup.js
```

✅ **Done when:** `recorder.js` это bundled версия из `src/`

---

### 1.5 Cleanup & Commit

**Удалить лишнее:**
```bash
rm -f bookmarklet/recorder.js.backup
rm -f bookmarklet/recorder.legacy.backup.js  # после проверки в prod
```

**Финальная структура:**
```
bookmarklet/
├── src/                 # Исходники (модульные)
│   ├── index.js
│   ├── core/
│   ├── interceptors/
│   ├── ui/
│   └── utils/
├── dist/                # Build output (в .gitignore)
│   ├── recorder.js
│   └── recorder.min.js
├── recorder.js          # Копия dist/recorder.js для production
├── recorder.min.js      # Копия dist/recorder.min.js
├── esbuild.config.js    # Build config
├── package.json
└── README.md
```

**Commit:**
```bash
git add .
git commit -m "[Wave 3.2] Bookmarklet: migrate from monolith to ES modules

- Setup esbuild for bundling src/ to dist/
- Verify feature parity with legacy
- Replace production files with bundled versions
- Clean up legacy files"

git push origin feature/wave-3
```

✅ **Done when:** PR создан, CI проходит

---

## Definition of Done

- [ ] esbuild настроен и работает
- [ ] Все функции перенесены в `src/`
- [ ] Bundled версия работает идентично legacy
- [ ] Legacy файлы удалены
- [ ] Код закоммичен и запушен
- [ ] CI проходит

---

## Troubleshooting

**esbuild не находит модули:**
```javascript
// Проверить что все import/export корректны
// src/index.js должен импортировать всё нужное
```

**Виджет не появляется:**
```javascript
// Проверить что IIFE выполняется
// В конце src/index.js должен быть вызов init() или createWidget()
```

**html2canvas не загружается:**
```javascript
// Проверить loadHtml2Canvas() — должен динамически подгружать скрипт
// Возможно нужно добавить в src/utils/ отдельный модуль
```

---

## Следующий шаг

После завершения Phase 1 → переходим к **Phase 2: Backend Services**

Прочитай `docs/instructions/WAVE_3.2_PHASE_2_BACKEND.md`
