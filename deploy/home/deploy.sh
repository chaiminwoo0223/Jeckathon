#!/usr/bin/env bash
# Build and (re)start the home server stack from the current checkout.
# Run by the self-hosted runner (.github/workflows/deploy-home.yml) or by hand.
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
env_file="${JECKATHON_ENV_FILE:-$HOME/.config/jeckathon/deploy.env}"

if [[ ! -f "$env_file" ]]; then
  echo "env file not found: $env_file" >&2
  exit 1
fi

compose() {
  docker compose --env-file "$env_file" -f "$root/deploy/home/compose.yml" "$@"
}

echo "deploying $(git -C "$root" rev-parse --short HEAD 2>/dev/null || echo 'working tree')"

compose build
if ! compose up -d --remove-orphans; then
  # Usually a failed migration/seed in prestart; the old backend keeps running.
  compose logs --tail 80 prestart backend >&2
  exit 1
fi

# `up -d` returns before the one-shot prestart finishes; wait for backend health.
for _ in $(seq 1 60); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$(compose ps -q backend)" 2>/dev/null || true)"
  [[ "$status" == "healthy" ]] && break
  sleep 3
done

compose ps -a
if [[ "$status" != "healthy" ]]; then
  echo "backend not healthy (status: ${status:-missing})" >&2
  compose logs --tail 80 prestart backend >&2
  exit 1
fi

# Drop superseded backend images so rebuilds don't fill the disk.
docker image prune -f --filter label=jeckathon.image=backend >/dev/null
echo "backend healthy"
