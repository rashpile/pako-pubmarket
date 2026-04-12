# Plan Review

Multi-round implementation plan review using parallel specialized agents. Validates plans before code is written — catching architectural, complexity, convention, and completeness issues at the design stage.

## Structure

```
plan-review/
├── SKILL.md                      # Skill definition for Claude Code (orchestrator)
├── README.md                     # This file - human documentation
├── agents/
│   ├── 1_architect.txt           # Round 1: strategy, dependencies, risks
│   ├── 1_simplifier.txt          # Round 1: over-engineering, YAGNI
│   ├── 2_conventions.txt         # Round 2: project pattern alignment
│   └── 2_completionist.txt       # Round 2: gaps, testing, security
└── scripts/
    └── run_plan_review.py        # External tool runner (Codex/Gemini/Pi)
```

## Architecture

The skill uses the same **skill-as-orchestrator** pattern as `external-code-review`:

- **SKILL.md** orchestrates all review rounds directly within the user's Claude Code session
- Agents are dispatched in rounds determined by the `N_` prefix in their filename
- Same-round agents run **in parallel**; rounds execute **sequentially**
- The orchestrator **synthesizes** findings between rounds, flagging conflicts
- The plan file is **annotated inline** with HTML comments containing findings
- **`scripts/run_plan_review.py`** runs an optional external model review (Codex/Gemini/Pi) in read-only mode

## How It Works

### Review Mode (default)

1. **Plan Discovery** — provide the plan file path (any format: markdown, structured, freeform)
2. **Round 1** — architect + simplifier run in parallel, reviewing strategy and complexity
3. **Synthesis** — orchestrator merges findings, flags conflicts between reviewers
4. **Round 2** — conventions + completionist run in parallel, informed by round 1 findings
5. **Synthesis** — final consolidated findings list
6. **Annotation** — plan file annotated with inline HTML comments per finding
7. **External Review** (optional) — independent model provides holistic assessment
8. **Summary** — findings by reviewer, severity, and conflicts resolved

### Config Mode (`--config`)

Interactive wizard for customizing agents:

1. Copies built-in agents to `.claude/plan-review/agents/`
2. Helps create new custom agents interactively
3. User assigns round numbers to each agent (or skips to remove)
4. Applies ordering by renaming files to `N_name.txt`
5. Optionally configures `config.json`

## Agent Naming Convention

Filenames follow the pattern `N_name.txt`:

- **N** — round number (integer)
- **name** — agent identifier
- Same N = run in parallel
- Ascending N = run sequentially
- No prefix = defaults to round 1

Example: `1_architect.txt` and `1_simplifier.txt` run together in round 1, then `2_conventions.txt` and `2_completionist.txt` run together in round 2.

## Configuration

Configuration is resolved with **project > user > built-in** precedence (first found wins, no merging):

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `./.claude/plan-review/` | Project-local |
| 2 | `~/.claude/plan-review/` | User-global |
| 3 (lowest) | Built-in (skill directory) | Default |

This applies to both `config.json` and `agents/*.txt`.

### config.json

Optional config file at `./.claude/plan-review/config.json` (project) or `~/.claude/plan-review/config.json` (user):

```json
{
  "external_review": true,
  "external_model": "auto",
  "max_rounds": 3,
  "annotation_format": "html_comment"
}
```

All fields are optional — omit to use defaults.

| Field | Default | Description |
|-------|---------|-------------|
| `external_review` | `true` | Enable/disable external model review round |
| `external_model` | `"auto"` | Which external tool: `auto`, `codex`, `gemini`, or `pi` |
| `max_rounds` | `3` | Safety cap on round count from agent filenames |
| `annotation_format` | `"html_comment"` | Annotation format for plan file |

### Custom Review Agents

Place `.txt` files in `agents/` at either config level to replace the built-in review agents:

```
# Project-local (applies to all contributors)
.claude/plan-review/agents/1_architect.txt
.claude/plan-review/agents/1_security.txt
.claude/plan-review/agents/2_conventions.txt

# User-global (personal preference)
~/.claude/plan-review/agents/1_simplifier.txt
```

If at least one `.txt` file exists at a higher-priority level, **all** lower-level agents are ignored. Use `--config` mode to set up project agents interactively.

## Built-in Agents

| Agent | Round | Focus |
|-------|-------|-------|
| **architect** | 1 | Strategy, dependency ordering, risks, single points of failure |
| **simplifier** | 1 | Over-engineering, YAGNI violations, simpler alternatives |
| **conventions** | 2 | Project patterns, infrastructure alignment, convention deviations |
| **completionist** | 2 | Gaps in error handling, testing strategy, security, observability |

Round 2 agents see round 1 findings — if the simplifier proposes an alternative, conventions checks whether it fits project patterns, and completionist checks whether it introduces new gaps.

## Plan Annotation Format

Findings are inserted as HTML comments above the relevant section:

```markdown
## Phase 1: Setup database schema
<!-- [architect] Consider adding rollback strategy for migration failure -->
<!-- [simplifier] This could use the existing ORM migration tool instead of raw SQL -->
Create the initial database tables...
```

HTML comments don't break plan rendering but are visible when editing.

## Prerequisites

Optional CLI tools for external review (at least one recommended):

- **codex** - [Codex CLI](https://github.com/openai/codex) (OpenAI)
- **gemini** - [Gemini CLI](https://github.com/google-gemini/gemini-cli) (Google)
- **pi** - [Pi CLI](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (multimodel)

## Quick Start

```bash
# Review a plan (invoke via Claude Code)
# /plan-review path/to/plan.md

# Configure agents for this project
# /plan-review --config

# Run just the external tool manually
python scripts/run_plan_review.py --plan-file path/to/plan.md
python scripts/run_plan_review.py --plan-file plan.md --external-tool gemini
```

## Script Usage

```bash
python scripts/run_plan_review.py [options]

Options:
  --plan-file, -f       Path to the plan file to review (required)
  --external-tool       External tool: auto (default), codex, gemini, or pi
  --codex-model         Codex model override
  --gemini-model        Gemini model override
  --pi-model            Pi model override (supports provider/model format)
  --pi-thinking         Pi thinking level: off, minimal, low, medium, high, xhigh
  --pi-options          Additional Pi CLI options as JSON array
  --internal-findings   Consolidated findings from internal review rounds
```

## Notes

- All orchestration happens in the user's Claude Code session — no permission escalation
- External tools run in read-only/sandbox mode
- Plan file is modified in-place with HTML comment annotations (additive only)
- Annotations preserve all original plan content — nothing is removed
