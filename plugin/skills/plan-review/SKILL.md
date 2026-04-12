---
name: plan-review
description: Multi-round plan review using parallel specialized agents. Validates implementation plans before code is written. Agents run in configurable rounds using N_name.txt naming convention. Produces annotated plan with inline findings. Optional external model review (Codex/Gemini/Pi). Triggers on "plan review", "review plan", "review my plan", "validate plan", "check plan", "plan-review --config", or "configure plan review".
allowed-tools: Bash(python *), Bash(mkdir *), Bash(mv *), Bash(rm *), Read, Write, Edit, Grep, Glob, Agent
---

# Plan Review

Multi-round implementation plan review using specialized agents with configurable round ordering.

Agents are dispatched in rounds (determined by `N_` prefix in filename), with orchestrator synthesis between rounds. The plan file is annotated inline with HTML comments containing findings.

## Prerequisites

Optional CLI tools for external review (at least one recommended):
- `codex` - Codex CLI (OpenAI)
- `gemini` - Gemini CLI (Google)
- `pi` - Pi CLI (multimodel)

## Configuration Hierarchy

Configuration is resolved with **project > user > built-in** precedence. This applies to both `config.json` and `agents/*.txt`:

| Priority | Location | Scope |
|----------|----------|-------|
| 1 (highest) | `./.claude/plan-review/` | Project-local |
| 2 | `~/.claude/plan-review/` | User-global |
| 3 (lowest) | Built-in (skill directory) | Default |

The first level that contains the resource wins — no merging between levels.

## Custom Review Agents

Place `.txt` files in `agents/` at either config level to override the built-in review agents. Each `.txt` file defines one agent — the filename (without extension) becomes the agent name, and the file content is the agent's review prompt.

### Naming Convention

Agent filenames follow the pattern `N_name.txt`:
- **N** is the round number (integer)
- **name** is the agent's identifier
- Agents with the same N run **in parallel**
- Rounds execute **sequentially** in ascending N order
- Files without a `N_` prefix are assigned to round 1

Resolution order:
1. `./.claude/plan-review/agents/*.txt` — project-local overrides
2. `~/.claude/plan-review/agents/*.txt` — user-global overrides
3. Built-in `agents/` directory

If at least one `.txt` file exists at a higher-priority level, **all** lower-level agents are ignored.

## Model Configuration

Optional `config.json` at either config level (project takes precedence over user):

```json
{
  "external_review": true,
  "external_model": "auto",
  "max_rounds": 3,
  "annotation_format": "html_comment"
}
```

| Field | Default | Effect |
|-------|---------|--------|
| `external_review` | `true` | Enable/disable external model review round |
| `external_model` | `"auto"` | `"auto"`, `"codex"`, `"gemini"`, or `"pi"` |
| `max_rounds` | `3` | Safety cap on round count from agent filenames |
| `annotation_format` | `"html_comment"` | Annotation format for plan file |

## Built-in Agents

| Agent | Round | Focus Area | Prompt File |
|-------|-------|------------|-------------|
| architect | 1 | Strategy, dependencies, risks, sequencing | `agents/1_architect.txt` |
| simplifier | 1 | Over-engineering, YAGNI, simpler alternatives | `agents/1_simplifier.txt` |
| conventions | 2 | Project patterns, infrastructure alignment | `agents/2_conventions.txt` |
| completionist | 2 | Gaps, error handling, testing, security | `agents/2_completionist.txt` |

## Mode Detection

If the user invoked this skill with `--config`, `configure`, or explicitly asked to configure/customize the plan review, enter **Config Mode** below. Otherwise, enter **Review Mode** (the normal Workflow).

---

## Config Mode

Interactive configuration wizard for customizing plan review agents in the current project.

### C1. Copy Built-in Agents to Project

Create `.claude/plan-review/agents/` in the project directory if it doesn't exist. Copy all built-in agent files from the skill's `agents/` directory into it.

```
mkdir -p .claude/plan-review/agents/
```

For each built-in agent file (`1_architect.txt`, `1_simplifier.txt`, `2_conventions.txt`, `2_completionist.txt`):
- Read the file from the skill's `agents/` directory
- Write it to `.claude/plan-review/agents/` with the same filename

Tell the user: "Copied N built-in agents to `.claude/plan-review/agents/`. These are now your project-local agents — you can customize them freely."

### C2. Create New Agents (Optional)

Ask the user: "Would you like to create any new custom review agents?"

If yes, for each new agent:
1. Ask for the agent's **name** (e.g., "security", "performance", "accessibility")
2. Ask for the agent's **focus area** — what should it review?
3. Help write the agent prompt following the same structure as built-in agents:
   - Section headings for review categories
   - Numbered checklist items under each section
   - "What to Report" section with finding format
   - "Report problems only - no positive observations" footer
4. Write the prompt to `.claude/plan-review/agents/<name>.txt` (no round prefix yet — ordering happens next)

Repeat until the user has no more agents to add.

### C3. Assign Round Ordering

List all agent files currently in `.claude/plan-review/agents/` (both copied and newly created).

Present them to the user as a numbered list:
```
Current agents:
1. architect — Strategy, dependencies, risks, sequencing
2. simplifier — Over-engineering, YAGNI, simpler alternatives
3. conventions — Project patterns, infrastructure alignment
4. completionist — Gaps, error handling, testing, security
5. security — (newly created)
```

For each agent, ask the user to assign a **round number** (1, 2, 3, etc.) or **skip** to remove it.

