#!/usr/bin/env bash
# Persist synchronized catalog without losing newer source-code or data pushes.
# If another job/developer pushed in parallel, re-read current main and re-sync.
set -euo pipefail

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'

for attempt in 1 2 3; do
  # Review records contain no raw PDFs, image data, or credentials.
  for file in data/telde_pdf_pilot/pending_review.json data/telde_pdf_pilot/vision_cache.json data/telde_pdf_pilot/scan_state.json data/telde_pdf_pilot/auto_report.json data/telde_pdf_pilot/verified_events.json; do
    if [[ -f "$file" ]]; then git add "$file"; fi
  done
  git add data/events.sqlite data/program_review_gc.json data/venue_review_gc.json data/source_quality_gc.json data/price_provenance_audit.json public/events.json public/meta.json public/municipal_programs.json
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
  python scripts/audit_source_health_gc.py
  python scripts/audit_price_provenance.py --output data/price_provenance_audit.json
done
