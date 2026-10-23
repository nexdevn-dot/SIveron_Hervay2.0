#!/usr/bin/env bash
source "$(dirname -- "$0")/common.sh"
umask 077
mkdir -p .tools .cache data
if [[ ! -x .tools/bootstrap/bin/uv ]]; then
  python3 -m pip install --no-cache-dir --target .tools/bootstrap 'uv==0.13.1'
fi
.tools/bootstrap/bin/uv python install 3.12.15 --no-bin
if [[ ! -x .venv/bin/python ]]; then
  .tools/bootstrap/bin/uv venv --python 3.12.15 .venv
fi
if [[ -s requirements-dev.lock ]]; then
  .tools/bootstrap/bin/uv pip install --python .venv/bin/python -r requirements-dev.lock
  .tools/bootstrap/bin/uv pip install --python .venv/bin/python --no-deps -e .
else
  .tools/bootstrap/bin/uv pip install --python .venv/bin/python -e '.[dev]'
fi
.venv/bin/python -m playwright install chromium
if [[ ! -x .tools/codex/node_modules/.bin/codex ]] || \
   [[ "$(.tools/codex/node_modules/.bin/codex --version)" != 'codex-cli 0.159.3' ]]; then
  npm install --prefix .tools/codex --no-audit --no-fund --save-exact '@openai/codex@0.159.3'
fi
if [[ ! -f .env ]]; then cp .env.example .env; fi
if [[ ! -f harvey.local.yaml ]]; then cp config/development.yaml harvey.local.yaml; fi
chmod 600 .env harvey.local.yaml
.venv/bin/python scripts/initialize.py
printf '%s\n' 'Siveron ist eingerichtet. Dashboard: bash scripts/dashboard.sh'
