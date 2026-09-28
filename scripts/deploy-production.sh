#!/usr/bin/env bash
# Called by the VPS deploy poller after CI passes for one repository.
set -euo pipefail

target="${1:-}"
case "$target" in
  backend|frontend) ;;
  *) echo "Usage: deploy-production.sh backend|frontend" >&2; exit 64 ;;
esac

backend_dir=/opt/prisma-app/PRISMA
backup_dir=/opt/prisma-app/backups
cd "$backend_dir"

if [[ ! -f .env.prod ]]; then
  echo "Missing $backend_dir/.env.prod" >&2
  exit 1
fi

compose=(docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.prod.caddy.yml)
"${compose[@]}" config --quiet

if [[ "$target" == backend ]]; then
  # A backup precedes every automated migration. Keep backups outside Git.
  install -d -m 700 "$backup_dir"
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  dump_tmp="$backup_dir/.prisma-$timestamp.dump.tmp"
  trap 'rm -f "$dump_tmp"' EXIT
  docker exec prisma-postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$dump_tmp"
  test -s "$dump_tmp"
  mv "$dump_tmp" "$backup_dir/prisma-$timestamp.dump"
  docker run --rm -v prisma_project-covers:/data:ro -v "$backup_dir":/backup alpine:3.20 \
    tar czf "/backup/project-covers-$timestamp.tgz" -C /data .

  "${compose[@]}" run --rm prisma-migrations
  "${compose[@]}" up -d --no-deps --build prisma-api prisma-worker

  for attempt in {1..30}; do
    if [[ "$(docker inspect -f '{{.State.Health.Status}}' prisma-api)" == healthy ]]; then
      break
    fi
    sleep 2
  done
  if [[ "$(docker inspect -f '{{.State.Health.Status}}' prisma-api)" != healthy ]]; then
    "${compose[@]}" logs --tail=80 prisma-api
    exit 1
  fi
  test "$(docker inspect -f '{{.State.Running}}' prisma-worker)" = true
else
  "${compose[@]}" up -d --no-deps --build prisma-web
  test "$(docker inspect -f '{{.State.Running}}' prisma-web)" = true
fi

"${compose[@]}" ps
