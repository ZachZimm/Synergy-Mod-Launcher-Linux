#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

find_python() {
  local candidate
  for candidate in python3.12 python3 python; do
    if ! command -v "$candidate" >/dev/null 2>&1; then
      continue
    fi
    if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

if ! PYTHON_BIN="$(find_python)"; then
  echo "No Python 3.12+ interpreter was found in PATH." >&2
  echo "Install Python 3.12 or newer, then rerun this script." >&2
  exit 1
fi

if [[ ! -d ./venv ]]; then
  "$PYTHON_BIN" -m venv ./venv
fi

./venv/bin/python -m pip install -r ./requirements.txt

if [[ -x ./discover_sc2_env.py ]]; then
  eval "$(./discover_sc2_env.py | grep '^export ')"
fi

exec ./run_sc2campaignlauncher.sh "$@"
