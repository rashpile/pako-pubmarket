#!/usr/bin/env python
"""Run external AI model with context. Supports codex, gemini, claude, and custom CLI."""

import subprocess
import sys
import tempfile
from pathlib import Path

def _log(msg: str):
    print(msg, file=sys.stderr)

def _write_prompt_file(prompt: str) -> str:
    """Write prompt to a temp file, return path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, prefix="second-opinion-")
    f.write(prompt)
    f.close()
    return f.name

def _run_cmd(cmd, shell=False, timeout=300) -> str:
    _log(f"Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, shell=shell,
        )
        if result.returncode != 0:
            _log(f"stderr: {result.stderr[:500]}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out after 5 minutes"
    except OSError as e:
        return f"[ERROR] Failed to run command: {e}"

def run_claude(prompt_file: str, model: str = "") -> str:
    prompt = Path(prompt_file).read_text()
    cmd = ["claude", "-p", prompt]
    if model:
        cmd.extend(["--model", model])
    return _run_cmd(cmd)

def run_codex(prompt_file: str, model: str = "") -> str:
    prompt = Path(prompt_file).read_text()
    cmd = ["codex", "exec", "--sandbox", "read-only"]
    if model:
        cmd.extend(["-c", f'model="{model}"'])
    cmd.append(prompt)
    return _run_cmd(cmd)

def run_gemini(prompt_file: str, model: str = "") -> str:
    prompt = Path(prompt_file).read_text()
    cmd = ["gemini", "-p", prompt, "-s", "-o", "text"]
    if model:
        cmd.extend(["-m", model])
    return _run_cmd(cmd)

def run_custom(prompt_file: str, custom_cmd: str) -> str:
    """Run custom CLI. {prompt_file} in command is replaced with the temp file path."""
    if "{prompt_file}" in custom_cmd:
        cmd_str = custom_cmd.replace("{prompt_file}", prompt_file)
    else:
        cmd_str = f"{custom_cmd} {prompt_file}"
    return _run_cmd(cmd_str, shell=True)

RUNNERS = {
    "codex": run_codex,
    "gemini": run_gemini,
    "claude": run_claude,
}

def main():
    """Usage: run_external.py <tool> <prompt_or_file> [model] [custom_cmd]

    If prompt_or_file is a path to an existing file, reads from it.
    Otherwise treats it as inline prompt text.
    """
    if len(sys.argv) < 3:
        print("Usage: run_external.py <tool> <prompt_or_file> [model] [custom_cmd]", file=sys.stderr)
        sys.exit(1)

    tool = sys.argv[1]
    prompt_or_file = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else ""
    custom_cmd = sys.argv[4] if len(sys.argv) > 4 else ""

    if Path(prompt_or_file).is_file():
        prompt_file = prompt_or_file
        cleanup = False
    else:
        prompt_file = _write_prompt_file(prompt_or_file)
        cleanup = True

    try:
        if tool == "custom" and custom_cmd:
            output = run_custom(prompt_file, custom_cmd)
        elif tool in RUNNERS:
            output = RUNNERS[tool](prompt_file, model)
        else:
            print(f"Unknown tool: {tool}. Available: {', '.join(RUNNERS.keys())}, custom", file=sys.stderr)
            sys.exit(1)
        print(output)
    finally:
        if cleanup:
            Path(prompt_file).unlink(missing_ok=True)

if __name__ == "__main__":
    main()
