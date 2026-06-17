#!/usr/bin/env bash
# Regenera el feed y lo publica en GitHub Pages. Pensado para correr por cron.
set -euo pipefail

cd "$(dirname "$0")"

# Carga .env si existe (para ANTHROPIC_API_KEY)
[ -f .env ] && export $(grep -v '^#' .env | xargs)

# Usa el venv si existe
[ -d .venv ] && source .venv/bin/activate

echo "[$(date)] Generando feed..."
python generar_feed.py

# Publica en GitHub Pages solo si el feed cambió
if ! git diff --quiet docs/feed.json; then
  git add docs/feed.json
  git commit -m "feed: actualización $(date +%Y-%m-%d_%H:%M)"
  git push origin main
  echo "[$(date)] Feed publicado."
else
  echo "[$(date)] Sin cambios en el feed."
fi
