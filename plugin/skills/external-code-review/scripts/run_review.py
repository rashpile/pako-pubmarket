#!/usr/bin/env python
"""
External Review Tool Runner

Runs an external AI review tool (Codex, Gemini, or Pi) against code changes
and prints findings to stdout. Designed to be called by the skill orchestrator.

Usage:
    python run_review.py --branch main
    python run_review.py --branch main --external-tool gemini
    python run_review.py --branch main --external-tool pi --pi-model "anthropic/claude-sonnet-4-20250514"
    python run_review.py --branch main --previous-context "dismissed findings..."
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ExternalTool(Enum):
    CODEX = "codex"
    GEMINI = "gemini"
    PI = "pi"


def _detect_external_tool(preferred: str = "auto") -> ExternalTool:
    """Detect which external review tool to use.

    If preferred is a specific tool name (codex/gemini/pi), return it
    directly without checking availability (will fail with clear error
    if the tool is not installed).

    If preferred is 'auto', probe for installed tools in order:
    codex -> gemini -> pi. If none found, return codex (will fail with
    clear error when run).
    """
    _tool_map = {
        "codex": ExternalTool.CODEX,
        "gemini": ExternalTool.GEMINI,
        "pi": ExternalTool.PI,
    }
    if preferred in _tool_map:
        return _tool_map[preferred]

    # Auto-detect: probe in priority order (codex -> gemini -> pi)
    for name, tool in _tool_map.items():
        try:
            result = subprocess.run(
                [name, "--version"], capture_output=True, timeout=10
            )
            if result.returncode == 0:
                return tool
        except (OSError, subprocess.TimeoutExpired):
            pass

    # None found, return codex (will produce a clear error when run)
    return ExternalTool.CODEX


@dataclass
class ReviewConfig:
    branch: str = "main"
    external_tool: str = "auto"  # "auto", "codex", "gemini", or "pi"
    codex_model: str = "gpt-5.2-codex"
    codex_sandbox: str = "read-only"
    codex_reasoning: str = "xhigh"
    gemini_model: str = ""  # empty = use gemini default
    pi_model: str = ""  # empty = use pi default
    pi_thinking: str = "high"  # thinking level: off, minimal, low, medium, high, xhigh
    pi_options: Optional[list[str]] = None  # additional CLI options
    previous_context: str = ""  # dismissed findings from prior iterations
    discussion_mode: bool = False  # discussion mode: debate disputed findings
    discussion_context: str = ""  # the dispute: finding + counter-argument exchange


class ExternalReviewRunner:
    """Runs external AI review tools and prints findings."""

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.external_tool_resolved = _detect_external_tool(config.external_tool)

    def _log(self, message: str, prefix: str = "🔍"):
        """Log a message to stderr (keep stdout clean for findings)."""
        print(f"{prefix} {message}", file=sys.stderr)

    def _run_command(self, cmd: list, timeout: int = 600) -> tuple[str, bool]:
        """Run a shell command and return (stdout, success). Stderr logged separately."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            if result.stderr.strip():
                self._log(f"stderr: {result.stderr.strip()[:500]}", "⚠️")
            return result.stdout.strip(), result.returncode == 0
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s", False
        except FileNotFoundError:
            return f"Command not found: {cmd[0]}", False
        except Exception as e:
            return str(e), False

    def _get_git_diff(self) -> str:
        """Get git diff against base branch. Returns None on error, empty string if no changes."""
        output, success = self._run_command(
            ["git", "diff", f"{self.config.branch}...HEAD"]
        )
        if not success:
            self._log(f"git diff failed: {output}", "❌")
            return None
        return output

    def _build_review_prompt(self, diff: str) -> str:
        """Build the review prompt for external tools."""
        ctx_section = ""
        if self.config.previous_context:
            ctx_section = f"""

## Previous Review Context

The following findings were reported in prior iterations and dismissed by the evaluator.
Do NOT re-report these unless you have new evidence:

{self.config.previous_context}
"""

        if self.config.discussion_mode:
            return self._build_discussion_prompt(diff)

        return f"""Review the following code changes for bugs, security issues, and quality problems.

CODE CHANGES:
{diff}

Report each issue with:
- Location: file and line
- Issue: description
- Impact: severity
- Fix: suggestion

Report problems only - no positive observations.{ctx_section}"""

    def _build_discussion_prompt(self, diff: str) -> str:
        """Build the discussion prompt for debating disputed findings."""
        return f"""You are in a code review discussion. Another reviewer (Claude) disagrees with some of your findings.

Review the counter-arguments below carefully. For each disputed finding, respond with ONE of:

1. **WITHDRAW** — You accept the counter-argument. State why briefly.
2. **MAINTAIN** — You still believe this is a real issue. Provide NEW evidence or reasoning not already presented. Reference specific code paths, edge cases, or conditions that support your position.
3. **COMPROMISE** — You partially agree. Clarify the narrower scope of the issue that still stands.

Be rigorous. If the counter-argument is valid, withdraw. If you have genuine new evidence, present it. Do NOT simply restate your original finding.

CODE CHANGES:
{diff}

## Discussion so far

{self.config.discussion_context}

Respond to each disputed finding using the format above."""

    def run_codex(self, prompt: str) -> tuple[str, bool]:
        """Run Codex CLI."""
        self._log("Running Codex review...", "🤖")
        cmd = [
            "codex",
            "exec",
            "--sandbox",
            self.config.codex_sandbox,
        ]
        if self.config.codex_model:
            cmd.extend(["-c", f'model="{self.config.codex_model}"'])
        cmd.extend(
            ["-c", f"model_reasoning_effort={self.config.codex_reasoning}", prompt]
        )
        return self._run_command(cmd)

    def run_gemini(self, prompt: str) -> tuple[str, bool]:
        """Run Gemini CLI."""
        self._log("Running Gemini review...", "💎")
        cmd = ["gemini", "-p", prompt, "-s", "-o", "text"]
        if self.config.gemini_model:
            cmd.extend(["-m", self.config.gemini_model])
        return self._run_command(cmd)

    def run_pi(self, prompt: str) -> tuple[str, bool]:
        """Run Pi CLI."""
        self._log("Running Pi review...", "🥧")
        cmd = ["pi", "-p", prompt]
        cmd.extend(["--thinking", self.config.pi_thinking])
        if self.config.pi_model:
            cmd.extend(["--model", self.config.pi_model])
        if self.config.pi_options:
            cmd.extend(self.config.pi_options)
        # Safety flags last — override any user options
        cmd.extend(["--tools", "read,grep,find,ls", "--no-extensions", "--no-skills"])
        return self._run_command(cmd)

    def run(self) -> bool:
        """Run the external review and print findings to stdout."""
        diff = self._get_git_diff()
        if diff is None:
            return False  # git error, already logged
        if not diff:
            self._log("No diff found — nothing to review", "⚠️")
            return True

        prompt = self._build_review_prompt(diff)
        tool = self.external_tool_resolved
        tool_name = tool.value

        self._log(f"Using {tool_name}", "🔍")

        if tool == ExternalTool.GEMINI:
            output, success = self.run_gemini(prompt)
        elif tool == ExternalTool.PI:
            output, success = self.run_pi(prompt)
        else:
            output, success = self.run_codex(prompt)

        if not success:
            self._log(f"{tool_name} failed: {output}", "❌")
            return False

        # Print findings to stdout (skill reads this)
        print(output)
        return True


