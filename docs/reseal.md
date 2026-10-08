# Reseal a maintainer edit

## Overview

Re-pins an approved item after an in-place edit, without a candidate round trip. For maintainer-made or
maintainer-reviewed changes only; external material goes through [promotion](promote.md).

```sh
# 1. scan and preview
python3 scripts/reseal_approved.py skill NAME \
  --approved-by "Reviewer" \
  --review-note "What changed and was checked"

# 2. apply after explicit human approval of the current bytes
python3 scripts/reseal_approved.py skill NAME \
  --approved-by … --review-note … \
  --maintainer-edit --apply
```

First positional argument: `skill`, `memory`, or `mcp`.

| Flag                    | Required           | Purpose |
| ----------------------- | ------------------ | --- |
| `--approved-by`         | yes                | human reviewer identity |
| `--review-note`         | yes                | what was reviewed |
| `--maintainer-edit`     | for apply          | attests bytes are maintainer-made or reviewed, with no unreviewed external material |
| `--accept-risk RULE_ID` | per medium finding | [accept a medium finding](accept-risk.md) |
| `--apply`               | no                 | omit for a dry run |

## Behavior

- Repairs exactly one thing: the target's digest or wrapper mismatch
- Any other integrity failure, or any critical/high content finding, blocks
- Success records `source: maintainer-edit`, keeps the previous registry entry in history, and regenerates the wrapper
  or index. No candidate copy is created.

## Next steps

- [Promote with `--replace`](promote.md) for a new upstream version, copied prompt, third-party code, or changed live
  MCP tool descriptions
- [Read the maintainer update rules](../rules/policy.md#maintainer-updates-to-approved-content)
