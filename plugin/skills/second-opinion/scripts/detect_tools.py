#!/usr/bin/env python
"""Detect available external AI CLI tools and manage second-opinion config."""

import json
import subprocess
import sys
from pathlib import Path

TOOLS = {
    "codex": {"cmd": "codex", "version_flag": "--version", "desc": "OpenAI Codex CLI"},
    "gemini": {"cmd": "gemini", "version_flag": "--version", "desc": "Google Gemini CLI"},
    "claude": {"cmd": "claude", "version_flag": "--version", "desc": "Anthropic Claude CLI"},
}

def get_config_path(project_name: str) -> Path:
    return Path.home() / ".agents" / "second-opinion" / project_name / "config.json"

def load_config(project_name: str) -> dict:
    path = get_config_path(project_name)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def save_config(project_name: str, config: dict) -> str:
    path = get_config_path(project_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if path.exists():
        with open(path) as f:
            existing = json.load(f)
    existing.update(config)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)
    return str(path)

def detect_tools() -> list[dict]:
    """Probe for installed CLI tools. Returns list of available tools."""
    available = []
    for name, info in TOOLS.items():
        try:
            result = subprocess.run(
                [info["cmd"], info["version_flag"]],
                capture_output=True, timeout=10, text=True,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0][:80]
                available.append({"name": name, "cmd": info["cmd"], "desc": info["desc"], "version": version})
        except (OSError, subprocess.TimeoutExpired):
            pass
    return available

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "detect"

    if action == "detect":
        tools = detect_tools()
        print(json.dumps({"available_tools": tools}, indent=2))

    elif action == "load-config":
        project = sys.argv[2] if len(sys.argv) > 2 else "default"
        config = load_config(project)
        print(json.dumps(config, indent=2))

    elif action == "save-config":
        project = sys.argv[2] if len(sys.argv) > 2 else "default"
        config_json = sys.argv[3] if len(sys.argv) > 3 else "{}"
        config = json.loads(config_json)
        path = save_config(project, config)
        print(json.dumps({"saved": str(path)}))

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()