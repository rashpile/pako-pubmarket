#!/usr/bin/env python3
"""
External Plan Review Tool Runner

Runs an external AI review tool (Codex, Gemini, or Pi) against an implementation
plan and prints findings to stdout. Designed to be called by the skill orchestrator.

Usage:
    python run_plan_review.py --plan-file path/to/plan.md
    python run_plan_review.py --plan-file plan.md --external-tool gemini
    python run_plan_review.py --plan-file plan.md --internal-findings "findings..."
"""

import subprocess
import sys
import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ExternalTool(Enum):
    CODEX = "codex"
    GEMINI = "gemini"
    PI = "pi"


def _detect_external_tool(preferred: str = "auto") -> ExternalTool:
    """Detect which external review tool to use.

    If preferred is a specific tool name (codex/gemini/pi), return it
    directly without checking availability.

    If preferred is 'auto', probe for installed tools in order:
    codex -> gemini -> pi.
    """
    _tool_map = {"codex": ExternalTool.CODEX, "gemini": ExternalTool.GEMINI, "pi": ExternalTool.PI}
    if preferred in _tool_map:
        return _tool_map[preferred]

    for name, tool in _tool_map.items():
        try:
            result = subprocess.run([name, "--version"], capture_output=True, timeout=10)
            if result.returncode == 0:
                return tool
        except (OSError, subprocess.TimeoutExpired):
            pass

    return ExternalTool.CODEX


@dataclass
class PlanReviewConfig:
    plan_file: str = ""
    external_tool: str = "auto"
    codex_model: str = "gpt-5.2-codex"
    codex_sandbox: str = "read-only"
    codex_reasoning: str = "xhigh"
    gemini_model: str = ""
    pi_model: str = ""
    pi_thinking: str = "high"
    pi_options: Optional[list[str]] = None
    internal_findings: str = ""  # consolidated findings from internal rounds


class ExternalPlanReviewRunner:
    """Runs external AI review tools against implementation plans."""

    def __init__(self, config: PlanReviewConfig):
        self.config = config
        self.external_tool_resolved = _detect_external_tool(config.external_tool)

    def _log(self, message: str, prefix: str = "🔍"):
        print(f"{prefix} {message}", file=sys.stderr)

    def _run_command(self, cmd: list, timeout: int = 600) -> tuple[str, bool]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
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

    def _read_plan(self) -> Optional[str]:
        plan_path = Path(self.config.plan_file)
        if not plan_path.exists():
            self._log(f"Plan file not found: {plan_path}", "❌")
            return None
        return plan_path.read_text()

    def _build_review_prompt(self, plan_content: str) -> str:
        findings_section = ""
        if self.config.internal_findings:
            findings_section = f"""

## Internal Review Findings

The following findings were produced by internal review agents. Evaluate whether
they are valid, and identify anything significant they missed:

{self.config.internal_findings}
"""

        return f"""Review the following implementation plan holistically.

IMPLEMENTATION PLAN:
{plan_content}
{findings_section}
Assess:
1. Will this plan achieve its stated goal? Rate confidence: high/medium/low
2. Are there fundamental flaws in the approach?
3. Did internal reviewers miss anything significant?
4. Are there risks that could cause the implementation to fail?

For each finding report:
- Section: which part of the plan
- Issue: clear description
- Impact: severity (critical/major/minor)
- Suggestion: specific recommendation

Report problems only - no positive observations."""

    def run_codex(self, prompt: str) -> tuple[str, bool]:
        self._log("Running Codex plan review...", "🤖")
        cmd = [
            "codex", "exec",
            "--sandbox", self.config.codex_sandbox,
        ]
        if self.config.codex_model:
            cmd.extend(["-c", f'model="{self.config.codex_model}"'])
        cmd.extend([
            "-c", f"model_reasoning_effort={self.config.codex_reasoning}",
            prompt
        ])
        return self._run_command(cmd)

    def run_gemini(self, prompt: str) -> tuple[str, bool]:
        self._log("Running Gemini plan review...", "💎")
        cmd = ["gemini", "-p", prompt, "-s", "-o", "text"]
        if self.config.gemini_model:
            cmd.extend(["-m", self.config.gemini_model])
        return self._run_command(cmd)

    def run_pi(self, prompt: str) -> tuple[str, bool]:
        self._log("Running Pi plan review...", "🥧")
        cmd = ["pi", "-p", prompt]
        cmd.extend(["--thinking", self.config.pi_thinking])
        if self.config.pi_model:
            cmd.extend(["--model", self.config.pi_model])
        if self.config.pi_options:
            cmd.extend(self.config.pi_options)
        cmd.extend(["--tools", "read,grep,find,ls", "--no-extensions", "--no-skills"])
        return self._run_command(cmd)

    def run(self) -> bool:
        plan_content = self._read_plan()
        if plan_content is None:
            return False
        if not plan_content.strip():
            self._log("Plan file is empty — nothing to review", "⚠️")
            return True

        prompt = self._build_review_prompt(plan_content)
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

        print(output)
        return True


