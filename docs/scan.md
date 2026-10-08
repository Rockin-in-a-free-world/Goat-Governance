# Scan and verify

## Overview

Static scanner plus registry integrity check. Reads files as text; never executes anything.

```sh
python3 scripts/scan_skills.py --scope candidates --skill NAME
python3 scripts/scan_memory.py --scope candidates --entry NAME
python3 scripts/scan_mcp.py    --scope candidates --entry NAME
```

| Flag                  | Values                             | Default |
| --------------------- | ---------------------------------- | --- |
| `--scope`             | `candidates`, `approved`, `all`    | `candidates` |
| `--skill` / `--entry` | one item name; omit for whole scope | all in scope |
| `--format`            | `text`, `json`                     | `text` |
| `--rules`             | path to rules file                 | [`rules/scanning-rules.json`](../rules/scanning-rules.json) |

## What it checks

- Content patterns: rule IDs and severities in [`rules/scanning-rules.json`](../rules/scanning-rules.json), one rule set for all three kinds
- Shape: frontmatter present and valid, name matches directory or filename, no tool-granting or hook frontmatter
- Integrity (`approved` and `all` scope only): digest matches registry, skill wrapper matches, registry entry exists
- MCP transport: the [`http://`, loopback, and `stdio` rules](../rules/policy.md#mcp-servers)

## Output

Findings sorted by severity, one per line: `SEVERITY RULE_ID path:line  message`. Last line `PASS` or `BLOCK` with
counts. Blocking threshold is `high`: any critical or high finding blocks.

## Exit code

| Code | Meaning |
| ---- | --- |
| `0`  | pass |
| `1`  | block |
| `2`  | scanner error |

## CI

[`.github/workflows/scan-skills.yml`](../.github/workflows/scan-skills.yml) runs tests then `--scope all` for each
scanner. A held candidate with a critical/high finding fails CI even when approved integrity passes.

## Next steps

- [Review the candidate as a human](../rules/policy.md#reviewer-responsibilities): a clean scan is necessary, not sufficient
- [Promote it](promote.md) after explicit approval
