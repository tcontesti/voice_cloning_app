#!/usr/bin/env bash
# Install worker extras into the existing voice_cloning venv on the Spark.
# Idempotent. Will NOT touch torch / chatterbox / numpy already installed.
#
# Usage:
#   bash worker/install_into_venv.sh
#
# Verifies torch is intact afterwards.
set -euo pipefail

VENV="${VC_VENV:-$HOME/voice_cloning_env/.venv}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -x "$VENV/bin/python" ]]; then
    echo "ERROR: venv not found at $VENV (set VC_VENV)" >&2
    exit 1
fi

echo ">> torch BEFORE:" "$($VENV/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available())' 2>&1 | tail -1)"

# --no-deps for sentinels that pull torch (we keep the cu130 build)
"$VENV/bin/pip" install --no-build-isolation -r "$HERE/requirements-extra.txt"

echo ">> torch AFTER: " "$($VENV/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available())' 2>&1 | tail -1)"

if ! "$VENV/bin/python" -c 'import torch; assert "+cu130" in torch.__version__, torch.__version__'; then
    echo "FATAL: torch was downgraded — abort and rollback" >&2
    exit 2
fi
echo "OK"
