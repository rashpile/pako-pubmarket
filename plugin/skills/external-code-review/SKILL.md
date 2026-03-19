---
name: external-code-review
description: Multi-phase code review using external AI models (Claude CLI, Codex CLI, Gemini CLI, and Pi CLI) with parallel review agents. Use when user wants external model verification, multi-agent code analysis, or autonomous review with fixes. Triggers on requests like "external code review", "multi-agent review", "review with external models", "review with gemini", "review with pi", or "comprehensive code analysis".
---

# External Code Review

Multi-phase code review system using external AI models (Claude, Codex, Gemini, and Pi) with parallel specialized agents. Inspired by the ralphex autonomous review pipeline.

## Prerequisites

Required CLI tools:
- `claude` - Claude CLI (Anthropic)
- `codex` - Codex CLI (OpenAI) - optional
- `gemini` - Gemini CLI (Google) - optional, used as fallback when codex is not available
- `pi` - [Pi CLI](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (multimodel) - optional, used as fallback when codex and gemini are not available

At least one of `codex`, `gemini`, or `pi` is recommended for the external review phase. If none is available, the external review phase will be skipped.

## Model Configuration

By default, **do NOT specify a model** for either Claude CLI or Codex CLI — let each use its own default.

**Exception**: If a config file exists at `~/.claude/external-code-review/config.json` with model overrides, use those. Before running any external CLI, check:

```bash
# Check for custom model config
if [ -f ~/.claude/external-code-review/config.json ]; then
  cat ~/.claude/external-code-review/config.json
fi
```

Supported config fields:

| Field | Effect |
|-------|--------|
| `claude_model` | Pass `--model <value>` to `claude` CLI |
| `codex_model` | Pass `-c 'model="<value>"'` to `codex exec` |
| `gemini_model` | Pass `-m <value>` to `gemini` CLI |
| `pi_model` | Pass `--model <value>` to `pi` CLI (supports `provider/model` format, e.g. `anthropic/claude-sonnet-4-20250514`) |
| `pi_thinking` | Pass `--thinking <value>` to `pi` CLI (default: `high`). Values: `off`, `minimal`, `low`, `medium`, `high`, `xhigh` |
| `pi_options` | Additional CLI options as a list of strings, e.g. `["--provider", "openai"]`. Options starting with `--tools`, `--extensions`, `--skills`, `--no-extensions`, or `--no-skills` are rejected (safety flags are enforced automatically). |
| `external_tool` | Which external tool to use: `auto` (default), `codex`, `gemini`, or `pi` |

Example config:
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

**External tool resolution (`auto` mode)**:
1. If user explicitly requests a specific tool (`gemini`, `pi`), use it
2. Try Codex CLI first (default)
3. If Codex is not installed, fall back to Gemini CLI
4. If Gemini is not installed, fall back to Pi CLI
5. If none is found, attempt Codex (will fail with clear error)

If a field is absent or the config file doesn't exist, omit the model flag entirely for that CLI.

## Review Modes

### Quick Review Mode

If the user requests a **quick review** (e.g., "quick review", "fast review", "quick code review"), skip directly to the **Final Review** phase only:

1. Run steps from **"0. Check Branch Status & Commit Changes"** and **"1. Gather Context"** as normal
2. Skip Phase 1 (First Review) entirely
3. Skip Phase 2 (Codex External Review) entirely
4. Run **Phase 3 (Final Review)** only — 2 agents (quality + implementation), critical/major issues only
5. Generate the review report (noting it was a quick review)

Use the script shortcut:
```bash
python scripts/run_review.py quick --branch main
```

### Full Review Mode (Default)

When no quick mode is requested, run all 3 phases as described below.

## Review Phases

### Phase 1: First Review (5 Agents in Parallel)

Launch 5 specialized agents simultaneously:

| Agent | Focus Area |
|-------|------------|
| quality | Bugs, security, race conditions, error handling |
| implementation | Goal achievement, requirement coverage, integration |
| testing | Test coverage, quality, edge cases, fake tests |
| simplification | Over-engineering, excessive abstraction, unused code |
| documentation | README, CLAUDE.md, breaking changes |

### Phase 2: External Review (Codex, Gemini, or Pi)

- External model (Codex, Gemini, or Pi) analyzes code in sandbox/read-only mode
- Independent perspective from different model family
- Claude evaluates external findings
- Categorize as: Valid / Invalid / Irrelevant
- Tool selection: auto-detects available CLI, or user can specify `--external-tool gemini` or `--external-tool pi`

### Phase 3: Final Review (2 Agents)

- Critical/major issues only
- Agents: quality + implementation
- Style/minor issues ignored

## Workflow

### 0. Check Branch Status & Commit Changes

Before running the review, verify you're on a feature branch with committed changes:

```bash
# Check current branch
git branch --show-current

# Check for uncommitted changes
git status

# Check if there are commits compared to base branch
git log main..HEAD --oneline
```

**If on main/master branch:**
1. Create a feature branch first: `git checkout -b review/code-review-$(date +%Y%m%d)`
2. Or ask the user which branch to review

**If there are uncommitted changes:**
1. Ask the user if they want to commit before review
2. If yes, stage and commit: `git add -A && git commit -m "wip: changes for review"`
3. This ensures clean separation between reviewed code and subsequent fixes

**If no commits ahead of base branch:**
- The review will have nothing to analyze
- Inform the user and ask what they want to review

### 1. Gather Context

```bash
# Get changes to review
git log main..HEAD --oneline
git diff main...HEAD
```

Determine scope: full codebase, branch diff, or specific files.

### 2. Run First Review

Execute the review script:

```bash
python scripts/run_review.py first --branch main
```

Or manually with claude CLI (add `--model <claude_model>` if configured):

```bash
# Check config for claude model
CLAUDE_MODEL=$(cat ~/.claude/external-code-review/config.json 2>/dev/null | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('claude_model',''))" 2>/dev/null)

claude -p "$(cat prompts/review_first.txt)" ${CLAUDE_MODEL:+--model "$CLAUDE_MODEL"}
```

**Agent launch pattern** (in parallel via Task tool):

```
For each agent in [quality, implementation, testing, simplification, documentation]:
  Task(subagent_type="general-purpose", prompt=agent_prompt + git_diff)
```

### 3. Process First Review Findings

For each finding:
1. **Verify** - Read actual code to confirm
2. **Classify** - CONFIRMED or FALSE POSITIVE
3. **Fix** - Apply changes for confirmed issues
4. **Test** - Run tests + linter
5. **Commit** - `git commit -m "fix: address code review findings"`

Loop until zero confirmed issues found.

### 4. Run External Review (Codex, Gemini, or Pi)

```bash
# Auto-detect tool (codex first, gemini fallback, pi fallback)
python scripts/run_review.py codex --branch main

# Explicitly use gemini
python scripts/run_review.py codex --branch main --external-tool gemini

# Explicitly use pi
python scripts/run_review.py codex --branch main --external-tool pi

# Pi with custom model and thinking level
python scripts/run_review.py codex --branch main --external-tool pi --pi-model "anthropic/claude-sonnet-4-20250514" --pi-thinking xhigh
```

Or manually with Codex:

```bash
CODEX_MODEL=$(cat ~/.claude/external-code-review/config.json 2>/dev/null | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('codex_model',''))" 2>/dev/null)

if [ -n "$CODEX_MODEL" ]; then
  codex exec --sandbox read-only \
    -c "model=\"$CODEX_MODEL\"" \
    -c model_reasoning_effort=xhigh \
    "Review code changes: $(git diff main...HEAD)"
else
  codex exec --sandbox read-only \
    -c model_reasoning_effort=xhigh \
    "Review code changes: $(git diff main...HEAD)"
fi
```

Or manually with Gemini:

```bash
GEMINI_MODEL=$(cat ~/.claude/external-code-review/config.json 2>/dev/null | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('gemini_model',''))" 2>/dev/null)

gemini -p "Review code changes: $(git diff main...HEAD)" \
  -s -o text ${GEMINI_MODEL:+-m "$GEMINI_MODEL"}
```

Or manually with Pi:

```bash
PI_MODEL=$(cat ~/.claude/external-code-review/config.json 2>/dev/null | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('pi_model',''))" 2>/dev/null)
PI_THINKING=$(cat ~/.claude/external-code-review/config.json 2>/dev/null | python3 -c "import sys,json; c=json.load(sys.stdin); print(c.get('pi_thinking','high'))" 2>/dev/null)

pi -p "Review code changes: $(git diff main...HEAD)" \
  --tools read,grep,find,ls --no-extensions --no-skills \
  --thinking "${PI_THINKING:-high}" ${PI_MODEL:+--model "$PI_MODEL"}
```

### 5. Evaluate External Findings

Pass external tool output to Claude for evaluation (add `--model <claude_model>` if configured):

```bash
claude -p "$(cat prompts/external_eval.txt)" ${CLAUDE_MODEL:+--model "$CLAUDE_MODEL"}
```

Three-path evaluation logic:
- **Valid issues found** → fix them, no signal, loop re-runs external tool to verify
- **All findings dismissed** → no signal, loop re-runs with dismissal explanations as context
- **External tool found nothing** → commit fixes, emit `<<<CODEX_REVIEW_DONE>>>`

### 6. Run Final Review

```bash
python scripts/run_review.py final --branch main
```

Only 2 agents (quality + implementation), critical/major issues only.

### 7. Generate Review Report

After all phases complete, output structured report:

```markdown
# Code Review Report

## Summary
- Files reviewed: N
- Issues found: X (Y fixed, Z false positives)
- Codex findings: A (B valid, C invalid)

## Phase 1: First Review
### Quality Agent
- [FIXED] Issue description
- [FALSE POSITIVE] Finding explanation

### Implementation Agent
...

## Phase 2: Codex External Review
- [VALID] Finding + fix applied
- [INVALID] Finding + rationale

## Phase 3: Final Review
- No critical/major issues remaining

## Commits
- abc123: fix: address code review findings
- def456: fix: address codex review findings
```

## Signal-Based Completion

The review loop uses signals to determine completion:

| Signal | Meaning |
|--------|---------|
| `<<<REVIEW_DONE>>>` | Zero issues found this iteration |
| `<<<CODEX_REVIEW_DONE>>>` | Codex found no issues |
| `<<<REVIEW_FAILED>>>` | Cannot fix (needs human intervention) |

**Important**: `REVIEW_DONE` means "found zero issues", NOT "finished fixing". If issues were fixed, do NOT emit signal - let loop run again to verify.

## Agent Definitions

See `agents/` directory for full agent prompts:

- `agents/quality.txt` - Quality & security review
- `agents/implementation.txt` - Goal achievement verification
- `agents/testing.txt` - Test coverage analysis
- `agents/simplification.txt` - Over-engineering detection
- `agents/documentation.txt` - Documentation updates

## Prompt Templates

See `prompts/` directory:

- `prompts/review_first.txt` - Phase 1 comprehensive review
- `prompts/external_eval.txt` - External tool findings evaluation (Codex/Gemini/Pi)
- `prompts/review_final.txt` - Phase 3 critical review

## Configuration Options

When invoking review, consider:

| Option | Default | Description |
|--------|---------|-------------|
| branch | main | Base branch for diff |
| max_iterations | 10 | Max review loops |
| claude_model | (claude default) | Claude model — uses Claude default unless overridden in `~/.claude/external-code-review/config.json` |
| codex_enabled | true | Run external review phase |
| codex_model | (codex default) | Codex model — uses Codex default unless overridden in `~/.claude/external-code-review/config.json` |
| codex_sandbox | read-only | Codex sandbox mode |
| codex_reasoning | xhigh | Codex reasoning effort level |
| external_tool | auto | External tool selection: `auto` (codex→gemini→pi fallback), `codex`, `gemini`, or `pi` |
| gemini_model | (gemini default) | Gemini model — uses Gemini default unless overridden in config |
| pi_model | (pi default) | Pi model — supports `provider/model` format (e.g. `anthropic/claude-sonnet-4-20250514`) |
| pi_thinking | high | Pi thinking level: `off`, `minimal`, `low`, `medium`, `high`, `xhigh` |
| pi_options | (none) | Additional Pi CLI options as list of strings |

## Example Session

**User**: "Review my feature branch against main"

**Execution**:
```bash
# Phase 1: First review with 5 agents
python scripts/run_review.py first --branch main

# Phase 2: Codex external review
python scripts/run_review.py codex --branch main

# Phase 3: Final review
python scripts/run_review.py final --branch main

# Generate report
python scripts/run_review.py report
```

## Notes

- Always verify findings by reading actual code before fixing
- Run tests + linter after each fix batch
- Commit fixes with descriptive messages
- Codex runs in read-only sandbox for safety
- Final review ignores style/minor issues (critical/major only)
- Pre-existing issues should still be fixed if found