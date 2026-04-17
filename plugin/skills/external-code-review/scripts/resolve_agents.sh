#!/usr/bin/env bash
# Resolve which agent set to use (project > user > built-in).
# Prints the winning directory followed by agent names (filenames without .txt).
#
# Output format:
#   dir: <absolute-path>
#   agents:
#   <agent1>
#   <agent2>
#   ...
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILTIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/agents"
PROJECT_DIR="$(pwd)/.claude/external-code-review/agents"
USER_DIR="${HOME}/.claude/external-code-review/agents"

pick_dir() {
    for dir in "${PROJECT_DIR}" "${USER_DIR}" "${BUILTIN_DIR}"; do
        if [ -d "${dir}" ] && compgen -G "${dir}/*.txt" >/dev/null; then
            echo "${dir}"
            return 0
        fi
    done
    return 1
}

DIR="$(pick_dir)" || { echo "error: no agent directory with *.txt found" >&2; exit 1; }

echo "dir: ${DIR}"
echo "agents:"
for f in "${DIR}"/*.txt; do
    basename "${f}" .txt
done
