#!/usr/bin/env bash
source "$(dirname -- "$0")/common.sh"
harvey_require_venv
.venv/bin/python --version
scripts/codex --version
.venv/bin/python - <<'PY'
from pathlib import Path
from harvey.config import load_config
cfg = load_config()
print(f'Konfiguration gültig: {cfg.brain.provider} / {cfg.brain.model}')
print(f'Zeitzone: {cfg.usage.quiet_hours.timezone}')
print(f'E-Mail aktiv: {cfg.channels.email.enabled}; Tageslimit: {cfg.channels.email.max_daily_sends}')
print(f'LinkedIn aktiv: {cfg.channels.linkedin.enabled}')
print('Neutrale Geschäftsdaten: ' + str(cfg.persona.company == 'Your Company'))
print('Datenbank vorhanden: ' + str(Path('data/harvey.db').is_file()))
PY
scripts/harvey sending status
scripts/harvey status
printf '%s\n' 'Live-KI-Zugriff separat prüfen: scripts/harvey status --check (kein Modellprompt).'
