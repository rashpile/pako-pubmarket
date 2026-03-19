# PaKo Public Plugin Marketplace

A public [Claude Code](https://docs.anthropic.com/claude-code) plugin marketplace with shared skills.

## Installation

Add this marketplace to your Claude Code configuration:

```bash
claude plugin add https://github.com/rashpile/pako-pubmarket
```

## Available Skills

### [external-code-review](plugin/skills/external-code-review/)

Multi-phase code review using external AI models (Claude CLI and Codex CLI) with parallel specialized agents.

- **Phase 1**: 5 parallel agents (quality, implementation, testing, simplification, documentation)
- **Phase 2**: Independent Codex review with Claude evaluation
- **Phase 3**: Final review — critical/major issues only
- Supports quick review mode (Phase 3 only)
- Configurable models via `~/.claude/external-code-review/config.json`

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