- Agents assigned the same round number will run in parallel
- Rounds execute sequentially in ascending order
- Present one agent at a time: "What round should **architect** run in? (1/2/3/skip)"

### C4. Apply Ordering

After all assignments:

1. **Rename** each kept agent file to include its round prefix: `N_name.txt`
2. **Delete** any agent files the user skipped
3. Show the final configuration:

```
Plan review agents configured:

Round 1 (parallel):
  - 1_architect.txt
  - 1_simplifier.txt

Round 2 (parallel):
  - 2_conventions.txt
  - 2_completionist.txt
  - 2_security.txt

Removed:
  - (none)

Agents saved to: .claude/plan-review/agents/
```

### C5. Config.json (Optional)

Ask the user if they want to customize `config.json` settings (external review, model, max rounds). If yes, create or update `.claude/plan-review/config.json` with their choices.

---

## Review Mode (Workflow)

### 1. Plan Discovery

Ask the user to provide the plan file path. The plan can be any format: markdown spec, structured plan with phases/tasks, or freeform text.

If the user invoked this skill with an argument (file path), use that directly.

Read the plan file content using the Read tool.

### 2. Agent Resolution

Resolve agents using the priority hierarchy:

```
project_dir = ./.claude/plan-review/agents/
user_dir    = ~/.claude/plan-review/agents/
builtin_dir = agents/   (relative to this skill)

project_agents = Glob(project_dir/*.txt)
user_agents    = Glob(user_dir/*.txt)

if project_agents is not empty:
  agent_dir = project_dir
  agent_files = project_agents
elif user_agents is not empty:
  agent_dir = user_dir
  agent_files = user_agents
else:
  agent_dir = builtin_dir
  agent_files = [1_architect.txt, 1_simplifier.txt, 2_conventions.txt, 2_completionist.txt]
```

### 3. Parse Round Groups

For each resolved agent file, extract the round number and agent name:

```
For each filename:
  if filename matches pattern "N_name.txt" (where N is integer):
    round = N
    name = everything after "N_"
  else:
    round = 1
    name = filename without .txt

Group agents by round number.
Sort rounds ascending.
Cap at max_rounds from config (default 3).
```

### 4. Execute Multi-Round Review

For each round N (ascending):

**4a. Dispatch agents in parallel:**

Launch ALL agents in round N simultaneously using the Agent tool. Each agent receives:
- The full plan content
- The agent's specialized prompt (from its `.txt` file)
- All consolidated findings from previous rounds (if round > 1)

```
For each agent in round N:
  Read <agent_dir>/<agent_file>
  Agent(
    description = "Plan review: <agent_name>",
    prompt = agent_prompt + "\n\nIMPLEMENTATION PLAN TO REVIEW:\n" + plan_content
             + (if round > 1: "\n\nFINDINGS FROM PREVIOUS ROUNDS:\n" + consolidated_findings)
  )
```

**4b. Orchestrator synthesis:**

After all agents in round N complete, read their outputs and synthesize:

1. Collect all findings from this round
2. Identify conflicts between reviewers (e.g., architect says X is needed, simplifier says X is over-engineered)
3. For conflicts: note both perspectives and flag for attention
4. For agreements: consolidate into unified findings
5. Produce a consolidated findings list that includes:
   - Each finding with its source agent
   - Conflict flags where reviewers disagree
   - Running total of all findings across rounds

This consolidated list becomes input for the next round.

### 5. Annotate Plan

After all internal rounds complete, annotate the original plan file with findings using HTML comments:

```markdown
## Phase 1: Setup database schema
<!-- [architect] Consider adding rollback strategy for migration failure -->
<!-- [simplifier] This could use the existing ORM migration tool instead of raw SQL -->
Create the initial database tables...
```

Rules for annotation:
- Place each annotation above the section it applies to
- Format: `<!-- [agent_name] finding text -->`
- If multiple findings apply to the same section, add multiple comment lines
- Use the Edit tool to insert annotations into the plan file
- Preserve all original plan content — only add, never remove

### 6. External Review (Optional)

Check config: if `external_review` is `false`, skip to step 7.

Run the external review script:

```bash
python scripts/run_plan_review.py --plan-file <path> --internal-findings "<consolidated_findings>"
```

Options:
```bash
# Force specific tool
python scripts/run_plan_review.py --plan-file <path> --external-tool gemini

# With internal findings context
python scripts/run_plan_review.py --plan-file <path> --internal-findings "..."
```

Parse the external tool's output. For each finding:
1. Evaluate whether it's valid — does it identify a real concern?
2. If valid, add it as an annotation: `<!-- [external:<tool_name>] finding text -->`
3. If invalid, dismiss it

### 7. Summary

Print a summary report:

```markdown
# Plan Review Summary

## Findings by Reviewer
- architect: N findings
- simplifier: N findings
- conventions: N findings
- completionist: N findings
- external (codex/gemini/pi): N findings (if run)

## Findings by Severity
- Critical: N
- Major: N
- Minor: N

## Conflicts Resolved
- [List any conflicts between reviewers and how they were resolved]

## Annotated Plan
Plan annotated at: <path to plan file>
```

## Notes

- All orchestration happens in the user's Claude Code session
- External tools run in read-only/sandbox mode
- Agent prompts are plain text — no special formatting required
- The plan file is modified in-place with HTML comment annotations
- Annotations are additive — original plan content is never removed
