# Smoke Tests — GitLab CE Setup

| Проверка | Как проверить | Ожидаемый результат |
|---------|--------------|---------------------|
| GitLab открывается | `curl -s http://localhost:8080/-/health` | `{"status":"ok"}` |
| Авторизация работает | Открыть в браузере, войти root / ErrorLens2024! | Успешный вход |
| API токен работает | `curl -H "PRIVATE-TOKEN: $TOKEN" http://localhost:8080/api/v4/user` | JSON с данными root |
| Группа создана | `curl -H "PRIVATE-TOKEN: $TOKEN" http://localhost:8080/api/v4/groups/qa-team` | 200, name: "QA Team" |
| Проект создан | `curl -H "PRIVATE-TOKEN: $TOKEN" http://localhost:8080/api/v4/projects?search=autotest-demo` | 200, один результат |
| Runner зарегистрирован | Открыть `http://localhost:8080/qa-team/-/runners` | Один runner онлайн |
| Runner тег docker | В списке runners | Тег "docker" присвоен |
| Переменные группы | `curl -H "PRIVATE-TOKEN: $TOKEN" http://localhost:8080/api/v4/groups/<id>/variables` | ERRORLENS_URL присутствует |
