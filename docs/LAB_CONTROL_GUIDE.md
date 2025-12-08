# Lab Control - Руководство для AI Агентов

> **Версия:** 1.0
> **Сервер:** 192.168.1.74
> **SSH команда:** `ssh -i ~/.ssh/id_ed25519 flomaster@192.168.1.74`

## Основные принципы

Домашний сервер имеет **ограниченные ресурсы**:
- **RAM:** 24GB (загрузка ~60% в idle режиме)
- **CPU:** Ограниченные ресурсы для одновременной работы всех проектов
- **Критично:** При активной работе память быстро упирается в потолок

**ОБЯЗАТЕЛЬНОЕ ПРАВИЛО для агентов:**
- **ПЕРЕД началом работы** — поднять нужное окружение
- **ПОСЛЕ завершения работы** — остановить окружение
- **Если не уверен** — выполнить `lab stop-all` в конце сессии

## Доступные Команды

| Команда | Действие | RAM |
|---------|----------|-----|
| `lab start-warehouse` | Warehouse prod + dev + мониторинг | ~2GB |
| `lab stop-warehouse` | Остановить Warehouse | -1.5GB |
| `lab start-errorlens` | ErrorLens + боты | ~800MB |
| `lab stop-errorlens` | Остановить ErrorLens | -800MB |
| `lab stop-all` | Остановить ВСЁ | -2.5GB |
| `lab status` | Показать состояние | - |

## Порты после запуска

### Warehouse
- API: `http://192.168.1.74:8080`
- UI: `http://192.168.1.74:3000`
- Grafana: `http://192.168.1.74:3001`

### ErrorLens
- Stage API: порты в K8s namespace `errorlens-stage`
- Bots: namespace `bots`

## Типичные Workflow

### Работа над ErrorLens

```bash
# 1. В начале задачи
ssh flomaster@192.168.1.74 'lab start-errorlens'

# 2. Выполнение задачи
# ... работа с ErrorLens ...

# 3. После завершения
ssh flomaster@192.168.1.74 'lab stop-errorlens'
```

### Работа над несколькими проектами

```bash
# Запустить всё нужное
ssh flomaster@192.168.1.74 'lab start-warehouse'
ssh flomaster@192.168.1.74 'lab start-errorlens'

# ... работа ...

# В конце — остановить всё сразу
ssh flomaster@192.168.1.74 'lab stop-all'
```

### Проверка статуса

```bash
ssh flomaster@192.168.1.74 'lab status'
```

## Troubleshooting

### Поды не стартуют

```bash
# 1. Проверить статус подов
ssh flomaster@192.168.1.74 'kubectl get pods -n errorlens-stage'

# 2. Посмотреть детали
ssh flomaster@192.168.1.74 'kubectl describe pod <pod-name> -n errorlens-stage'

# 3. Если не хватает памяти
ssh flomaster@192.168.1.74 'lab stop-all'
ssh flomaster@192.168.1.74 'lab start-errorlens'
```

### Проверка памяти

```bash
ssh flomaster@192.168.1.74 'free -h'
```

**Критические пороги:**
- **< 2GB свободной RAM:** Срочно остановить окружения
- **2-5GB:** Нормально, но запас небольшой
- **> 5GB:** Достаточно места

## Рекомендации для Агентов

### ✅ ДЕЛАТЬ:
- Всегда `lab start-*` перед работой
- Всегда `lab stop-*` после завершения
- Проверять `lab status` перед началом
- Использовать `lab stop-all` если не уверен

### ❌ НЕ ДЕЛАТЬ:
- Не оставлять окружения запущенными
- Не запускать все окружения сразу без необходимости
- Не трогать StatefulSets (базы данных)
- Не останавливать `kube-system`

## K8s Namespaces

| Namespace | Проект | Управление |
|-----------|--------|-----------|
| `errorlens-stage` | ErrorLens staging | `lab start/stop-errorlens` |
| `bots` | Telegram боты | `lab start/stop-errorlens` |
| `warehouse` | Warehouse prod | `lab start/stop-warehouse` |
| `warehouse-dev` | Warehouse dev | `lab start/stop-warehouse` |
| `monitoring` | Grafana, Prometheus | `lab start/stop-warehouse` |

---

**Важно:** Правило "start перед работой, stop после" — обязательное требование для стабильности сервера.
