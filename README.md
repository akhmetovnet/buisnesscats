# Business Cats

Полный стек проекта:
- `backend/` — FastAPI + SQLAlchemy (SQLite)
- `frontend/business-cats-hr/` — React + Vite

В проект добавлена авторизация/регистрация по email:
- `/api/auth/register`
- `/api/auth/email/verify`
- `/api/auth/email/resend`
- `/api/auth/login`
- `/api/auth/refresh`
- `/api/auth/logout`
- `/api/auth/logout-all`
- `/api/auth/password/reset/request`
- `/api/auth/password/reset/confirm`
- `/api/me`

Добавлены платформенные API:
- `/api/me/profile` (GET/PATCH)
- `/api/me/avatar` (POST/DELETE)
- `/api/me/change-password`
- `/api/competencies/summary`
- `/api/sessions/active`
- `/api/sessions/start`
- `/api/sessions/{id}/continue`
- `/api/sessions/history`
- `/api/sessions/{id}/details`

## 1) Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Примечания:
- Email в dev: `EMAIL_PROVIDER=console` (ссылка пишется в лог и возвращается в API в `devEmailPreviewUrl`).
- В production `NODE_ENV=production`, `COOKIE_SECURE=true`, выставить безопасные `JWT_*_SECRET`.

## 2) Frontend setup

```bash
cd frontend/business-cats-hr
npm install
npm run dev
```

Vite проксирует `/api` и `/uploads` на `http://127.0.0.1:8000`.

## 3) Auth UI routes

- `/login` — вход/регистрация + resend + forgot password
- `/verify-email?token=...` — подтверждение email
- `/reset-password` — запрос reset
- `/reset-password?token=...` — подтверждение нового пароля

Остальные страницы (`/competencies`, `/profile`, `/sessions/history`, `/faq`, `/play/...`) требуют ACTIVE-пользователя.

## 4) Тесты

Backend:
```bash
cd backend
.venv/bin/python -m unittest -v tests/test_auth.py tests/test_platform.py
```

Frontend:
```bash
cd frontend/business-cats-hr
npm run test
```

## 5) Важные детали реализации

- Пароли: `bcrypt` (cost 12)
- Verify/reset токены: одноразовые, хранятся только как SHA-256 hash
- Сессии: HttpOnly cookies (`access` + `refresh`)
- Refresh rotation: старый refresh revoke + `replaced_by_token_id`
- Lockout/rate-limit: login fail + endpoint rate limits
- Audit log: таблица `audit_logs` c `email_hash`
