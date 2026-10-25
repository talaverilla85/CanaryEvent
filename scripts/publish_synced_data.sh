#!/usr/bin/env bash
# Persist synchronized catalog without losing newer source-code or data pushes.
# If another job/developer pushed in parallel, re-read current main and re-sync.
set -euo pipefail

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'

for attempt in 1 2 3; do
  git add data/events.sqlite public/events.json public/meta.json public/municipal_programs.json
  if git diff --cached --quiet; then
    echo "Sin cambios para guardar"
    exit 0
  fi

  git commit -m "data: actualizar eventos y estado de fuentes [skip ci]"
  if git push origin HEAD:main; then
    echo "Catálogo sincronizado y publicado (intento $attempt)"
    exit 0
  fi

  if [[ "$attempt" -eq 3 ]]; then
    echo "Error: la rama principal volvió a cambiar; no se han sobrescrito cambios remotos" >&2
    exit 1
  fi

  echo "Otra publicación actualizó main; recuperando el catálogo más reciente (intento $attempt/3)"
  # Discard only ephemeral work on this fresh checkout; generated data will be
  # rebuilt from the newest published SQLite. Never force-push over others.
  git fetch --no-tags origin main
  git reset --hard origin/main
  python -m unittest discover -s tests -q
  python scripts/sync_events.py
done
