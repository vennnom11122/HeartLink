# HeartLink Deployment

Chosen fallback deployment target: Railway.

Railway is easier to register than Oracle for many users and can deploy this project from the Dockerfile.
The bot uses polling, so it does not need an inbound HTTP port or a public domain.

Important: Railway's current free option is a trial/credit model, not a permanent free VPS.
Check current conditions before deploying: https://railway.com/pricing

## Railway Path

Railway official docs used by this project:

- Docker/start command config: https://docs.railway.com/reference/config-as-code
- Start command shell wrapper: https://docs.railway.com/guides/start-command
- PostgreSQL service: https://docs.railway.com/databases/postgresql/
- Variables: https://docs.railway.com/develop/variables

## Deploy To Railway

1. Push this project to GitHub.
2. Create a Railway account and a new project.
3. Add a service from the GitHub repo.
4. Add PostgreSQL service.
5. Add Redis service.
6. Open the bot service variables and set values from `.env.railway.example`.
7. Set `BOT_TOKEN` to the real token from BotFather.
8. Set `ADMINS` to your Telegram ID list, for example `[123456789]`.
9. Deploy.

The included `railway.toml` tells Railway to:

```bash
alembic upgrade head && python scripts/seed_cities.py && python -m app.main
```

`DATABASE_URL` from Railway Postgres can be `postgresql://...`; HeartLink normalizes it to `postgresql+asyncpg://...` automatically.

## Railway CLI Option

If you use Railway CLI:

```bash
railway login
railway init
railway up
```

Then create Postgres/Redis from the Railway dashboard and add variables from `.env.railway.example`.

## VPS Option

If Railway does not work for you either, use any Ubuntu VPS with Docker Compose. The project still includes:

- `docker-compose.prod.yml`
- `deploy/ubuntu_vps_bootstrap.sh`
- `deploy/deploy_to_vps.ps1`

That path runs PostgreSQL, Redis, and HeartLink on the same VPS.

## Useful Server Commands

```bash
cd ~/dating_bot
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f bot
docker compose -f docker-compose.prod.yml restart bot
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Backups

Create a PostgreSQL dump:

```bash
cd ~/dating_bot
docker compose -f docker-compose.prod.yml exec postgres pg_dump -U dating dating_bot > backup.sql
```

Restore:

```bash
cd ~/dating_bot
cat backup.sql | docker compose -f docker-compose.prod.yml exec -T postgres psql -U dating dating_bot
```
