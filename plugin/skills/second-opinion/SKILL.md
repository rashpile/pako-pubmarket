---
name: second-opinion
description: Get a second opinion from external AI models. Gathers current task context and sends it to external AI models (Codex, Gemini, Claude CLI) or prepares it for manual copy-paste. Full context with real code is shared freely — use second-opinion-nda for restricted projects. 3 modes — consult (send to CLI automatically), gather (save context file for manual copy), review (external code/design review). Triggers on "second opinion", "discuss externally", "get external opinion", "ask another model", "what would codex/gemini think".
---

# Second Opinion

Get a second opinion from external AI models. Shares full project context (real code, real names) freely. For NDA-restricted projects, use **/second-opinion-nda** instead.

## Critical Rule: Never Blindly Trust External Response

**You are the final decision-maker, not the external model.** When processing the external model's response:

1. **Critically evaluate** every suggestion — does it actually apply to this codebase and context?
2. **Filter out** generic advice, hallucinated assumptions, and recommendations that contradict known constraints
3. **Verify** specific claims by checking the actual code/docs before passing them to the user
4. **Classify** each point: agree (with reasoning), partially agree (what to adapt), or disagree (why it's wrong)
5. **Present a final assessed report** to the user — not a raw dump of the external response

## Mode Selection

Determine mode from user's request or ask:

| Mode | Trigger | Flow |
|------|---------|------|
| **consult** | "discuss with external model", "get opinion from codex" | Gather → save → approve → send via CLI → evaluate → report |
| **gather** | "prepare context", "I'll paste it myself" | Gather → save → approve → done |
| **review** | "external review", "get review from another model" | Gather diff/code → save → approve → send → evaluate → report |

If `.second-opinion-context.md` already exists, warn: "Context file already exists — overwrite or append?" 

Default to **gather** if user mentions manual copy.

## Step 1: Gather Context

**Required checklist — always include:**
- [ ] Current task/goal stated clearly
- [ ] Current blocker or decision point
- [ ] Constraints (performance, compatibility, deadlines)
- [ ] Key files involved (full content for 1-3 files max, summarize the rest)
- [ ] Specific questions to answer

**Include when relevant:**
- [ ] Git diff (`git diff` or `git diff --staged`) for recent changes
- [ ] Dependencies from package files (package.json, go.mod, requirements.txt, etc.)
- [ ] Architecture context if the question is structural
- [ ] For **review** mode: `git diff main...HEAD` for full branch changes

## Step 2: Generate Context Document

Include real code, real file paths, real project names — no obfuscation.

**consult / gather:**
```markdown
# External Consultation: [Topic]

## Goal
[What advice is needed]

## Background
[Project context]

## Current Approach
[Real code]

## Technologies Used
[Stack and dependencies]

## Specific Questions
1. [Question]
```

**review:**
```markdown
# External Review Request

## What to Review
[Description of component/design/approach]

## Context
[Background]

## Implementation
[Real code]

## Technologies & Constraints
[Stack, performance/scale requirements]

## Review Focus
- [Specific areas to evaluate]
```

If config has a `prompt` field, prepend it as custom instructions.

## Step 3: Save & Approve

Save to `.second-opinion-context.md` in project root.

**If file already exists and not empty**, warn user: "File .second-opinion-context.md already has content. Overwrite or append?"

For append (continuing discussion), add a separator:
```markdown
---
# Follow-up (timestamp)
...
```

First send always requires approval. Follow-ups can proceed without re-approval.

```
"Context saved to .second-opinion-context.md — review and confirm."
Options: "Approved — send it", "Needs edits — I'll update the file", "Cancel"
```

## Step 4: Deliver

### gather mode
File is saved. User copies from it. Done.

If user pastes back a response, apply the critical evaluation rule before interpreting.

### consult / review modes

Load config and detect tools:

```bash
python scripts/detect_tools.py load-config "<project-dir-basename>"
python scripts/detect_tools.py detect
```

If config has `preferred_tool` — use it. Otherwise ask:

```
"Which external tool?"
Options: [detected CLI tools] + "Manual copy" + "Custom CLI"
```

Save preference and send (pass file path — the script reads it):
```bash
python scripts/run_external.py <tool> .second-opinion-context.md [model] [custom_cmd]
```

## Step 5: Follow-up Q&A

If external model asks questions, draft answers with full context and send. No re-approval needed after first send.

For **gather** mode: if user pastes back questions, prepare answers for them to copy.

## Step 6: Evaluate & Report

**Do NOT relay external response verbatim.** Critically evaluate:

1. Cross-check claims against the actual codebase
2. Classify each recommendation:
   - **Agree** — valid and applicable, explain why
   - **Partially agree** — has merit but needs adaptation
   - **Disagree** — wrong, inapplicable, or based on bad assumptions
3. Present assessed report:

```markdown
## Second Opinion Report

### Summary
[1-2 sentence assessment]

### Recommendations

#### Agreed
- [Point] — [why and how to apply]

#### Partially Agreed  
- [Point] — [what to adapt, why]

#### Disagreed
- [Point] — [why it's wrong]

### Suggested Next Steps
- [Actionable items]
```

## Config

Stored at `~/.agents/second-opinion/<project-dir-basename>/config.json`:

```json
{
  "preferred_tool": "codex|gemini|claude|custom|manual",
  "model": {"codex": "", "gemini": "", "claude": ""},
  "custom_cmd": "my-script {prompt_file}",
  "default_mode": "gather",
  "prompt": ""
}
```

- `model` — per-tool model overrides
- `prompt` — custom instructions prepended to every context document
