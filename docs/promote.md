# Promote a candidate

## Overview

Moves reviewed external material from `candidates/` to `approved/`, pins its digest in the registry, and regenerates
the skill wrapper or memory/MCP index.

```sh
# dry run (default)
python3 scripts/promote_skill.py NAME \
  --approved-by "Reviewer" \
  --source "https://source.example/commit" \
  --review-note "What was checked"

# apply
python3 scripts/promote_skill.py NAME --approved-by … --source … --review-note … --apply
```

`promote_memory.py ENTRY` and `promote_mcp.py ENTRY` take the same flags.

| Flag                    | Required            | Purpose |
| ----------------------- | ------------------- | --- |
| `--approved-by`         | yes                 | human reviewer identity, recorded in registry |
| `--source`              | yes                 | provenance: URL plus commit, or who reported it |
| `--review-note`         | yes                 | what the reviewer checked |
| `--accept-risk RULE_ID` | per medium finding  | [accept a medium finding](accept-risk.md) |
| `--apply`               | no                  | omit for a dry run that changes nothing |
| `--replace`             | when target exists  | replace approved item and keep registry history |

## Behavior

- Runs the [scan](scan.md) first. Critical/high findings block; unaccepted medium findings block.
- Refuses to overwrite an existing approved item without `--replace`
- Success consumes the candidate. Dry run or failure leaves it in quarantine.
- Registry entry records reviewer, source, time, digest, findings, accepted risks, and note; the previous entry stays in `history`
- Never hand-edit generated files: `.claude/skills/*/SKILL.md`, `memory/approved/MEMORY.md`, `mcp/approved/MCP.md`

## After apply

```sh
python3 -m unittest discover -s tests -q
python3 scripts/scan_skills.py --scope all
python3 scripts/scan_memory.py --scope all
python3 scripts/scan_mcp.py --scope all
```

## Next steps

- [Read the mandatory controls](../rules/policy.md#mandatory-controls): rules 5, 7, and 8 govern promotion
- [Reseal instead](reseal.md) when the change is a maintainer edit to an already approved item
