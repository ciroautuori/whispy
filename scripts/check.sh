#!/usr/bin/env bash
# Everything CI would run, run locally. Same checks a reviewer will apply.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

PY="${PYTHON:-python3}"
fail=0

step() { printf '\n\033[1m→ %s\033[0m\n' "$1"; }

step "ruff check"
"$PY" -m ruff check . || fail=1        # `.`, exactly like CI — not just whispy/ + tests/

step "ruff format --check"
"$PY" -m ruff format --check . || fail=1

step "pytest"
"$PY" -m pytest -q || fail=1

if [[ "$fail" -eq 0 ]]; then
    printf '\n\033[32m✔ all checks passed\033[0m\n'
else
    printf '\n\033[31m✘ some checks failed\033[0m\n' >&2
fi
exit "$fail"
