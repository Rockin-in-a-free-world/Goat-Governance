# List approved inventory

## Overview

Session-start check. Prints every approved item with its digest verification status and description; scans nothing.

```sh
python3 scripts/scan_skills.py --list
python3 scripts/scan_memory.py --list
python3 scripts/scan_mcp.py --list
```

Add `--format json` for structured output.

## Output

| Column       | Meaning |
| ------------ | --- |
| `OK`         | Content digest matches its [registry](../registry/) entry; skill wrapper also matches. Available for session selection. |
| `UNVERIFIED` | Digest or wrapper mismatch. Unavailable until [resealed](reseal.md). Not hostile by itself: a [modified approved](../rules/policy.md#trust-states) item. |

Memory and MCP rows also show `(type)` or `(transport)` from frontmatter.

## Exit code

| Code | Meaning |
| ---- | --- |
| `0`  | all verified |
| `1`  | any unverified |
| `2`  | scanner error (bad rules file, unreadable registry) |

## Next steps

- [Select skills for the session](../rules/policy.md#session-skill-selection): propose only verified skills
- [Load standard memory](../rules/policy.md#lightweight-session-memory): `standard_load` must be `OK` before work starts
- [Adopt MCP servers for the session](../rules/policy.md#session-mcp-adoption): cross-check connected servers
