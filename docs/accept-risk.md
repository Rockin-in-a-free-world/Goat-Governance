# Accept a medium-risk finding

## Overview

Medium findings never pass silently. Each needs `--accept-risk RULE_ID` on both the dry run and the apply of a
[promotion](promote.md) or [reseal](reseal.md). Accepted IDs are recorded in the registry entry.

```sh
python3 scripts/promote_mcp.py my_server … --accept-risk LOCAL_STDIO_TRANSPORT --apply
```

Repeat the flag once per rule ID.

## Rule IDs

Content rules and severities are in [`rules/scanning-rules.json`](../rules/scanning-rules.json). The
[MCP transport rules](../rules/policy.md#mcp-servers) add `LOCAL_LOOPBACK_HTTP_TRANSPORT` and `LOCAL_STDIO_TRANSPORT`.

## Not waivable

Critical and high. Fix the content or decline the candidate. Editing rules to make a candidate pass is a
[governance-control change](../rules/policy.md#governance-control-changes) and needs its own review.

## Next steps

- [Promote the candidate](promote.md) with the accepted IDs
- [Reseal the item](reseal.md) with the accepted IDs
