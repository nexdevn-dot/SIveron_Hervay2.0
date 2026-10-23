#!/usr/bin/env bash
set -euo pipefail
HARVEY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HARVEY_ROOT"
export PATH="$HARVEY_ROOT/.tools/codex/node_modules/.bin:$HARVEY_ROOT/.venv/bin:$PATH:/opt/homebrew/bin:/usr/local/bin"
export PLAYWRIGHT_BROWSERS_PATH="$HARVEY_ROOT/.cache/ms-playwright"
export UV_CACHE_DIR="$HARVEY_ROOT/.cache/uv"
export UV_PYTHON_INSTALL_DIR="$HARVEY_ROOT/.python"
export npm_config_cache="$HARVEY_ROOT/.cache/npm"

harvey_require_venv() {
  if [[ ! -x "$HARVEY_ROOT/.venv/bin/python" ]]; then
    printf '%s\n' 'Umgebung fehlt. Zuerst: bash scripts/setup.sh' >&2
    exit 1
  fi
}
