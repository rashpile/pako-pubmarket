#!/usr/bin/env bash
# Resolve which config.json to use (project > user > none).
# Prints the winning path and its contents.
#
# Output format:
#   path: <path-or-"(none)">
#   --- contents ---
#   <file-contents, or empty if none found>
set -uo pipefail

PROJECT_CONFIG="$(pwd)/.claude/external-code-review/config.json"
USER_CONFIG="${HOME}/.claude/external-code-review/config.json"

for path in "${PROJECT_CONFIG}" "${USER_CONFIG}"; do
    if [ -f "${path}" ]; then
        echo "path: ${path}"
        echo "--- contents ---"
        cat "${path}"
        exit 0
    fi
done

echo "path: (none — built-in defaults apply)"
echo "--- contents ---"
