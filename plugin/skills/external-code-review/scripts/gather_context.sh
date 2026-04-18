#!/usr/bin/env bash
# Gather review context: commit log + full diff against base branch.
# Writes both to a fresh mktemp -d so concurrent sessions never collide,
# then prints a small summary (paths + counts) to stdout.
# Review agents should Read the diff_path rather than receive the diff
# inlined in their prompts — keeps the orchestrator's context lean.
set -uo pipefail

BASE="${1:-main}"

if ! git rev-parse --verify "${BASE}" >/dev/null 2>&1; then
    echo "error: base branch '${BASE}' not found" >&2
    exit 1
fi

OUT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/external-code-review.XXXXXX")"
DIFF_PATH="${OUT_DIR}/diff.patch"
COMMITS_PATH="${OUT_DIR}/commits.txt"

git log "${BASE}..HEAD" --oneline > "${COMMITS_PATH}"
git diff "${BASE}...HEAD" > "${DIFF_PATH}"

DIFF_LINES=$(wc -l < "${DIFF_PATH}" | tr -d ' ')
COMMIT_COUNT=$(wc -l < "${COMMITS_PATH}" | tr -d ' ')

echo "base: ${BASE}"
echo "commits: ${COMMIT_COUNT}"
echo "commits_path: ${COMMITS_PATH}"
echo "diff_path: ${DIFF_PATH}"
echo "diff_lines: ${DIFF_LINES}"
