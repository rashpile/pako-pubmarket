# External Code Review

Multi-phase code review system using external AI models (Claude and Codex) with parallel specialized agents. Inspired by the [ralphex](https://github.com/anthropics/ralphex) autonomous review pipeline.

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
│   ├── codex_eval.txt            # Phase 2: Codex evaluation
│   └── review_final.txt          # Phase 3: Critical issues (2 agents)
└── scripts/
    └── run_review.py             # Review orchestration script
```

## Prerequisites

Install and configure these CLI tools:

- **claude** - [Claude CLI](https://docs.anthropic.com/claude-code) (Anthropic) - required
- **codex** - [Codex CLI](https://github.com/openai/codex) (OpenAI) - optional but recommended

## Model Configuration

Both CLIs use their defaults unless overridden in `~/.claude/external-code-review/config.json`:

```json
{
  "claude_model": "sonnet",
  "codex_model": "gpt-5.2-codex"
}
```

Fields are optional — omit to use the CLI default.

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

### Phase 2: Codex External Review

- Codex analyzes code in `read-only` sandbox (uses Codex default model, configurable via config)
- Provides independent perspective from a different model
- Claude evaluates Codex findings and categorizes as:
  - **Valid** - Fix the issue
  - **Invalid** - Explain why it doesn't apply
  - **Irrelevant** - Out of scope or pre-existing

### Phase 3: Final Review (2 Agents)

- Only **quality** and **implementation** agents
- Focuses on **critical/major issues only**
- Ignores style and minor issues

## Signal-Based Completion

The review loop uses signals to determine when to stop:

| Signal | Meaning |
|--------|---------|
| `<<<REVIEW_DONE>>>` | Zero issues found this iteration |
| `<<<CODEX_REVIEW_DONE>>>` | Codex found no issues |
| `<<<REVIEW_FAILED>>>` | Cannot fix issues (needs human help) |

**Important**: `REVIEW_DONE` means "found zero issues", NOT "finished fixing". If issues were fixed, the loop continues to verify the fixes didn't introduce new problems.

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
  --no-codex          Disable Codex external review
  --codex-model       Codex model override (default: codex default)
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
- `codex_eval.txt` - Change how Codex findings are evaluated
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
# 🤖 Starting CODEX REVIEW phase
# ... codex analysis ...
# ✅ Codex review complete!
# 🎯 Starting FINAL REVIEW phase (2 agents)
# ... final verification ...
# ✅ Final review complete - no critical issues!
# 🎉 FULL REVIEW pipeline complete!
```

## Notes

- Pre-existing issues (linter errors, failed tests) are fixed too
- Codex runs in read-only sandbox for safety
- Each iteration verifies previous fixes didn't introduce new issues
- Tests and linter must pass after each fix batch