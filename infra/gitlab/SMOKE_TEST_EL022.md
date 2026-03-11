# EL022: Smoke Test Checklist

## Предусловия

- GitLab запущен (EL021): `http://localhost:8080`
- Runner зарегистрирован и активен
- `.env` заполнен: `GITLAB_ROOT_TOKEN`, `GITLAB_PROJECT_ID`
- `populate_project.sh` выполнен успешно

## Проверки

| # | Проверка | Действие | Ожидаемый результат |
|---|---------|---------|---------------------|
| 1 | Файлы в репозитории | Открыть `http://localhost:8080/qa-team/autotest-demo` | Все файлы видны в дереве |
| 2 | Ручной запуск пайплайна | CI/CD → Pipelines → Run pipeline (branch: main) | Pipeline запустился |
| 3 | Тесты прошли | Дождаться завершения job `run_tests` | 15+ passed, 3-4 failed (ожидаемо) |
| 4 | Артефакт создан | Скачать артефакт `allure-results/` | ZIP содержит JSON файлы |
| 5 | Upload в ErrorLens | Дождаться job `upload_to_errorlens` | Job завершился успешно (exit 0) |
| 6 | Launch в ErrorLens | Открыть ErrorLens → Results | Новый Launch с именем `autotest-demo / main` |
| 7 | Тесты видны | Открыть Launch | ~20 тестов, разные статусы |
| 8 | Flaky отображается | Открыть аналитику | `test_user_list_pagination` в таблице Flaky |
| 9 | Вложение открывается | Открыть `test_get_product_list` → вложения | PNG отображается |

## Намеренно падающие тесты (3 шт.)

| Тест | Ошибка | Цель |
|------|--------|------|
| `test_login_with_wrong_password` | `Expected 999, got 200` | Демо категоризации дефектов |
| `test_product_out_of_stock` | `stock count mismatch: expected 0, got 5` | Демо разных сообщений об ошибках |
| `test_checkout_with_invalid_card` | `Expected validation error, got 200` | Демо BLOCKER severity |

## Flaky тест (1 шт.)

| Тест | Частота падений | Цель |
|------|----------------|------|
| `test_user_list_pagination` | ~40% | Демо таблицы Flaky Tests |
