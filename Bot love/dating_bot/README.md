# HeartLink Telegram Dating Bot 18+

HeartLink — Telegram-бот знакомств 18+ на Python 3.11+, aiogram 3, PostgreSQL, SQLAlchemy 2, Alembic, Redis и Docker.

## Что реализовано

- брендированный первый вход HeartLink;
- подтверждение 18+ перед созданием анкеты;
- короткая пошаговая FSM-регистрация: имя, возраст, пол, кого ищет, город, описание, фото;
- города России с населением от 300 000 человек в seed-скрипте;
- загрузка 1-6 фото, первое фото главное, статус модерации `pending/approved/rejected`;
- управление фото: добавить, удалить, назначить главное;
- поиск анкет с учётом города, возраста, пола, предпочтений, блокировок, просмотров, оценок, банов, скрытия и фото;
- правило показа рейтинга: `rating_count < 5 OR rating_avg >= 5`;
- оценки 1-10 с обновлением существующей оценки;
- оценки 7-10 создают симпатию, взаимные симпатии создают match;
- если оценку снизили ниже 7, симпатия от этой оценки удаляется, а match деактивируется при отсутствии другой взаимной симпатии;
- валентинки, анонимные валентинки, принятие, отклонение, TTL 7 дней;
- жалобы, авто-скрытие анкеты после порога жалоб;
- блокировки между анкетами;
- настройки поиска;
- админ-команды: `/admin`, `/stats`, `/moderation`, `/ban`, `/unban`, `/broadcast`;
- Docker, Alembic, Redis FSM storage, APScheduler для архивации валентинок;
- примеры pytest-тестов сервисов.

## Архитектура

```text
app/
  bot/
    handlers/       # Telegram-команды и callback-сценарии
    keyboards/      # inline/reply клавиатуры
    middlewares/    # DB session, auth/upsert, throttling
    states/         # FSM-состояния
    filters/        # admin/moderator filters
  db/
    models.py       # SQLAlchemy-модели
    session.py      # async engine/session factory
    repositories/   # частые DB-запросы
  services/         # бизнес-логика
  utils/            # валидация, фильтры текста, логирование
migrations/         # Alembic
scripts/            # seed городов
tests/              # pytest
```

## База данных

Главные таблицы:

- `users` — Telegram-пользователь, роли, бан, premium-флаги.
- `profiles` — анкета, возраст 18-99, город, описание, рейтинг.
- `photos` — фото анкеты и модерация.
- `cities` — города 300k+.
- `profile_views` — история показов.
- `ratings` — оценка 1-10, уникальная пара `from_profile_id/to_profile_id`.
- `likes`, `matches` — симпатии и взаимности.
- `valentines` — валентинки.
- `complaints`, `blocks` — безопасность и модерация.
- `daily_limits` — дневные лимиты действий.
- `search_settings` — настройки поиска.
- `conversations`, `messages` — опциональное общение через бота после match.
- `audit_logs` — бизнес-события.

## Локальный запуск через Docker

1. Создай `.env`:

```bash
cp .env.example .env
```

2. Укажи `BOT_TOKEN` и свой Telegram ID в `ADMINS`.

Не коммить реальные токены. Если токен случайно попал в историю или публичный файл, перевыпусти его через BotFather.

3. Запусти:

```bash
docker compose up --build
```

Контейнер `bot` применит миграции, заполнит города и запустит polling.

## Локальный запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_cities.py
python -m app.main
```

Для локального PostgreSQL в `.env` поставь:

```env
DATABASE_URL=postgresql+asyncpg://dating:dating@localhost:5432/dating_bot
REDIS_URL=redis://localhost:6379/0
```

## Тесты

```bash
pytest
```

Тесты используют SQLite in-memory и проверяют сервисную логику без Telegram API.

## Деплой на VPS

Выбранный запасной вариант деплоя после Oracle: Railway.
Подробная инструкция лежит в `DEPLOYMENT.md`.

1. Установи Docker и Docker Compose plugin.
2. Склонируй репозиторий на сервер.
3. Создай `.env` с production-токеном и админами.
4. Закрой наружу PostgreSQL/Redis или оставь порты только на localhost.
5. Запусти:

```bash
docker compose up -d --build
```

6. Проверь логи:

```bash
docker compose logs -f bot
```

Для production лучше добавить reverse SSH/CI деплой, регулярный backup PostgreSQL, мониторинг контейнера и отдельный managed Redis/Postgres при росте нагрузки.

## Важные бизнес-правила

- пользователь младше 18 не допускается;
- анкета без одобренного фото не показывается;
- анкета с `rating_count >= 5` и `rating_avg < 5` не показывается;
- оценка только 1-10;
- одна оценка на пару анкет, повторная оценка обновляет прежнюю;
- 7-10 считается симпатией;
- взаимная симпатия создаёт match;
- валентинка создаёт match при принятии;
- заблокированные, забаненные и скрытые анкеты не показываются;
- пользователь не видит самого себя;
- username раскрывается только после match;
- жалобы уходят модераторам, порог жалоб скрывает анкету автоматически.

## Seed городов

`scripts/seed_cities.py` содержит 65 городов с населением от 300 000 человек по оценке Росстата на 01.01.2025. Список сверялся с:

- https://www.russiametrics.ru/cities
- https://www.mojgorod.ru/cities/pop2025_1.html
- https://www.mojgorod.ru/cities/pop2025_2.html
- https://www.mojgorod.ru/cities/pop2025_3.html

Города из исходного примера, которые сейчас ниже 300 000, в seed не добавлены.
