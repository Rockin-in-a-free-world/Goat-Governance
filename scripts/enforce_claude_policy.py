#!/usr/bin/env python3
"""Claude Code PreToolUse hook for non-negotiable repository safeguards."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


DESTRUCTIVE_PATTERNS = (
    (re.compile(r"(?i)(?:^|[;&|]\s*)(?:sudo\s+)?rm\s+[^\n]*(?:-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)"), "recursive forced deletion is blocked"),
    (re.compile(r"(?i)\bgit\s+reset\s+--hard\b"), "hard Git reset is blocked"),
    (re.compile(r"(?i)\bgit\s+clean\s+-[^\n]*f"), "forced Git clean is blocked"),
    (re.compile(r"(?i)\bgit\s+push\b[^\n]*(?:--force(?:-with-lease)?|-f\b)"), "forced Git push is blocked"),
    (re.compile(r"(?i)\bgit\s+branch\s+-D\b"), "forced branch deletion is blocked"),
    (re.compile(r"(?i)\bRemove-Item\b[^\n]*-Recurse[^\n]*-Force"), "recursive forced deletion is blocked"),
)

CANDIDATE_PATH = re.compile(r"(?i)(?:^|[\s'\"]|\.\/|\.\\)(?:skills|memory|mcp)[\\/]candidates(?:[\\/]|\b)")


def decision(kind: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
            "permissionDecisionReason": reason,
        }
    }))


def get_command(payload: dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    command = tool_input.get("command")
    return command if isinstance(command, str) else ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        decision("deny", f"governance hook could not parse tool input: {exc}")
        return 0

    command = get_command(payload)
    if not command:
        decision("deny", "governance hook received a shell tool call without a command")
        return 0

    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if pattern.search(command):
            decision("deny", reason)
            return 0

    scanner_call = re.search(r"(?i)\bscripts[\\/]scan_(?:skills|memory|mcp)\.py\b", command)
    if CANDIDATE_PATH.search(command) and not scanner_call:
        decision("deny", "shell access to candidate quarantine is blocked; use the static scanner and read candidate files as text")
        return 0

    # No allow decision: the committed permission rules still require human approval.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
