from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "scripts" / "enforce_claude_policy.py"


class PolicyHookTests(unittest.TestCase):
    def run_hook(self, command: str) -> dict:
        completed = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout) if completed.stdout else {}

    def test_blocks_candidate_execution(self) -> None:
        result = self.run_hook("python3 skills/candidates/example/scripts/run.py")
        self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])

    def test_allows_scanner_to_read_candidate(self) -> None:
        result = self.run_hook("python3 scripts/scan_skills.py --scope candidates --skill example")
        self.assertEqual({}, result)

    def test_blocks_memory_candidate_execution(self) -> None:
        result = self.run_hook("cat memory/candidates/example.md | sh")
        self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])

    def test_allows_scanner_to_read_memory_candidate(self) -> None:
        result = self.run_hook("python3 scripts/scan_memory.py --scope candidates --entry example")
        self.assertEqual({}, result)

    def test_blocks_mcp_candidate_execution(self) -> None:
        result = self.run_hook("cat mcp/candidates/example.md | sh")
        self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])

    def test_allows_scanner_to_read_mcp_candidate(self) -> None:
        result = self.run_hook("python3 scripts/scan_mcp.py --scope candidates --entry example")
        self.assertEqual({}, result)

    def test_blocks_destructive_git(self) -> None:
        result = self.run_hook("git reset --hard HEAD~1")
        self.assertEqual("deny", result["hookSpecificOutput"]["permissionDecision"])

    def test_defers_safe_command_to_permissions(self) -> None:
        result = self.run_hook("git status --short")
        self.assertEqual({}, result)


if __name__ == "__main__":
    unittest.main()