def _validate_pi_options(raw: Optional[list]) -> Optional[list[str]]:
    if raw is None:
        return None
    if not isinstance(raw, list) or not all(isinstance(o, str) for o in raw):
        print("Warning: pi_options must be a list of strings, ignoring", file=sys.stderr)
        return None

    _denied_prefixes = (
        "--tools", "--no-tools", "--no-extensions", "--no-skills",
        "--extensions", "--skills",
        "--prompt", "--system-prompt", "--append-system-prompt",
        "--model", "--thinking",
        "--extension", "--skill", "--prompt-template",
        "--no-prompt-templates",
    )
    _denied_exact = {"--", "-p", "-e", "-ne", "-ns", "-np"}
    has_denied = any(
        o.strip() in _denied_exact or any(o.strip().startswith(p) for p in _denied_prefixes)
        for o in raw
    )
    if has_denied:
        print("Warning: pi_options contains restricted flags, ignoring", file=sys.stderr)
        return None
    return raw


def main():
    parser = argparse.ArgumentParser(
        description="Run external AI plan review tool (Codex/Gemini/Pi) and print findings",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--plan-file", "-f", required=True,
                        help="Path to the plan file to review")
    parser.add_argument("--external-tool", default=None,
                        choices=["auto", "codex", "gemini", "pi"],
                        help="External tool: auto (codex->gemini->pi), codex, gemini, or pi")
    parser.add_argument("--codex-model", default=None,
                        help="Codex model to use")
    parser.add_argument("--gemini-model", default=None,
                        help="Gemini model to use")
    parser.add_argument("--pi-model", default=None,
                        help="Pi model (e.g. 'google/gemini-2.5-pro')")
    parser.add_argument("--pi-thinking", default=None,
                        choices=["off", "minimal", "low", "medium", "high", "xhigh"],
                        help="Pi thinking level (default: high)")
    parser.add_argument("--pi-options", default=None,
                        help="Additional Pi CLI options as JSON array")
    parser.add_argument("--internal-findings", default="",
                        help="Consolidated findings from internal review rounds")

    args = parser.parse_args()

    # Load config.json — project > user > empty
    _config_candidates = [
        Path(".claude") / "plan-review" / "config.json",
        Path.home() / ".claude" / "plan-review" / "config.json",
    ]
    file_config = {}
    for config_path in _config_candidates:
        if config_path.exists():
            try:
                file_config = json.loads(config_path.read_text())
                print(f"Loaded config from {config_path}", file=sys.stderr)
                break
            except Exception as e:
                print(f"Warning: could not load config from {config_path}: {e}", file=sys.stderr)

    cli_pi_options = None
    if args.pi_options is not None:
        try:
            cli_pi_options = json.loads(args.pi_options)
        except json.JSONDecodeError:
            print("Warning: --pi-options must be a JSON array, ignoring", file=sys.stderr)
    raw_pi_options = _validate_pi_options(
        cli_pi_options if cli_pi_options is not None else file_config.get("pi_options", None)
    )

    _valid_thinking = {"off", "minimal", "low", "medium", "high", "xhigh"}
    pi_thinking_val = args.pi_thinking if args.pi_thinking is not None else file_config.get("pi_thinking", "high")
    if pi_thinking_val not in _valid_thinking:
        print(f"Warning: invalid pi_thinking '{pi_thinking_val}', using 'high'", file=sys.stderr)
        pi_thinking_val = "high"

    _valid_tools = {"auto", "codex", "gemini", "pi"}
    ext_tool_val = args.external_tool if args.external_tool is not None else file_config.get("external_tool", "auto")
    if ext_tool_val not in _valid_tools:
        print(f"Warning: invalid external_tool '{ext_tool_val}', using 'auto'", file=sys.stderr)
        ext_tool_val = "auto"

    config = PlanReviewConfig(
        plan_file=args.plan_file,
        external_tool=ext_tool_val,
        codex_model=args.codex_model if args.codex_model is not None else file_config.get("codex_model", "gpt-5.2-codex"),
        gemini_model=args.gemini_model if args.gemini_model is not None else file_config.get("gemini_model", ""),
        pi_model=args.pi_model if args.pi_model is not None else file_config.get("pi_model", ""),
        pi_thinking=pi_thinking_val,
        pi_options=raw_pi_options,
        internal_findings=args.internal_findings,
    )

    runner = ExternalPlanReviewRunner(config)
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
