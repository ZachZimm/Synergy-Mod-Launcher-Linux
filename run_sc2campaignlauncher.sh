#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
exec ./venv/bin/python ./run_sc2campaignlauncher.py "$@"
