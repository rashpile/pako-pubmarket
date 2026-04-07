# Second Opinion — NDA

Strictly sanitized external AI consultation for NDA-restricted projects. All context is converted to pseudocode with company names obfuscated before the user manually copies it to an external chat. **No external CLI tools are used** — they cannot be trusted to not read local files.

**For open projects**, use [second-opinion](../second-opinion/) instead — it can send full context to external CLIs directly.

## Structure

```
second-opinion-nda/
├── SKILL.md                      # Skill definition (orchestrator)
├── README.md                     # This file
└── references/
    └── obfuscation-guide.md     # Sanitization rules, replacement tables, pseudocode examples
```

## How It Works

1. **Gather** — reads relevant code, conversation, and git diff
2. **Sanitize** — converts all code to pseudocode, replaces company names with placeholders
3. **Save** — writes sanitized document to `.second-opinion-nda-context.md`
4. **User approves** — reviews the file in IDE, confirms it's safe to share
5. **User copies** — manually pastes into external AI chat (ChatGPT, web Claude, etc.)
6. **User pastes back** — brings the external response back
7. **Validate** — checks inbound response for information leaks or suspicious inferences
8. **Evaluate** — critically assesses the advice, maps placeholders back to real names
9. **Report** — presents classified recommendations (agree/partially/disagree)

**No automated sending. Every outbound message requires explicit approval.**

## Sanitization

| What | Action |
|------|--------|
| Company/product/brand names | Replaced with `CompanyX`, `ProductA`, `ServiceAlpha` |
| Real code | Described in plain text; pseudocode only when structure/flow must be shown |
| Internal URLs/endpoints | Replaced with generic placeholders |
| Employee names/emails | Replaced with `developer@company` |
| File paths | Genericized (`src/auth/middleware` → `src/module-a/component`) |
| Database/table names | Replaced with `MainDatabase`, `UsersTable` |
| Config values/secrets | Removed entirely |
| Open-source lib names | **Kept as-is** (React, FastAPI, PostgreSQL, etc.) |

See [references/obfuscation-guide.md](references/obfuscation-guide.md) for full rules.

## Inbound Response Validation

When the user pastes back an external response, the skill checks for:
- References to details NOT present in the sanitized context
- Suspiciously accurate guesses about the company or product
- Requests to share real code or internal details

Issues are flagged before proceeding.

## Configuration

Stored at `~/.agents/second-opinion-nda/<project-dir-basename>/config.json`:

```json
{
  "prompt": ""
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `prompt` | (none) | Custom instructions prepended to every context |

Minimal config — no tool selection (manual only), no model config.

## Output File

Sanitized context is saved to `.second-opinion-nda-context.md` in the project root. If the file already exists, the skill warns and asks whether to overwrite or append.

## Safety Guarantees

1. **No external CLI tools** — manual copy-paste only
2. **Every outbound message requires approval** — no exceptions, no auto-approve
3. **Real code is never included** — pseudocode only
4. **Company names never exposed** — generic placeholders
5. **Inbound responses are validated** — checked for information leaks
6. **External advice is never trusted blindly** — critically evaluated and classified

## Quick Start

```bash
# "nda second opinion about the auth design"
# "safe consult about the API refactoring"
# /second-opinion-nda
```
