#!/usr/bin/env bash
source "$(dirname -- "$0")/common.sh"
harvey_require_venv
exec "$HARVEY_ROOT/scripts/harvey" dashboard --host 127.0.0.1 --port "${HARVEY_PORT:-5555}"
