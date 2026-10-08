# Enforcement hook

## Overview

[`scripts/enforce_claude_policy.py`](../scripts/enforce_claude_policy.py) runs as a Claude Code `PreToolUse` hook on
`Bash` and `PowerShell`, wired in [`.claude/settings.json`](../.claude/settings.json). It runs automatically; there is
nothing to invoke.

## Denies

| Command shape                                                                 | Reason |
| ----------------------------------------------------------------------------- | --- |
| `rm -rf`, `Remove-Item -Recurse -Force`                                       | recursive forced deletion |
| `git reset --hard`, `git clean -f`, `git push --force` or `-f`, `git branch -D` | destructive Git |
| any shell command touching `skills/`, `memory/`, or `mcp/` `candidates/`      | quarantine: read candidates as text via the [scanner](scan.md), never via shell |
| unparseable or empty tool input                                               | fail closed |

The decision is returned as `permissionDecision: deny` with a reason Claude sees.

## Next steps

- [Understand the enforcement limits](../rules/policy.md#portability-and-enforcement-limits): project hooks are not
  tamper-proof against whoever controls the clone
