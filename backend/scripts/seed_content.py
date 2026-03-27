"""Content builders for seed_demo_v2: grid-1 JSON and TipTap nodes."""

import json
import uuid


def gen_id() -> str:
    return str(uuid.uuid4())


def _make_tiptap_doc(nodes: list[dict]) -> dict:
    return {"type": "doc", "content": nodes}


def _heading(text: str, level: int = 2) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}


def _paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [{"type": "text", "text": text}]}


def _callout(variant: str, text: str) -> dict:
    return {"type": "callout", "attrs": {"variant": variant}, "content": [_paragraph(text)]}


def _code_block(language: str, code: str) -> dict:
    return {"type": "codeBlock", "attrs": {"language": language}, "content": [{"type": "text", "text": code}]}


def _expand(summary: str, text: str) -> dict:
    return {"type": "details", "attrs": {"summary": summary}, "content": [_paragraph(text)]}


def make_grid_content(rows_data: list[list[dict]]) -> str:
    """Build grid-1 JSON string from rows. Each row is a list of nodes."""
    rows = []
    for row_nodes in rows_data:
        columns = []
        for node in row_nodes:
            columns.append({
                "id": gen_id(), "span": 12 // len(row_nodes),
                "content": _make_tiptap_doc([node]),
            })
        rows.append({"id": gen_id(), "columns": columns})
    return json.dumps({"version": "grid-1", "rows": rows}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 5 article content builders
# ---------------------------------------------------------------------------

def content_architecture() -> str:
    return make_grid_content([
        [_heading("Архитектура JWT в ErrorLens", 1)],
        [_callout("info", "JWT-аутентификация использует два токена: access (30 мин) и "
                  "refresh (7 дней). Access-токен передаётся в заголовке Authorization.")],
        [_paragraph("Access-токен подписывается HS256 с секретом из переменной JWT_SECRET."),
         _paragraph("Refresh-токен хранится в httpOnly cookie и ротируется при каждом обновлении.")],
        [_heading("Поток аутентификации", 2)],
        [_paragraph("1. Клиент отправляет credentials на /auth/login. "
                    "2. Сервер проверяет bcrypt-хеш пароля. "
                    "3. При успехе возвращает access_token в body и refresh_token в cookie. "
                    "4. Клиент использует access_token для всех запросов к API.")],
    ])


def content_security() -> str:
    return make_grid_content([
        [_heading("Руководство по безопасности API", 1)],
        [_callout("warning", "Никогда не передавайте JWT-токены в query-параметрах URL. "
                  "Используйте только заголовок Authorization: Bearer <token>.")],
        [_code_block("python",
            "from fastapi import Depends, HTTPException, status\n"
            "from fastapi.security import HTTPBearer\n\n"
            "security = HTTPBearer()\n\n"
            "async def get_current_user(\n"
            "    token: str = Depends(security),\n"
            "    db: AsyncSession = Depends(get_db),\n"
            ") -> User:\n"
            '    payload = jwt.decode(token.credentials, SECRET, algorithms=["HS256"])\n'
            '    user = await db.get(User, payload["sub"])\n'
            "    if not user:\n"
            '        raise HTTPException(status_code=401, detail="Invalid token")\n'
            "    return user")],
        [_paragraph("Все эндпоинты кроме /auth/login и /auth/register защищены middleware. "
                    "Токен проверяется на срок действия, подпись и наличие пользователя в БД.")],
    ])


def content_api_ref() -> str:
    return make_grid_content([
        [_heading("Справочник API: Эндпоинты аутентификации", 1)],
        [_heading("POST /auth/login", 2)],
        [_code_block("json", json.dumps({"email": "user@example.com", "password": "SecureP@ss123"}, indent=2))],
        [_code_block("json", json.dumps(
            {"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 1800}, indent=2))],
        [_callout("danger", "При 5 неудачных попытках входа подряд аккаунт блокируется на 15 минут. "
                  "Это защита от brute-force атак.")],
        [_heading("POST /auth/refresh", 2)],
        [_paragraph("Обновляет access_token используя refresh_token из httpOnly cookie. "
                    "Старый refresh_token инвалидируется, выпускается новая пара.")],
    ])


def content_troubleshoot() -> str:
    return make_grid_content([
        [_heading("Устранение ошибок авторизации", 1)],
        [_expand("401 Unauthorized — Token expired",
                 "Access-токен истёк. Клиент должен вызвать /auth/refresh для получения нового. "
                 "Если refresh-токен тоже истёк — требуется повторный логин.")],
        [_expand("403 Forbidden — Insufficient permissions",
                 "Пользователь аутентифицирован, но не имеет нужной роли. "
                 "Проверьте project_members и роль пользователя (owner/admin/member/viewer).")],
        [_expand("500 Internal Server Error при логине",
                 "Чаще всего вызвано спецсимволами в пароле, которые ломают bcrypt. "
                 "Убедитесь что пароль передаётся в UTF-8 и не содержит null-байтов.")],
        [_code_block("bash",
            "# Проверка JWT-токена вручную\n"
            'curl -s http://localhost:8000/auth/me \\\n'
            '  -H "Authorization: Bearer $TOKEN" | jq .\n\n'
            "# Декодирование payload (без проверки подписи)\n"
            "echo $TOKEN | cut -d. -f2 | base64 -d | jq .")],
    ])


def content_refresh_token() -> str:
    return make_grid_content([
        [_heading("Refresh Token: принцип работы и ротация", 1)],
        [_paragraph("Refresh-токен — это долгоживущий токен (7 дней), который используется "
                    "исключительно для получения новой пары access + refresh токенов. "
                    "Он хранится в httpOnly secure cookie и недоступен из JavaScript.")],
        [_callout("success", "При каждом обновлении выпускается новый refresh-токен, а старый "
                  "инвалидируется. Это реализует ротацию токенов и ограничивает окно уязвимости при утечке.")],
        [_callout("warning", "Если refresh-токен украден и использован атакующим раньше легитимного "
                  "пользователя — при следующем обращении пользователя сервер обнаружит "
                  "повторное использование и инвалидирует всю цепочку (token family).")],
        [_heading("Хранение на сервере", 2)],
        [_paragraph("Каждый refresh-токен хранится в таблице refresh_tokens с полями: "
                    "id, user_id, token_hash, family_id, is_revoked, expires_at, created_at. "
                    "При ротации создаётся новый токен с тем же family_id.")],
    ])
