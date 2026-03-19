#!/usr/bin/env python3
"""
External Code Review Runner

Orchestrates multi-phase code review using Claude and Codex CLIs.

Usage:
    python run_review.py first --branch main [--max-iterations 10]
    python run_review.py codex --branch main [--max-iterations 5]
    python run_review.py final --branch main [--max-iterations 3]
    python run_review.py full --branch main [--goal "Feature description"]
    python run_review.py quick --branch main [--goal "Feature description"]
    python run_review.py report
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Phase(Enum):
    FIRST = "first"
    CODEX = "codex"
    FINAL = "final"
    FULL = "full"
    QUICK = "quick"


class ExternalTool(Enum):
    CODEX = "codex"
    GEMINI = "gemini"


class Signal(Enum):
    REVIEW_DONE = "<<<REVIEW_DONE>>>"
    CODEX_REVIEW_DONE = "<<<CODEX_REVIEW_DONE>>>"
    REVIEW_FAILED = "<<<REVIEW_FAILED>>>"


def _detect_external_tool(preferred: str = "codex") -> ExternalTool:
    """Detect which external review tool to use.

    Priority:
    1. If user explicitly requested 'gemini', use gemini
    2. Try codex first (default)
    3. Fall back to gemini if codex not found
    4. If neither found, return codex (will fail with clear error)
    """
    if preferred == "gemini":
        return ExternalTool.GEMINI

    # Check if codex is available
    try:
        subprocess.run(["codex", "--version"], capture_output=True, timeout=10)
        return ExternalTool.CODEX
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: check if gemini is available
    try:
        subprocess.run(["gemini", "--version"], capture_output=True, timeout=10)
        return ExternalTool.GEMINI
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Neither found, return codex (will produce a clear error when run)
    return ExternalTool.CODEX


@dataclass
class ReviewConfig:
    branch: str = "main"
    goal: str = ""
    max_iterations: int = 10
    codex_enabled: bool = True
    codex_model: str = "gpt-5.2-codex"
    codex_sandbox: str = "read-only"
    codex_reasoning: str = "xhigh"
    timeout: int = 120
    external_tool: str = "auto"  # "auto", "codex", or "gemini"
    gemini_model: str = ""  # empty = use gemini default


class ReviewRunner:
    """Orchestrates code review using external AI models."""

    def __init__(self, config: ReviewConfig):
        self.config = config
        self.script_dir = Path(__file__).parent
        self.prompts_dir = self.script_dir.parent / "prompts"
        self.agents_dir = self.script_dir.parent / "agents"

    def _log(self, message: str, prefix: str = "🔍"):
        """Log a message."""
        print(f"\n{prefix} {message}")

    def _run_command(self, cmd: list, timeout: int = 120) -> tuple[str, bool]:
        """Run a shell command and return output + success."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            output = result.stdout.strip() or result.stderr.strip()
            return output, result.returncode == 0
        except subprocess.TimeoutExpired:
            return f"Command timed out after {timeout}s", False
        except FileNotFoundError:
            return f"Command not found: {cmd[0]}", False
        except Exception as e:
            return str(e), False

    def _check_signal(self, output: str) -> Optional[Signal]:
        """Check if output contains a completion signal."""
        for signal in Signal:
            if signal.value in output:
                return signal
        return None

    def _get_git_diff(self) -> str:
        """Get git diff against base branch."""
        output, _ = self._run_command([
            "git", "diff", f"{self.config.branch}...HEAD"
        ])
        return output

    def _get_git_log(self) -> str:
        """Get git log since base branch."""
        output, _ = self._run_command([
            "git", "log", f"{self.config.branch}..HEAD", "--oneline"
        ])
        return output

    def _load_prompt(self, name: str) -> str:
        """Load a prompt template."""
        prompt_file = self.prompts_dir / f"{name}.txt"
        if prompt_file.exists():
            return prompt_file.read_text()
        return ""

    def _load_agent(self, name: str) -> str:
        """Load an agent definition."""
        agent_file = self.agents_dir / f"{name}.txt"
        if agent_file.exists():
            return agent_file.read_text()
        return ""

    def _build_prompt(self, template: str) -> str:
        """Build prompt with variable substitution."""
        prompt = template
        prompt = prompt.replace("{{GOAL}}", self.config.goal or "Code changes")
        prompt = prompt.replace("{{DEFAULT_BRANCH}}", self.config.branch)

        # Substitute agent references
        for agent_name in ["quality", "implementation", "testing", "simplification", "documentation"]:
            agent_content = self._load_agent(agent_name)
            prompt = prompt.replace(f"{{{{AGENT:{agent_name}}}}}", agent_content)

        return prompt

    def run_claude(self, prompt: str) -> tuple[str, bool, Optional[Signal]]:
        """Run Claude CLI with prompt."""
        self._log("Running Claude review...", "🧠")

        cmd = [
            "claude", "-p", prompt,
            "--dangerously-skip-permissions",
            "--output-format", "text"
        ]

        output, success = self._run_command(cmd, timeout=self.config.timeout)
        signal = self._check_signal(output)

        return output, success, signal

    def _resolve_external_tool(self) -> ExternalTool:
        """Resolve which external tool to use for this review."""
        return _detect_external_tool(self.config.external_tool)

    def run_codex(self, diff: str) -> tuple[str, bool]:
        """Run Codex CLI for external review."""
        self._log("Running Codex external review...", "🤖")

        prompt = self._build_external_review_prompt(diff)

        # Use -c key=value for configuration (matches ralphex pattern)
        cmd = [
            "codex",
            "exec",
            "--sandbox", self.config.codex_sandbox,
            "-c", f'model="{self.config.codex_model}"',
            "-c", f"model_reasoning_effort={self.config.codex_reasoning}",
            prompt
        ]

        output, success = self._run_command(cmd, timeout=600)  # 10 min for codex
        return output, success

    def run_gemini(self, diff: str) -> tuple[str, bool]:
        """Run Gemini CLI for external review."""
        self._log("Running Gemini external review...", "💎")

        prompt = self._build_external_review_prompt(diff)

        cmd = [
            "gemini",
            "-p", prompt,
            "-s",  # sandbox mode
            "-o", "text",
        ]

        # Add model override if configured
        if self.config.gemini_model:
            cmd.extend(["-m", self.config.gemini_model])

        output, success = self._run_command(cmd, timeout=600)  # 10 min for gemini
        return output, success

    def run_external_review(self, diff: str) -> tuple[str, bool]:
        """Run external review using the resolved tool (codex or gemini)."""
        tool = self._resolve_external_tool()
        if tool == ExternalTool.GEMINI:
            return self.run_gemini(diff)
        return self.run_codex(diff)

    def _build_external_review_prompt(self, diff: str) -> str:
        """Build the review prompt for external tools."""
        return f"""Review the following code changes for bugs, security issues, and quality problems.

CODE CHANGES:
{diff}

Report each issue with:
- Location: file and line
- Issue: description
- Impact: severity
- Fix: suggestion

Report problems only - no positive observations."""

    def run_first_review(self) -> bool:
        """Run first review phase with 5 agents."""
        self._log("Starting FIRST REVIEW phase (5 agents)", "📋")

        template = self._load_prompt("review_first")
        if not template:
            print("❌ Could not load review_first.txt prompt")
            return False

        iteration = 0
        while iteration < self.config.max_iterations:
            iteration += 1
            self._log(f"First review iteration {iteration}/{self.config.max_iterations}", "🔄")

            prompt = self._build_prompt(template)
            output, success, signal = self.run_claude(prompt)

            print(f"\n{'='*60}")
            print("CLAUDE OUTPUT:")
            print('='*60)
            print(output[:5000] if len(output) > 5000 else output)
            print('='*60)

            if signal == Signal.REVIEW_DONE:
                self._log("First review complete - no issues found!", "✅")
                return True
            elif signal == Signal.REVIEW_FAILED:
                self._log("First review failed - issues cannot be fixed", "❌")
                return False
            # No signal = issues were fixed, continue loop

        self._log(f"First review hit max iterations ({self.config.max_iterations})", "⚠️")
        return True

    def run_codex_review(self) -> bool:
        """Run external review phase (Codex or Gemini)."""
        if not self.config.codex_enabled:
            self._log("External review disabled, skipping", "⏭️")
            return True

        tool = self._resolve_external_tool()
        tool_name = tool.value.capitalize()
        self._log(f"Starting EXTERNAL REVIEW phase ({tool_name})", "🤖")

        diff = self._get_git_diff()
        if not diff:
            self._log("No diff found, skipping external review", "⏭️")
            return True

        codex_iterations = max(3, self.config.max_iterations // 5)
        iteration = 0

        while iteration < codex_iterations:
            iteration += 1
            self._log(f"{tool_name} iteration {iteration}/{codex_iterations}", "🔄")

            # Run external tool
            ext_output, ext_success = self.run_external_review(diff)

            if not ext_success:
                self._log(f"{tool_name} execution failed, continuing anyway", "⚠️")
                return True

            print(f"\n{'='*60}")
            print(f"{tool_name.upper()} OUTPUT:")
            print('='*60)
            print(ext_output[:3000] if len(ext_output) > 3000 else ext_output)
            print('='*60)

            # Check if external tool found no issues
            if not ext_output.strip() or "no issues" in ext_output.lower():
                self._log(f"{tool_name} found no issues!", "✅")
                return True

            # Have Claude evaluate external findings
            eval_template = self._load_prompt("codex_eval")
            eval_prompt = eval_template.replace("{{CODEX_OUTPUT}}", ext_output)
            eval_prompt = self._build_prompt(eval_prompt)

            output, success, signal = self.run_claude(eval_prompt)

            print(f"\n{'='*60}")
            print("CLAUDE EVALUATION:")
            print('='*60)
            print(output[:3000] if len(output) > 3000 else output)
            print('='*60)

            if signal == Signal.CODEX_REVIEW_DONE:
                self._log(f"{tool_name} review complete!", "✅")
                return True

            # Get fresh diff for next iteration
            diff = self._get_git_diff()

        self._log(f"{tool_name} review hit max iterations ({codex_iterations})", "⚠️")
        return True

    def run_final_review(self) -> bool:
        """Run final review phase with 2 agents."""
        self._log("Starting FINAL REVIEW phase (2 agents)", "🎯")

        template = self._load_prompt("review_final")
        if not template:
            print("❌ Could not load review_final.txt prompt")
            return False

        final_iterations = max(3, self.config.max_iterations // 10)
        iteration = 0

        while iteration < final_iterations:
            iteration += 1
            self._log(f"Final review iteration {iteration}/{final_iterations}", "🔄")

            prompt = self._build_prompt(template)
            output, success, signal = self.run_claude(prompt)

            print(f"\n{'='*60}")
            print("CLAUDE OUTPUT:")
            print('='*60)
            print(output[:5000] if len(output) > 5000 else output)
            print('='*60)

            if signal == Signal.REVIEW_DONE:
                self._log("Final review complete - no critical issues!", "✅")
                return True
            elif signal == Signal.REVIEW_FAILED:
                self._log("Final review failed - issues cannot be fixed", "❌")
                return False

        self._log(f"Final review hit max iterations ({final_iterations})", "⚠️")
        return True

    def run_quick_review(self) -> bool:
        """Run quick review: final phase only (2 agents, critical/major issues)."""
        self._log("Starting QUICK REVIEW (final phase only)", "⚡")
        return self.run_final_review()

    def run_full_review(self) -> bool:
        """Run complete review pipeline: first -> codex -> final."""
        self._log("Starting FULL REVIEW pipeline", "🚀")

        # Phase 1: First review
        if not self.run_first_review():
            return False

        # Phase 2: Codex review
        if not self.run_codex_review():
            return False

        # Phase 3: Final review
        if not self.run_final_review():
            return False

        self._log("FULL REVIEW pipeline complete!", "🎉")
        return True

    def generate_report(self):
        """Generate a summary report of the review."""
        self._log("Generating review report", "📊")

        log = self._get_git_log()
        diff_stats, _ = self._run_command([
            "git", "diff", f"{self.config.branch}...HEAD", "--stat"
        ])

        print(f"""
{'='*60}
CODE REVIEW REPORT
{'='*60}

Base Branch: {self.config.branch}
Goal: {self.config.goal or "Code review"}

COMMITS SINCE {self.config.branch}:
{log or "No commits"}

CHANGES:
{diff_stats or "No changes"}

{'='*60}
""")


def main():
    parser = argparse.ArgumentParser(
        description="External Code Review Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("phase", choices=["first", "codex", "final", "full", "quick", "report"],
                        help="Review phase to run")
    parser.add_argument("--branch", "-b", default="main",
                        help="Base branch for diff (default: main)")
    parser.add_argument("--goal", "-g", default="",
                        help="Description of what was implemented")
    parser.add_argument("--max-iterations", "-i", type=int, default=10,
                        help="Max review iterations (default: 10)")
    parser.add_argument("--no-codex", action="store_true",
                        help="Disable external review (Codex/Gemini)")
    parser.add_argument("--codex-model", default="gpt-5.2-codex",
                        help="Codex model to use")
    parser.add_argument("--external-tool", default="auto",
                        choices=["auto", "codex", "gemini"],
                        help="External review tool: auto (codex with gemini fallback), codex, or gemini")
    parser.add_argument("--gemini-model", default="",
                        help="Gemini model to use (default: gemini default)")
    parser.add_argument("--timeout", "-t", type=int, default=120,
                        help="Timeout per Claude call in seconds")

    args = parser.parse_args()

    config = ReviewConfig(
        branch=args.branch,
        goal=args.goal,
        max_iterations=args.max_iterations,
        codex_enabled=not args.no_codex,
        codex_model=args.codex_model,
        timeout=args.timeout,
        external_tool=args.external_tool,
        gemini_model=args.gemini_model,
    )

    runner = ReviewRunner(config)

    if args.phase == "first":
        success = runner.run_first_review()
    elif args.phase == "codex":
        success = runner.run_codex_review()
    elif args.phase == "final":
        success = runner.run_final_review()
    elif args.phase == "full":
        success = runner.run_full_review()
    elif args.phase == "quick":
        success = runner.run_quick_review()
    elif args.phase == "report":
        runner.generate_report()
        success = True
    else:
        parser.print_help()
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