def _validate_pi_options(raw: Optional[list]) -> Optional[list[str]]:
    """Validate pi_options against denylist."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(o, str) for o in raw):
        print(
            "Warning: pi_options must be a list of strings, ignoring", file=sys.stderr
        )
        return None

    _denied_prefixes = (
        "--tools",
        "--no-tools",
        "--no-extensions",
        "--no-skills",
        "--extensions",
        "--skills",
        "--prompt",
        "--system-prompt",
        "--append-system-prompt",
        "--model",
        "--thinking",
        "--extension",
        "--skill",
        "--prompt-template",
        "--no-prompt-templates",
    )
    _denied_exact = {"--", "-p", "-e", "-ne", "-ns", "-np"}
    has_denied = any(
        o.strip() in _denied_exact
        or any(o.strip().startswith(p) for p in _denied_prefixes)
        for o in raw
    )
    if has_denied:
        print(
            "Warning: pi_options contains restricted flags, ignoring", file=sys.stderr
        )
        return None
    return raw


def main():
    parser = argparse.ArgumentParser(
        description="Run external AI review tool (Codex/Gemini/Pi) and print findings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--branch", "-b", default="main", help="Base branch for diff (default: main)"
    )
    parser.add_argument(
        "--external-tool",
        default=None,
        choices=["auto", "codex", "gemini", "pi"],
        help="External tool: auto (codex->gemini->pi), codex, gemini, or pi",
    )
    parser.add_argument("--codex-model", default=None, help="Codex model to use")
    parser.add_argument("--gemini-model", default=None, help="Gemini model to use")
    parser.add_argument(
        "--pi-model",
        default=None,
        help="Pi model (e.g. 'google/gemini-2.5-pro', 'anthropic/claude-sonnet-4-20250514')",
    )
    parser.add_argument(
        "--pi-thinking",
        default=None,
        choices=["off", "minimal", "low", "medium", "high", "xhigh"],
        help="Pi thinking level (default: high)",
    )
    parser.add_argument(
        "--pi-options",
        default=None,
        help="Additional Pi CLI options as JSON array (e.g. '[\"--verbose\"]')",
    )
    parser.add_argument(
        "--previous-context",
        default="",
        help="Dismissed findings from prior iterations (passed to external tool)",
    )
    parser.add_argument(
        "--discuss",
        action="store_true",
        default=False,
        help="Discussion mode: debate disputed findings with counter-arguments",
    )
    parser.add_argument(
        "--discussion-context",
        default="",
        help="The dispute exchange: findings + counter-arguments so far",
    )

    args = parser.parse_args()

    # Load config.json — project > user > empty (first found wins, no merging)
    _config_candidates = [
        Path(".claude") / "external-code-review" / "config.json",  # project-local
        Path.home() / ".claude" / "external-code-review" / "config.json",  # user-global
    ]
    file_config = {}
    for config_path in _config_candidates:
        if config_path.exists():
            try:
                file_config = json.loads(config_path.read_text())
                print(f"Loaded config from {config_path}", file=sys.stderr)
                break
            except Exception as e:
                print(
                    f"Warning: could not load config from {config_path}: {e}",
                    file=sys.stderr,
                )

    # Validate pi_options (CLI arg is JSON string, config is list)
    cli_pi_options = None
    if args.pi_options is not None:
        try:
            cli_pi_options = json.loads(args.pi_options)
        except json.JSONDecodeError:
            print(
                "Warning: --pi-options must be a JSON array, ignoring", file=sys.stderr
            )
    raw_pi_options = _validate_pi_options(
        cli_pi_options
        if cli_pi_options is not None
        else file_config.get("pi_options", None)
    )

    # Validate pi_thinking
    _valid_thinking = {"off", "minimal", "low", "medium", "high", "xhigh"}
    pi_thinking_val = (
        args.pi_thinking
        if args.pi_thinking is not None
        else file_config.get("pi_thinking", "high")
    )
    if pi_thinking_val not in _valid_thinking:
        print(
            f"Warning: invalid pi_thinking '{pi_thinking_val}', using 'high'",
            file=sys.stderr,
        )
        pi_thinking_val = "high"

    # Validate external_tool
    _valid_tools = {"auto", "codex", "gemini", "pi"}
    ext_tool_val = (
        args.external_tool
        if args.external_tool is not None
        else file_config.get("external_tool", "auto")
    )
    if ext_tool_val not in _valid_tools:
        print(
            f"Warning: invalid external_tool '{ext_tool_val}', using 'auto'",
            file=sys.stderr,
        )
        ext_tool_val = "auto"

    config = ReviewConfig(
        branch=args.branch,
        external_tool=ext_tool_val,
        codex_model=args.codex_model
        if args.codex_model is not None
        else file_config.get("codex_model", "gpt-5.2-codex"),
        gemini_model=args.gemini_model
        if args.gemini_model is not None
        else file_config.get("gemini_model", ""),
        pi_model=args.pi_model
        if args.pi_model is not None
        else file_config.get("pi_model", ""),
        pi_thinking=pi_thinking_val,
        pi_options=raw_pi_options,
        previous_context=args.previous_context,
        discussion_mode=args.discuss,
        discussion_context=args.discussion_context,
    )

    runner = ExternalReviewRunner(config)
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
