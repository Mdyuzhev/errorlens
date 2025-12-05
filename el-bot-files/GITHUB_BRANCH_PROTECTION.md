# GitHub Branch Protection Setup

## Настройка защиты ветки main

Для репозитория `Mdyuzhev/errorlens` нужно настроить защиту ветки `main`:

### Шаги:

1. Перейти в **Settings** → **Branches** → **Add branch protection rule**

2. В поле **Branch name pattern** ввести: `main`

3. Включить следующие настройки:

   - [x] **Require a pull request before merging**
     - [x] Require approvals: 1
     - [ ] Dismiss stale pull request approvals when new commits are pushed

   - [ ] Require status checks to pass before merging
     (Опционально - если есть CI/CD)

   - [x] **Do not allow bypassing the above settings**

4. Нажать **Create** или **Save changes**

### Результат:

После настройки:
- Прямой push в `main` будет запрещён
- Все изменения только через Pull Request
- Claude Agent должен создавать feature branches и PR

### Workflow для агента:

```bash
# 1. Создать новую ветку
git checkout main
git pull origin main
git checkout -b feature/task-name

# 2. Внести изменения
# ... код ...

# 3. Закоммитить
git add -A
git commit -m "feat: description"

# 4. Запушить
git push -u origin feature/task-name

# 5. Создать PR (через gh CLI или GitHub UI)
gh pr create --title "Feature: Task Name" --body "Description" --base main
```

### Примечание

Если нужно экстренно внести изменения напрямую в main:
- Временно отключить protection в Settings → Branches
- Сделать push
- Включить protection обратно
