#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROJECT_DIR:-$HOME/dating_bot}"
REPO_URL="${REPO_URL:-}"

if [[ -z "$REPO_URL" && ! -f "$PROJECT_DIR/docker-compose.prod.yml" ]]; then
  echo "Set REPO_URL to your git repository URL or upload the project to $PROJECT_DIR first." >&2
  exit 2
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl git ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi

sudo usermod -aG docker "$USER" || true

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow OpenSSH
  sudo ufw --force enable
fi

if [[ ! -d "$PROJECT_DIR/.git" && -n "$REPO_URL" ]]; then
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

if [[ ! -f .env ]]; then
  cp .env.prod.example .env
  POSTGRES_PASSWORD="$(openssl rand -hex 24)"
  sed -i "s/replace-with-long-random-password/$POSTGRES_PASSWORD/g" .env
  echo "Created $PROJECT_DIR/.env"
  echo "Edit BOT_TOKEN and ADMINS before starting the bot:"
  echo "  nano $PROJECT_DIR/.env"
  exit 0
fi

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f bot
