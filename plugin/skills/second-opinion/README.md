# Second Opinion

Get a second opinion from external AI models. Gathers current task context with full code and project details, then sends to external AI CLIs or saves for manual copy-paste.

**For NDA-restricted projects**, use [second-opinion-nda](../second-opinion-nda/) instead — it sanitizes all context and only supports manual copy-paste.

## Structure

```
second-opinion/
├── SKILL.md                      # Skill definition (orchestrator)
├── README.md                     # This file
└── scripts/
    ├── detect_tools.py           # CLI tool detection and config management
    └── run_external.py           # External tool runner (Codex/Gemini/Claude/custom)
```

## Modes

| Mode | Trigger | What it does |
|------|---------|-------------|
| **consult** | "discuss with external model", "get opinion from codex" | Gather → save → approve → send via CLI → evaluate → report |
| **gather** | "prepare context for chat", "I'll paste it myself" | Gather → save to file → done |
| **review** | "external review", "get review from another model" | Gather diff → save → approve → send → evaluate → report |

## Prerequisites

Install at least one external CLI tool for automated modes:

- **codex** - [Codex CLI](https://github.com/openai/codex) (OpenAI)
- **gemini** - [Gemini CLI](https://github.com/google-gemini/gemini-cli) (Google)
- **claude** - [Claude Code CLI](https://docs.anthropic.com/claude-code) (Anthropic)

For **gather** mode, no external tools are needed.

## Key Feature: Critical Evaluation

External responses are never relayed verbatim. The skill:
1. Cross-checks claims against the actual codebase
2. Classifies each recommendation: **Agree**, **Partially Agree**, or **Disagree**
3. Presents an assessed report with actionable next steps

## Configuration

Stored at `~/.agents/second-opinion/<project-dir-basename>/config.json`:

```json
{
  "preferred_tool": "codex",
  "model": {"codex": "", "gemini": "", "claude": ""},
  "custom_cmd": "",
  "default_mode": "gather",
  "prompt": ""
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `preferred_tool` | (ask) | `codex`, `gemini`, `claude`, `custom`, or `manual` |
| `model` | CLI defaults | Per-tool model overrides |
| `custom_cmd` | (none) | Custom CLI command; `{prompt_file}` is replaced with temp file path |
| `default_mode` | `gather` | Default mode when not specified |
| `prompt` | (none) | Custom instructions prepended to every context |

## Output File

Context is saved to `.second-opinion-context.md` in the project root. If the file already exists, the skill warns and asks whether to overwrite or append.

## Quick Start

```bash
# "get a second opinion on the auth refactoring"
# "second opinion from codex about the caching approach"
# "gather context for external chat"
# /second-opinion
```
