---
name: external-code-review
description: Multi-phase code review using external AI models (Codex CLI, Gemini CLI, and Pi CLI) with parallel review agents. Use when user wants external model verification, multi-agent code analysis, or autonomous review with fixes. Triggers on requests like "external code review", "multi-agent review", "review with external models", "review with gemini", "review with pi", or "comprehensive code analysis".
allowed-tools: Bash(git *), Bash(python *), Bash(npm *), Bash(npx *), Bash(make *), Bash(go *), Bash(cargo *), Read, Write, Edit, Grep, Glob, Agent
---

# External Code Review

Multi-phase code review system using external AI models (Codex, Gemini, and Pi) with parallel specialized agents.

The skill orchestrates all review phases directly — no subprocess escalation or `--dangerously-skip-permissions`. External tools run in read-only/sandbox mode; all fixes happen in the user's session with normal permissions.

## Prerequisites

Required CLI tools (at least one external tool recommended):
- `codex` - Codex CLI (OpenAI) - optional
- `gemini` - Gemini CLI (Google) - optional, fallback when codex unavailable
- `pi` - [Pi CLI](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (multimodel) - optional, fallback when codex and gemini unavailable

## Model Configuration

Optional config file at `~/.claude/external-code-review/config.json`:

```json
{
  "codex_model": "gpt-5.2-codex",
  "gemini_model": "",
  "pi_model": "",
  "pi_thinking": "high",
  "external_tool": "auto"
}
```

| Field | Effect |
|-------|--------|
| `codex_model` | Pass `-c 'model="<value>"'` to `codex exec` |
| `gemini_model` | Pass `-m <value>` to `gemini` CLI |
| `pi_model` | Pass `--model <value>` to `pi` CLI (supports `provider/model` format) |
| `pi_thinking` | Pass `--thinking <value>` to `pi` CLI (default: `high`). Values: `off`, `minimal`, `low`, `medium`, `high`, `xhigh` |
| `pi_options` | Additional CLI options as a list of strings, e.g. `["--provider", "openai"]`. Safety-related flags are rejected. |
| `external_tool` | Which external tool to use: `auto` (default), `codex`, `gemini`, or `pi` |

**External tool resolution (`auto` mode)**:
1. If user explicitly requests a specific tool (`gemini`, `pi`), use it
2. Try Codex CLI first (default)
3. If Codex is not installed, fall back to Gemini CLI
4. If Gemini is not installed, fall back to Pi CLI

If a field is absent or the config file doesn't exist, omit the model flag entirely for that CLI.

## Review Modes

**IMPORTANT: Always default to Full Review Mode unless the user explicitly says "quick review", "quick", or "fast review".** Phrases like "review my code", "run a review", "external code review", or just invoking this skill without qualifiers all mean Full Review. When in doubt, run the full review.

### Quick Review Mode

**Only** if the user explicitly requests a "quick review" or "fast review", skip Phase 1 and Phase 2:

1. Run **"0. Check Branch Status"** and **"1. Gather Context"** as normal
2. Skip Phase 1 (First Review) entirely
3. Skip Phase 2 (External Review) entirely
4. Run **Phase 3 (Final Review)** only — 2 agents (quality + implementation), critical/major issues only

### Full Review Mode (Default — use this unless user explicitly asks for quick)

Run all 3 phases as described below.

## Review Phases

### Phase 1: First Review (5 Agents in Parallel)

Launch 5 specialized agents simultaneously using the Agent tool:

| Agent | Focus Area | Prompt File |
|-------|------------|-------------|
| quality | Bugs, security, race conditions, error handling | `agents/quality.txt` |
| implementation | Goal achievement, requirement coverage, integration | `agents/implementation.txt` |
| testing | Test coverage, quality, edge cases, fake tests | `agents/testing.txt` |
| simplification | Over-engineering, excessive abstraction, unused code | `agents/simplification.txt` |
| documentation | README, CLAUDE.md, breaking changes | `agents/documentation.txt` |

### Phase 2: External Review (Codex, Gemini, or Pi)

- Run external tool via the script (read-only/sandbox mode)
- Get independent perspective from a different model family
- Evaluate findings directly and fix valid issues
- Tool selection: auto-detects available CLI, or user can specify

### Phase 3: Final Review (2 Agents)

- Critical/major issues only
- Agents: quality + implementation
- Style/minor issues ignored

## Workflow

### 0. Check Branch Status & Commit Changes

Before running the review, verify you're on a feature branch with committed changes:

```bash
git branch --show-current
git status
git log main..HEAD --oneline
```

**If on main/master branch:**
1. Create a feature branch first: `git checkout -b review/code-review-$(date +%Y%m%d)`
2. Or ask the user which branch to review

**If there are uncommitted changes:**
1. Ask the user if they want to commit before review
2. If yes, stage and commit: `git add -A && git commit -m "wip: changes for review"`

**If no commits ahead of base branch:**
- Inform the user and ask what they want to review

### 1. Gather Context

```bash
git log main..HEAD --oneline
git diff main...HEAD
```

Save the diff output — you'll pass it to the review agents.

### 2. Run Phase 1: First Review (5 Agents)

Read each agent prompt from `agents/*.txt`. Launch ALL 5 agents in parallel using the Agent tool. Each agent receives the git diff and its specialized prompt.

```
For each agent in [quality, implementation, testing, simplification, documentation]:
  Read agents/<agent>.txt
  Agent(prompt = agent_prompt + "\n\nCode changes to review:\n" + git_diff)
```

### 3. Process First Review Findings

After all agents complete, collect their findings. For each finding:

1. **Verify** - Read the actual code at file:line using Read tool
2. **Classify** - CONFIRMED or FALSE POSITIVE
3. **Fix** - Apply changes for confirmed issues using Edit tool
4. **Test** - Run tests + linter via Bash
5. **Commit** - `git commit -m "fix: address code review findings"`

**Loop**: Re-run Phase 1 agents to verify fixes didn't introduce new issues. Continue until zero confirmed issues found in an iteration.

IMPORTANT: Pre-existing issues (linter errors, failed tests) should also be fixed.

### 4. Run Phase 2: External Review

Run the external review script via Bash:

```bash
python scripts/run_review.py --branch main
```

Options:
```bash
# Force specific tool
python scripts/run_review.py --branch main --external-tool gemini
python scripts/run_review.py --branch main --external-tool pi

# With previous context (dismissed findings)
python scripts/run_review.py --branch main --previous-context "..."
```

The script runs the external tool in read-only mode and prints findings to stdout.

### 5. Evaluate External Findings

Read the script output. For EACH finding:

1. Read the code at the reported location using the Read tool
2. Trace the flow — find callers, understand full context
3. Assess actual impact — real problem or style preference?

Categorize as:
- **Valid issues** → Fix using Edit tool, run tests, DO NOT commit yet
- **Invalid/irrelevant** → Note why (will be passed as previous context)

### 6. Loop External Review

If valid issues were fixed:
- Run the script again to verify fixes (external tool re-checks)

If all findings were dismissed:
- Run script again with `--previous-context` containing dismissal explanations
- This prevents the external tool from re-reporting the same findings

If the external tool finds nothing:
- Commit all accumulated fixes: `git commit -m "fix: address external review findings"`
- External review is complete

Max iterations: 3. If max reached, commit any fixes and move on.

### 7. Run Phase 3: Final Review (2 Agents)

Same as Phase 1 but:
- Only 2 agents: quality + implementation
- Focus on **critical/major issues only**
- Ignore style/minor issues
- Max iterations: 3

### 8. Generate Review Report

After all phases complete, output structured report:

```markdown
# Code Review Report

## Summary
- Files reviewed: N
- Issues found: X (Y fixed, Z false positives)
- External review findings: A (B valid, C invalid)

## Phase 1: First Review
### Quality Agent
- [FIXED] Issue description
- [FALSE POSITIVE] Finding explanation

## Phase 2: External Review
- [VALID] Finding + fix applied
- [INVALID] Finding + rationale

## Phase 3: Final Review
- No critical/major issues remaining

## Commits
- abc123: fix: address code review findings
- def456: fix: address external review findings
```

## Agent Definitions

See `agents/` directory for full agent prompts:

- `agents/quality.txt` - Quality & security review
- `agents/implementation.txt` - Goal achievement verification
- `agents/testing.txt` - Test coverage analysis
- `agents/simplification.txt` - Over-engineering detection
- `agents/documentation.txt` - Documentation updates

## Script Usage

The script `scripts/run_review.py` is a thin wrapper that runs external tools only:

```bash
python scripts/run_review.py [options]

Options:
  --branch, -b        Base branch for diff (default: main)
  --external-tool     External tool: auto (default), codex, gemini, or pi
  --codex-model       Codex model override
  --gemini-model      Gemini model override
  --pi-model          Pi model override (supports provider/model format)
  --pi-thinking       Pi thinking level: off, minimal, low, medium, high, xhigh
  --pi-options        Additional Pi CLI options
  --previous-context  Dismissed findings from prior iterations
```

## Notes

- All orchestration happens in the user's Claude Code session — no permission escalation
- External tools run in read-only/sandbox mode (Codex: `--sandbox read-only`, Gemini: `-s`, Pi: `--tools read,grep,find,ls`)
- Always verify findings by reading actual code before fixing
- Run tests + linter after each fix batch
- Commit fixes with descriptive messages
- Pre-existing issues should still be fixed if found
