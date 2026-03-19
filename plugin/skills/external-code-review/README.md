# External Code Review

Multi-phase code review system using external AI models (Claude, Codex, Gemini, and Pi) with parallel specialized agents. Inspired by the [ralphex](https://github.com/umputun/ralphex) autonomous review pipeline.

## Structure

```
external-code-review/
├── SKILL.md                      # Skill definition for Claude Code
├── README.md                     # This file - human documentation
├── agents/
│   ├── quality.txt               # Bugs, security, quality review
│   ├── implementation.txt        # Goal achievement verification
│   ├── testing.txt               # Test coverage analysis
│   ├── simplification.txt        # Over-engineering detection
│   └── documentation.txt         # Documentation updates review
├── prompts/
│   ├── review_first.txt          # Phase 1: Comprehensive (5 agents)
│   ├── external_eval.txt          # Phase 2: External tool evaluation (Codex/Gemini/Pi)
│   └── review_final.txt          # Phase 3: Critical issues (2 agents)
└── scripts/
    └── run_review.py             # Review orchestration script
```

## Prerequisites

Install and configure these CLI tools:

- **claude** - [Claude CLI](https://docs.anthropic.com/claude-code) (Anthropic) - required
- **codex** - [Codex CLI](https://github.com/openai/codex) (OpenAI) - optional
- **gemini** - [Gemini CLI](https://github.com/google-gemini/gemini-cli) (Google) - optional, fallback when codex unavailable
- **pi** - [Pi CLI](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (multimodel) - optional, fallback when codex and gemini unavailable

## Configuration

Optional config file at `~/.claude/external-code-review/config.json`:

```json
{
  "claude_model": "sonnet",
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
| `claude_model` | CLI default | Model for `claude` CLI (`--model` flag) |
| `codex_model` | `gpt-5.2-codex` | Model for `codex` CLI |
| `gemini_model` | CLI default | Model for `gemini` CLI (`-m` flag) |
| `pi_model` | CLI default | Model for `pi` CLI (`--model` flag, supports `provider/model` format) |
| `pi_thinking` | `high` | Thinking level for `pi` CLI: `off`, `minimal`, `low`, `medium`, `high`, `xhigh` |
| `pi_options` | (none) | Additional `pi` CLI options as list of strings, e.g. `["--provider", "openai"]`. Options starting with `--tools`, `--extensions`, `--skills`, `--no-extensions`, `--no-skills`, `--prompt`, `--model`, or `--thinking` are rejected, as are `-p` and bare `--` (safety flags and dedicated config fields are enforced automatically). |
| `external_tool` | `auto` | Which external tool to use: `auto`, `codex`, `gemini`, or `pi` |

**External tool resolution (`auto` mode):**
1. Try Codex CLI first
2. If Codex is not installed, fall back to Gemini CLI
3. If Gemini is not installed, fall back to Pi CLI
4. If user explicitly asks for a tool (e.g., "review with pi"), use it regardless

Set `external_tool` to `codex`, `gemini`, or `pi` to skip auto-detection and always use a specific tool.

## Quick Start

**Important:** You must be on a feature branch with changes compared to the base branch.

```bash
# 1. Make sure you're on a feature branch (not main/master)
git branch --show-current

# 2. If on main, create a feature branch first
git checkout -b review/code-review-$(date +%Y%m%d)

# 3. Run full review pipeline
python scripts/run_review.py full --branch main --goal "Feature X implementation"

# Quick review (final phase only - 2 agents, critical/major issues)
python scripts/run_review.py quick --branch main --goal "Feature X implementation"

# Run individual phases
python scripts/run_review.py first --branch main
python scripts/run_review.py codex --branch main
python scripts/run_review.py final --branch main

# Generate summary report
python scripts/run_review.py report
```

## Review Phases

### Phase 1: First Review (5 Agents)

Launches 5 specialized agents **in parallel**:

| Agent | Focus |
|-------|-------|
| **quality** | Bugs, security vulnerabilities, race conditions, error handling |
| **implementation** | Goal achievement, requirement coverage, integration completeness |
| **testing** | Test coverage, test quality, fake test detection, edge cases |
| **simplification** | Over-engineering, excessive abstraction, premature optimization |
| **documentation** | README updates, CLAUDE.md, breaking changes |

### Phase 2: External Review (Codex, Gemini, or Pi)

- External tool (Codex, Gemini, or Pi) analyzes code in sandbox/read-only mode
- Auto-detects available tool: codex first, gemini fallback, pi fallback. Use `--external-tool pi` to force Pi.
- Provides independent perspective from a different model family
- Claude evaluates findings with three-path logic:
  - **Valid issues found** → fix them, loop re-runs external tool to verify
  - **All findings dismissed** → loop re-runs with dismissal context to avoid re-reporting
  - **External tool found nothing** → commit fixes, done

### Phase 3: Final Review (2 Agents)

- Only **quality** and **implementation** agents
- Focuses on **critical/major issues only**
- Ignores style and minor issues

## Signal-Based Completion

The review script (`run_review.py`) and the Claude CLI prompts communicate through signal strings. The script launches `claude -p "<prompt>"` as a subprocess, captures stdout, and scans it for specific signal strings to decide whether to keep iterating or stop.

| Signal | Meaning | Script action |
|--------|---------|---------------|
| `<<<REVIEW_DONE>>>` | Zero issues found this iteration | Stop loop — review is clean |
| `<<<CODEX_REVIEW_DONE>>>` | External tool found no issues | Stop loop — external review done |
| `<<<REVIEW_FAILED>>>` | Issues found but cannot be fixed | Stop loop — needs human help |
| No signal | Issues were found and fixed | Continue loop — re-verify fixes |

The prompts tell Claude exactly when to emit each signal:

- **Path A** — no issues found → output `<<<REVIEW_DONE>>>`
- **Path B** — issues found and fixed → stop, no signal (loop runs again to verify)
- **Path C** — issues found but can't fix → output `<<<REVIEW_FAILED>>>`

`REVIEW_DONE` means "found zero issues", NOT "finished fixing". If issues were fixed, the loop continues to verify the fixes didn't introduce new problems.

## CLI Options

```bash
python scripts/run_review.py <phase> [options]

Phases:
  first       Run first review (5 agents)
  codex       Run Codex external review
  final       Run final review (2 agents)
  full        Run complete pipeline (first → codex → final)
  quick       Run quick review (final phase only — 2 agents, critical/major)
  report      Generate summary report

Options:
  --branch, -b        Base branch for diff (default: main)
  --goal, -g          Description of what was implemented
  --max-iterations, -i  Max review iterations (default: 10)
  --no-codex          Disable external review (Codex/Gemini/Pi)
  --codex-model       Codex model override (default: codex default)
  --external-tool     External tool: auto (default), codex, gemini, or pi
  --gemini-model      Gemini model override (default: gemini default)
  --pi-model          Pi model override (default: pi default, supports provider/model format)
  --pi-thinking       Pi thinking level: off, minimal, low, medium, high (default), xhigh
  --timeout, -t       Timeout per Claude call in seconds (default: 120)
```

## Workflow

1. **Get context**: `git diff` and `git log` against base branch
2. **Launch agents**: All agents run in parallel via Task tool
3. **Collect findings**: Merge and deduplicate across agents
4. **Verify each finding**: Read actual code to confirm (not false positive)
5. **Fix confirmed issues**: Apply changes
6. **Run tests + linter**: Verify fixes don't break anything
7. **Commit**: `git commit -m "fix: address code review findings"`
8. **Loop**: Continue until zero issues found

## Agent Definitions

Each agent has a specific focus area defined in `agents/*.txt`:

- **quality.txt** - Correctness, security, simplicity assessment
- **implementation.txt** - Requirement coverage, wiring, completeness
- **testing.txt** - Coverage gaps, test quality, fake test detection
- **simplification.txt** - Abstraction layers, premature generalization
- **documentation.txt** - README, CLAUDE.md, plan file updates

## Customization

### Custom Agents

Edit files in `agents/` to modify review focus areas.

### Custom Prompts

Edit files in `prompts/` to change the review workflow:

- `review_first.txt` - Modify which agents run or how findings are processed
- `external_eval.txt` - Change how external tool findings are evaluated
- `review_final.txt` - Adjust final review criteria

## Example Session

```bash
# Create feature branch
git checkout -b feature/user-auth

# ... implement feature ...

# Run full review
python scripts/run_review.py full \
  --branch main \
  --goal "User authentication with JWT tokens"

# Output:
# 🔍 Starting FULL REVIEW pipeline
# 📋 Starting FIRST REVIEW phase (5 agents)
# 🔄 First review iteration 1/10
# 🧠 Running Claude review...
# ... agent findings ...
# ✅ First review complete - no issues found!
# 🤖 Starting EXTERNAL REVIEW phase (Codex)
# ... external analysis ...
# ✅ Codex review complete!
# 🎯 Starting FINAL REVIEW phase (2 agents)
# ... final verification ...
# ✅ Final review complete - no critical issues!
# 🎉 FULL REVIEW pipeline complete!
```

## Notes

- Pre-existing issues (linter errors, failed tests) are fixed too
- Codex runs in read-only sandbox for safety
- Pi runs with restricted tools (read, grep, find, ls) and extensions/skills disabled
- Gemini runs in sandbox mode (-s flag)
- Each iteration verifies previous fixes didn't introduce new issues
- Tests and linter must pass after each fix batch

## Credits

Agent prompts (`agents/*.txt`) are sourced from [ralphex](https://github.com/umputun/ralphex) by [Umputun](https://github.com/umputun), licensed under the MIT License. The review pipeline design is inspired by ralphex's autonomous code review approach.

Copyright (c) 2026 Umputun — see [ralphex LICENSE](https://github.com/umputun/ralphex/blob/master/LICENSE) for details.