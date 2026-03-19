---
name: external-code-review
description: Multi-phase code review using external AI models (Claude CLI and Codex CLI) with parallel review agents. Use when user wants comprehensive code review, external model verification, multi-agent code analysis, or autonomous review with fixes. Triggers on requests like "review my code with external models", "run code review", "external code review", "multi-agent review", or "comprehensive code analysis". 
---

# External Code Review

Multi-phase code review system using external AI models (Claude and Codex) with parallel specialized agents. Inspired by the ralphex autonomous review pipeline.

## Prerequisites

Required CLI tools:
- `claude` - Claude CLI (Anthropic)
- `codex` - Codex CLI (OpenAI) - optional but recommended

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

Example config:
```json
{
  "claude_model": "sonnet",
  "codex_model": "gpt-5.2-codex"
}
```

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

### Phase 2: External Review (Codex)

- Codex analyzes code with `read-only` sandbox
- Independent perspective from different model
- Claude evaluates Codex findings
- Categorize as: Valid / Invalid / Irrelevant

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

### 4. Run Codex External Review

```bash
python scripts/run_review.py codex --branch main
```

Or manually — check config for model override, otherwise use Codex default:

```bash
# If ~/.claude/external-code-review/config.json has codex_model set:
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

### 5. Evaluate Codex Findings

Pass Codex output to Claude for evaluation (add `--model <claude_model>` if configured):

```bash
claude -p "$(cat prompts/codex_eval.txt)" ${CLAUDE_MODEL:+--model "$CLAUDE_MODEL"}
```

For each Codex finding:
- **Valid** - Fix it
- **Invalid** - Document why
- **Irrelevant** - Skip (pre-existing, out of scope)

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
- `prompts/codex_eval.txt` - Codex findings evaluation
- `prompts/review_final.txt` - Phase 3 critical review

## Configuration Options

When invoking review, consider:

| Option | Default | Description |
|--------|---------|-------------|
| branch | main | Base branch for diff |
| max_iterations | 10 | Max review loops |
| claude_model | (claude default) | Claude model — uses Claude default unless overridden in `~/.claude/external-code-review/config.json` |
| codex_enabled | true | Run Codex phase |
| codex_model | (codex default) | Codex model — uses Codex default unless overridden in `~/.claude/external-code-review/config.json` |
| codex_sandbox | read-only | Codex sandbox mode |
| codex_reasoning | xhigh | Codex reasoning effort level |

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