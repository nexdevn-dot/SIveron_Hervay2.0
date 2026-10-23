#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/common.sh"
harvey_require_venv
exec "$HARVEY_ROOT/.venv/bin/python" -m playwright install chromium
