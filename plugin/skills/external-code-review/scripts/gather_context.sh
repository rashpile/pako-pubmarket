#!/usr/bin/env bash
# Gather review context: commit log + full diff against base branch.
# Output is consumed by review agents as the canonical change-set.
set -uo pipefail

BASE="${1:-main}"

if ! git rev-parse --verify "${BASE}" >/dev/null 2>&1; then
    echo "error: base branch '${BASE}' not found" >&2
    exit 1
fi

echo "=== commits ==="
git log "${BASE}..HEAD" --oneline
echo
echo "=== diff ==="
git diff "${BASE}...HEAD"
