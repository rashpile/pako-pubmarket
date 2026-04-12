# PaKo Public Plugin Marketplace

A public [Claude Code](https://docs.anthropic.com/claude-code) plugin marketplace with shared skills for automated code quality workflows.

## Installation

```bash
claude plugin add https://github.com/rashpile/pako-pubmarket
```

## Available Skills

### [external-code-review](plugin/skills/external-code-review/)

Automated multi-phase code review that catches bugs, security issues, and over-engineering by combining Claude with an independent external model (Codex, Gemini, or Pi). Finds issues, applies fixes, and commits them — iterating until clean.

**How it works:**

1. **First Review** — 5 specialized agents run in parallel (quality, implementation, testing, simplification, documentation), each analyzing your diff from a different angle
2. **External Review** — an independent model (Codex, Gemini, or Pi) reviews the same changes, and Claude evaluates its findings to filter false positives
3. **Final Review** — focused pass on critical/major issues only

**Why use it:**
- Multi-model review catches issues a single model misses
- Parallel agents cover more ground (security, tests, docs, over-engineering) in one pass
- Iterative loop: finds issues → fixes → re-verifies until clean
- Works with Codex, Gemini, Pi, or any combination — auto-detects what's installed

**Usage:** Ask Claude Code for an "external code review" or "multi-agent review". For a faster pass covering critical issues only, ask for a "quick external code review".

See the [full skill documentation](plugin/skills/external-code-review/README.md) for configuration, CLI options, and customization.

Agent prompts are sourced from [ralphex](https://github.com/umputun/ralphex) by [Umputun](https://github.com/umputun).

### [plan-review](plugin/skills/plan-review/)

Multi-round plan review that validates implementation plans before code is written. Specialized agents run in configurable rounds — catching architectural flaws, over-engineering, convention violations, and completeness gaps at the design stage.

**How it works:**

1. **Round 1** — architect + simplifier agents run in parallel, reviewing strategy and complexity
2. **Synthesis** — orchestrator merges findings, flags conflicts between reviewers
3. **Round 2** — conventions + completionist agents run in parallel, informed by round 1 findings
4. **External Review** (optional) — independent model (Codex, Gemini, or Pi) provides holistic assessment
5. **Annotation** — plan file annotated inline with HTML comments per finding

**Why use it:**
- Catch issues at the plan stage — cheaper than fixing them in code
- Multi-round review: later agents see earlier findings, catching cross-cutting concerns
- Configurable agent ordering via `N_name.txt` filename convention
- Interactive `--config` mode to customize agents per project
- Works with any plan format: markdown specs, structured plans, or freeform text

**Usage:** Ask Claude Code for a "plan review" or "review my plan". To customize agents, ask to "configure plan review" or use `--config`.

See the [full skill documentation](plugin/skills/plan-review/README.md) for configuration, agent customization, and the naming convention.

### [second-opinion](plugin/skills/second-opinion/)

Get a second opinion from external AI models. Gathers current task context with full code and sends it to Codex, Gemini, Claude CLI, or saves for manual copy-paste. External responses are critically evaluated — never relayed blindly.

| Mode | Use case |
|------|----------|
| **consult** | Send context to external CLI → evaluate response → assessed report |
| **gather** | Save context file for manual copy-paste to any external AI chat |
| **review** | External design/code review with focused review prompt |

**Usage:** Ask for a "second opinion", "discuss externally", or "get external review".

### [second-opinion-nda](plugin/skills/second-opinion-nda/)

Strictly sanitized external consultation for NDA-restricted projects. All code is converted to pseudocode, company names are obfuscated. **Manual copy-paste only** — no external CLI tools are used (they cannot be reliably restricted from reading local files).

**Key safety features:**
- No external CLI tools — manual copy-paste is the only delivery method
- Every outbound message requires explicit user approval
- Real code is never included — pseudocode only
- Inbound responses are validated for information leaks
- External advice is critically evaluated, never trusted blindly

**Usage:** Ask for a "nda second opinion" or "safe consult".

See full documentation: [second-opinion](plugin/skills/second-opinion/README.md) | [second-opinion-nda](plugin/skills/second-opinion-nda/README.md)

## Structure

```
.claude-plugin/marketplace.json    # Marketplace definition
plugin/
├── .claude-plugin/plugin.json     # Plugin metadata
└── skills/                        # Skill definitions
    ├── external-code-review/      # Multi-phase AI code review
    ├── plan-review/               # Multi-round plan review
    ├── second-opinion/            # External AI consultation (open)
    └── second-opinion-nda/        # NDA-safe consultation (manual only)
```

## License

MIT
