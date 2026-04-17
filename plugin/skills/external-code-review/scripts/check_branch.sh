#!/usr/bin/env bash
# Check branch readiness for code review.
# Prints current branch, working-tree status, and commits ahead of base.
# Exits 0 always — caller interprets the output.
set -uo pipefail

BASE="${1:-main}"

echo "branch: $(git branch --show-current 2>/dev/null || echo '(detached)')"
echo "base: ${BASE}"
echo "--- status ---"
git status --short
echo "--- commits ahead of ${BASE} ---"
if git rev-parse --verify "${BASE}" >/dev/null 2>&1; then
    git log "${BASE}..HEAD" --oneline
else
    echo "(base branch '${BASE}' not found)"
fi
