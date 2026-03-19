# PaKo Public Plugin Marketplace

A public [Claude Code](https://docs.anthropic.com/claude-code) plugin marketplace with shared skills for automated code quality workflows.

## Installation

```bash
claude plugin add https://github.com/rashpile/pako-pubmarket
```

## Available Skills

### [external-code-review](plugin/skills/external-code-review/)

Automated multi-phase code review that catches bugs, security issues, and over-engineering by combining Claude with an independent external model (Codex or Gemini). Runs on your feature branch and commits fixes automatically.

**How it works:**

1. **First Review** — 5 specialized agents run in parallel (quality, implementation, testing, simplification, documentation), each analyzing your diff from a different angle
2. **External Review** — an independent model (Codex or Gemini) reviews the same changes, and Claude evaluates its findings to filter false positives
3. **Final Review** — focused pass on critical/major issues only

**Why use it:**
- Multi-model review catches issues a single model misses
- Parallel agents cover more ground (security, tests, docs, over-engineering) in one pass
- Iterative loop: finds issues → fixes → re-verifies until clean
- Works with Codex, Gemini, or both — auto-detects what's installed

**Usage:** Ask Claude Code for an "external code review" or "multi-agent review". For a faster pass covering critical issues only, ask for a "quick external code review".

Agent prompts are sourced from [ralphex](https://github.com/umputun/ralphex) by [Umputun](https://github.com/umputun).

## Structure

```
.claude-plugin/marketplace.json    # Marketplace definition
plugin/
├── .claude-plugin/plugin.json     # Plugin metadata
└── skills/                        # Skill definitions
    └── external-code-review/      # Multi-phase AI code review
```

## License

MIT
