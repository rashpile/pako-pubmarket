# External Code Review

Multi-phase code review system using external AI models (Codex, Gemini, and Pi) with parallel specialized agents. Inspired by the [ralphex](https://github.com/umputun/ralphex) autonomous review pipeline.

## Structure

```
external-code-review/
├── SKILL.md                      # Skill definition for Claude Code (orchestrator)
├── README.md                     # This file - human documentation
├── agents/
│   ├── quality.txt               # Bugs, security, quality review
│   ├── implementation.txt        # Goal achievement verification
│   ├── testing.txt               # Test coverage analysis
│   ├── simplification.txt        # Over-engineering detection
│   └── documentation.txt         # Documentation updates review
└── scripts/
    └── run_review.py             # External tool runner (Codex/Gemini/Pi)
```

## Architecture

The skill uses a **skill-as-orchestrator** pattern:

- **SKILL.md** orchestrates all review phases directly within the user's Claude Code session
- **`scripts/run_review.py`** is a thin wrapper that only runs external tools (Codex/Gemini/Pi) and prints findings to stdout
- No `claude -p --dangerously-skip-permissions` subprocess — all fixes happen with the user's normal permissions
- External tools always run in read-only/sandbox mode

## Prerequisites

Install at least one external review tool:

- **codex** - [Codex CLI](https://github.com/openai/codex) (OpenAI) - optional
- **gemini** - [Gemini CLI](https://github.com/google-gemini/gemini-cli) (Google) - optional, fallback when codex unavailable
- **pi** - [Pi CLI](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (multimodel) - optional, fallback when codex and gemini unavailable

## Configuration

Configuration is resolved with **project > user > built-in** precedence (first found wins, no merging):

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `./.claude/external-code-review/` | Project-local (commit to repo) |
| 2 | `~/.claude/external-code-review/` | User-global |
| 3 (lowest) | Built-in (skill directory) | Default |

This applies to both `config.json` and `agents/*.txt`.

### config.json

Optional config file at `./.claude/external-code-review/config.json` (project) or `~/.claude/external-code-review/config.json` (user):

```json
{
  "codex_model": "gpt-5.2-codex",
  "gemini_model": "",
  "pi_model": "",
  "pi_thinking": "high",
  "external_tool": "auto"
}
```

All fields are optional — omit to use defaults.

| Field | Default | Description |
|-------|---------|-------------|
| `codex_model` | `gpt-5.2-codex` | Model for `codex` CLI |
| `gemini_model` | CLI default | Model for `gemini` CLI (`-m` flag) |
| `pi_model` | CLI default | Model for `pi` CLI (`--model` flag, supports `provider/model` format) |
| `pi_thinking` | `high` | Thinking level for `pi` CLI: `off`, `minimal`, `low`, `medium`, `high`, `xhigh` |
| `pi_options` | (none) | Additional `pi` CLI options as list of strings. Safety-related flags are rejected. |
| `external_tool` | `auto` | Which external tool to use: `auto`, `codex`, `gemini`, or `pi` |

**External tool resolution (`auto` mode):**
1. Try Codex CLI first
2. If Codex is not installed, fall back to Gemini CLI
3. If Gemini is not installed, fall back to Pi CLI

Set `external_tool` to `codex`, `gemini`, or `pi` to skip auto-detection.

### Custom Review Agents

Place `.txt` files in `agents/` at either config level to replace the built-in review agents:

```
# Project-local (applies to all contributors)
.claude/external-code-review/agents/security.txt
.claude/external-code-review/agents/performance.txt

# User-global (personal preference)
~/.claude/external-code-review/agents/quality.txt
~/.claude/external-code-review/agents/testing.txt
```

Each file defines one agent — the filename (without `.txt`) becomes the agent name, and the file content is the review prompt passed to the agent.

If at least one `.txt` file exists at a higher-priority level, **all** lower-level agents are ignored. To customize just one agent, copy all built-in agents from `agents/` to your override directory and modify the ones you want.

## Quick Start

```bash
# Make sure you're on a feature branch with committed changes
git branch --show-current

# Invoke the skill via Claude Code
# /external-code-review

# Or run just the external tool manually
python scripts/run_review.py --branch main --external-tool gemini
```

## Review Phases

### Phase 1: First Review (Parallel Agents)

The skill launches specialized agents **in parallel** using the Agent tool, passing the git diff to each. The agent set is resolved from the configuration hierarchy — custom agents override built-in ones.

**Built-in agents** (used when no overrides exist):

| Agent | Focus |
|-------|-------|
| **quality** | Bugs, security vulnerabilities, race conditions, error handling |
| **implementation** | Goal achievement, requirement coverage, integration completeness |
| **testing** | Test coverage, test quality, fake test detection, edge cases |
| **simplification** | Over-engineering, excessive abstraction, premature optimization |
| **documentation** | README updates, CLAUDE.md, breaking changes |

### Phase 2: External Review (Codex, Gemini, or Pi)

- The skill runs `python scripts/run_review.py` to invoke the external tool
- External tool analyzes code in sandbox/read-only mode
- The skill evaluates findings: fixes valid issues, dismisses clearly invalid ones
- **Disputed findings** trigger a structured discussion — Claude sends counter-arguments, the external tool responds with WITHDRAW/MAINTAIN/COMPROMISE, up to 10 rounds per finding
- Loops until external tool finds nothing new

### Phase 3: Final Review (2 Agents)

- Only **quality** and **implementation** agents
- Focuses on **critical/major issues only**
- Ignores style and minor issues

## Script Usage

The script is a simple external-tool runner:

```bash
python scripts/run_review.py [options]

Options:
  --branch, -b          Base branch for diff (default: main)
  --external-tool       External tool: auto (default), codex, gemini, or pi
  --codex-model         Codex model override
  --gemini-model        Gemini model override
  --pi-model            Pi model override (supports provider/model format)
  --pi-thinking         Pi thinking level: off, minimal, low, medium, high, xhigh
  --pi-options          Additional Pi CLI options
  --previous-context    Dismissed findings from prior iterations
  --discuss             Discussion mode: debate disputed findings
  --discussion-context  The dispute exchange (findings + counter-arguments)
```

## Workflow

1. **Gather context**: `git diff` and `git log` against base branch
2. **Launch agents**: Agents run in parallel via Agent tool
3. **Verify findings**: Read actual code to confirm each finding
4. **Fix confirmed issues**: Apply changes using Edit tool
5. **Run tests + linter**: Verify fixes via Bash
6. **Commit**: `git commit -m "fix: address code review findings"`
7. **Loop**: Re-run agents to verify fixes, continue until clean
8. **External review**: Run external tool, evaluate findings, fix valid issues
9. **Discuss disputes**: Debate non-trivial disagreements with external reviewer (up to 10 rounds)
10. **Final review**: Critical/major issues only

## Notes

- All orchestration happens in the user's Claude Code session — no permission escalation
- Codex runs in read-only sandbox (`--sandbox read-only`)
- Pi runs with restricted tools (`read,grep,find,ls`) and extensions/skills disabled
- Gemini runs in sandbox mode (`-s` flag)
- Pre-existing issues (linter errors, failed tests) are fixed too
- Each iteration verifies previous fixes didn't introduce new issues

## Credits

Agent prompts (`agents/*.txt`) are sourced from [ralphex](https://github.com/umputun/ralphex) by [Umputun](https://github.com/umputun), licensed under the MIT License. The review pipeline design is inspired by ralphex's autonomous code review approach.

Copyright (c) 2026 Umputun — see [ralphex LICENSE](https://github.com/umputun/ralphex/blob/master/LICENSE) for details.
