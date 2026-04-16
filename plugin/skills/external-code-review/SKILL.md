---
name: external-code-review
description: Multi-phase code review using external AI models (Codex CLI, Gemini CLI, and Pi CLI) with parallel review agents. Use when user wants external model verification, multi-agent code analysis, or autonomous review with fixes. Triggers on requests like "external code review", "multi-agent review", "review with external models", "review with gemini", "review with pi", or "comprehensive code analysis".
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---

# External Code Review

Multi-phase code review system using external AI models (Codex, Gemini, and Pi) with parallel specialized agents.

External tools run in read-only/sandbox mode.

## Prerequisites

Required CLI tools (at least one external tool recommended):
- `codex` - Codex CLI (OpenAI) - optional
- `gemini` - Gemini CLI (Google) - optional, fallback when codex unavailable
- `pi` - [Pi CLI](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent) (multimodel) - optional, fallback when codex and gemini unavailable

## Configuration Hierarchy

Configuration is resolved with **project > user > built-in** precedence. This applies to both `config.json` and `agents/*.txt`:

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `./.claude/external-code-review/` | Project-local |
| 2 | `~/.claude/external-code-review/` | User-global |
| 3 (lowest) | Built-in (skill directory) | Default |

The first level that contains the resource wins — no merging between levels.

## Custom Review Agents

Place `.txt` files in `agents/` at either config level to override the built-in review agents. Each `.txt` file defines one agent — the filename (without extension) becomes the agent name, and the file content is the agent's review prompt.

Resolution order:
1. `./.claude/external-code-review/agents/*.txt` — project-local overrides
2. `~/.claude/external-code-review/agents/*.txt` — user-global overrides
3. Built-in `agents/` directory

If at least one `.txt` file exists at a higher-priority level, **all** lower-level agents are ignored.

## Model Configuration

Optional `config.json` at either config level (project takes precedence over user):

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

### Phase 1: First Review (Parallel Agents)

Launch specialized agents simultaneously using the Agent tool. Agent set is resolved at runtime:

- **Project overrides** (`./.claude/external-code-review/agents/*.txt`): Highest priority. If at least one `.txt` file exists, use only those agents.
- **User overrides** (`~/.claude/external-code-review/agents/*.txt`): Used if no project overrides exist. File name = agent name.
- **Built-in defaults** (when no overrides exist):

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
- Evaluate findings: fix valid issues, discuss disputed ones (up to 10 rounds per finding)
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

### 2. Run Phase 1: First Review (Agents)

**Agent resolution — project > user > built-in:**

1. Check if `./.claude/external-code-review/agents/` contains any `.txt` files (use Glob)
2. If not, check `~/.claude/external-code-review/agents/` for `.txt` files
3. If neither override directory has `.txt` files, use the built-in `agents/*.txt`
4. The first level with at least one `.txt` file wins — all lower levels are ignored

The file name (without `.txt`) becomes the agent name.

Launch ALL resolved agents in parallel using the Agent tool. Each agent receives the git diff and its specialized prompt.

```
project_dir = ./.claude/external-code-review/agents/
user_dir    = ~/.claude/external-code-review/agents/
builtin_dir = agents/   (relative to skill)

project_agents = Glob(project_dir/*.txt)
user_agents    = Glob(user_dir/*.txt)

if project_agents is not empty:
  agent_dir = project_dir
  agents = [filename without .txt for each file in project_agents]
elif user_agents is not empty:
  agent_dir = user_dir
  agents = [filename without .txt for each file in user_agents]
else:
  agent_dir = builtin_dir
  agents = [quality, implementation, testing, simplification, documentation]

For each agent in agents:
  Read <agent_dir>/<agent>.txt
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
- **Disputed** → You disagree with the finding but it raises a non-trivial point → enter Discussion (step 6)
- **Invalid/irrelevant** → Clearly wrong (wrong file, outdated info, style-only) → dismiss, pass as `--previous-context`

### 6. Discussion with External Reviewer

When you disagree with a non-trivial finding, engage in a structured debate instead of dismissing it:

1. Build the discussion context — a structured exchange of the finding and your counter-argument:
   ```
   ## Finding: <summary>
   **External reviewer:** <original finding with location and reasoning>
   **Claude (round 1):** <your counter-argument — reference specific code, explain why it's safe/correct>
   ```

2. Run the script in discussion mode:
   ```bash
   python scripts/run_review.py --branch main --discuss --discussion-context "<exchange>"
   ```

3. Parse the external reviewer's response. For each disputed finding they will respond with:
   - **WITHDRAW** — Dispute resolved. No action needed.
   - **MAINTAIN** — They provide new evidence. Read the referenced code, evaluate the new argument.
   - **COMPROMISE** — Narrower issue. Evaluate the reduced scope.

4. If the external reviewer maintains with new evidence you find compelling → fix the issue.
   If you still disagree → append your new counter-argument to the discussion context and run step 2 again.

5. Continue until all disputes are resolved (WITHDRAW/COMPROMISE/fix) or **max 10 discussion rounds** reached.

6. If max rounds reached without resolution, Claude makes the final call — dismiss or fix based on the accumulated evidence. Log the full exchange and the decision rationale in the review report.

**Important:** Only enter discussion for findings that are substantive and where the external reviewer might have a point. Clearly invalid findings (wrong file, misread code) should be dismissed via `--previous-context` without discussion.

### 7. Loop External Review

After fixing valid issues and resolving discussions:

If valid issues were fixed:
- Run the script again to verify fixes (external tool re-checks)

If all remaining findings were dismissed:
- Run script again with `--previous-context` containing dismissal explanations
- This prevents the external tool from re-reporting the same findings

If the external tool finds nothing new:
- Commit all accumulated fixes: `git commit -m "fix: address external review findings"`
- External review is complete

Max review iterations: 3 (separate from the 10-round discussion limit per finding).

### 8. Run Phase 3: Final Review

Same as Phase 1 but:
- If using **built-in agents**: only 2 agents (quality + implementation)
- If using **user override agents**: only agents whose names contain "quality" or "implementation" (case-insensitive). If no override agents match, run all override agents but with the final-review constraint below.
- Focus on **critical/major issues only**
- Ignore style/minor issues
- Max iterations: 3

### 9. Generate Review Report

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
- [DISCUSSED → FIXED] Finding + discussion summary (N rounds)
- [DISCUSSED → WITHDRAWN] Finding withdrawn by external reviewer (N rounds)
- [DISCUSSED → DISMISSED] Finding + full exchange + Claude's decision rationale (max rounds reached)

## Phase 3: Final Review
- No critical/major issues remaining

## Commits
- abc123: fix: address code review findings
- def456: fix: address external review findings
```

## Agent Definitions

Agent prompts are resolved with project > user > built-in precedence (see Configuration Hierarchy above).

**Project overrides**: `./.claude/external-code-review/agents/*.txt`
**User overrides**: `~/.claude/external-code-review/agents/*.txt`
**Built-in defaults**: `agents/` directory:

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
  --discuss           Discussion mode: debate disputed findings
  --discussion-context  The dispute exchange (findings + counter-arguments)
```

## Notes

- All orchestration happens in the user's Claude Code session — no permission escalation
- External tools run in read-only/sandbox mode (Codex: `--sandbox read-only`, Gemini: `-s`, Pi: `--tools read,grep,find,ls`)
- Always verify findings by reading actual code before fixing
- Run tests + linter after each fix batch
- Commit fixes with descriptive messages
- Pre-existing issues should still be fixed if found
