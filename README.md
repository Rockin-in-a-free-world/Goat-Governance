# Goat Governance

Portable trust boundary for Claude skills, shared memory, MCP server records.

## Quickstart

Set two variables once in your shell rc, then one command verifies the whole trust boundary from any directory. It
stops at the first failure.

```sh
export GOAT_GOVERNANCE="$HOME/path/to/goat-governance"
export GOAT_MEMORY="$HOME/path/to/goat-memory"          # private memory clone

python3 "$GOAT_GOVERNANCE"/scripts/scan_skills.py --list \
  && python3 "$GOAT_GOVERNANCE"/scripts/scan_memory.py --root "$GOAT_MEMORY" --list \
  && python3 "$GOAT_GOVERNANCE"/scripts/scan_mcp.py --list
```

Exit `0` and every row `OK`: the session may proceed. Anything else: stop, nothing unverified loads.

## TL;DR

External material enters quarantine under `candidates/`. Human reviews. Promotion SHA-256 pins approved content in `registry/`. Claude uses only digest-verified approved items, and only after you agree per session. Maintainer edits to approved items use shorter [reseal flow](#maintainer-edit-and-reseal).

## Why Goat Governance?

Three security controls:

1. **Quarantine.** External material is inert data under `candidates/` until a human promotes it. See [Trust model](#trust-model) and [External intake and promotion](#external-intake-and-promotion).
2. **Anti-poisoning.** Every approved skill, memory entry, and MCP record is SHA-256 pinned in `registry/`; Claude loads nothing unverified. See [Verification](#verification).
3. **Per-session consent.** Approved is not in-use: Claude proposes skills and MCP servers, uses only what you agree to. See [Start a Claude session](#1-start-a-claude-session).

## Get started

### Prerequisites

- Python 3.10+, standard library only.
- Clone may live anywhere; paths resolve from script location.
- Claude Code opened at this repository loads [`CLAUDE.md`](CLAUDE.md). Other Claude setups: tell them where clone lives, apply same gates.

### 1. Start a Claude session

Paste at session start:

```text
Governance load: use CLAUDE.md and rules/policy.md from <absolute-repository-path>.
Verify approved memory. Read memory/approved/standard_load.md before work.
Load other approved memory only when task-relevant. List approved skills and connected
MCP servers, propose only relevant ones, and wait for my agreement before using them.

Task: <task>
```

Startup stays light:

1. `python3 scripts/scan_memory.py --list`.
2. Read [`memory/approved/standard_load.md`](memory/approved/standard_load.md), mandatory startup context.
3. No other memory body unless indexed description matches task.
4. `python3 scripts/scan_skills.py --list`; propose relevant verified skills; wait for user agreement.
5. Enumerate connected MCP tools, cross-check `python3 scripts/scan_mcp.py --list`, propose relevant servers, wait for user agreement.

No full-repository read. No copy into machine-local memory.

### 2. Check approved inventory

Registries are source of truth. No stale lists in README.

```sh
python3 scripts/scan_skills.py --list
python3 scripts/scan_memory.py --list
python3 scripts/scan_mcp.py --list
```

Any `UNVERIFIED` item unavailable.

## Canonical controls

- [`CLAUDE.md`](CLAUDE.md) — startup instructions.
- [`rules/policy.md`](rules/policy.md) — full policy.
- [`skills/approved/governance-policy/SKILL.md`](skills/approved/governance-policy/SKILL.md) — operational policy skill.
- [`rules/scanning-rules.json`](rules/scanning-rules.json) — static detection rules.

## Trust model

| State | Meaning | Claude behavior |
| --- | --- | --- |
| Candidate | External or unreviewed content under `candidates/` path | Inert data. Never invoke, execute, install, load as memory. |
| Approved | Content digest matches registry entry; skill wrapper also matches | Available for task-specific selection. |
| Modified approved | Approved content changed after promotion | Report "modified and awaiting reseal." No use until resealed. |

Digest mismatch proves change, not hostility. Location alone proves nothing.

MCP approval covers reviewed record: identity, transport, auth model, host, known tool descriptions. Does not connect server, control live behavior, or make runtime output trusted.

## External intake and promotion

| Kind | Candidate | Scanner | Promoter | Approved | Registry |
| --- | --- | --- | --- | --- | --- |
| Skill | `skills/candidates/NAME/` | `scan_skills.py --skill NAME` | `promote_skill.py NAME` | `skills/approved/NAME/` | `approved-skills.json` |
| Memory | `memory/candidates/NAME.md` | `scan_memory.py --entry NAME` | `promote_memory.py NAME` | `memory/approved/NAME.md` | `approved-memory.json` |
| MCP record | `mcp/candidates/NAME.md` | `scan_mcp.py --entry NAME` | `promote_mcp.py NAME` | `mcp/approved/NAME.md` | `approved-mcp.json` |

Skill names `kebab-case`. Memory and MCP filenames `snake_case`.

Flow:

1. Put external material in candidate path. Pin source commit or release when possible.
2. Scan candidate. Scanner reads text only; never run candidate code.
3. Review provenance, need, scope, tool grants, hooks, dynamic commands, bundled code, external paths, network behavior, destructive or persistent behavior.
4. Skills: store assessment at `reports/skills/NAME.md`. Include source, pinned revision, digest, scan findings, overall severity, manual review for prompt injection, exfiltration, supply chain, reverse shell, credential extraction, execution, filesystem, persistence, obfuscation, network.
5. Discuss all findings; report decision with user.
6. Preview promotion. No `--apply` yet.
7. Promote only after user explicitly approves exact reviewed candidate and accepted risks.

<details>
<summary>Skill example: scan, dry run, apply</summary>

```sh
python3 scripts/scan_skills.py --scope candidates --skill example --format json

python3 scripts/promote_skill.py example \
  --approved-by "Reviewer Name" \
  --source "https://source.example/commit" \
  --review-note "Reviewed scope, code, tools, and external effects"

python3 scripts/promote_skill.py example \
  --approved-by "Reviewer Name" \
  --source "https://source.example/commit" \
  --review-note "Reviewed scope, code, tools, and external effects" \
  --apply
```

</details>

Rules:

- Critical/high findings block promotion.
- Each medium finding needs `--accept-risk RULE_ID` on dry run and apply.
- External replacement of existing approved item needs `--replace`.
- Successful apply consumes candidate. Dry run or failed apply preserves candidate.
- Approved copy, registry history, review report, Git history preserve audit trail.
- Promotion regenerates skill discovery wrapper, [`memory/approved/MEMORY.md`](memory/approved/MEMORY.md), or [`mcp/approved/MCP.md`](mcp/approved/MCP.md). Never edit generated files.

<details>
<summary>Memory and MCP: same flags</summary>

```sh
python3 scripts/promote_memory.py ENTRY_NAME --approved-by "Reviewer Name" --source "Source" --review-note "Review"
python3 scripts/promote_mcp.py ENTRY_NAME --approved-by "Reviewer Name" --source "Source" --review-note "Review"
```

</details>

<details>
<summary>Memory candidate frontmatter</summary>

```yaml
---
name: short-kebab-slug
description: One-line relevance summary.
metadata:
  type: user # user, feedback, project, or reference
---
```

</details>

<details>
<summary>MCP candidate frontmatter</summary>

```yaml
---
name: example-server
description: One-line server summary.
metadata:
  transport: http # http, sse, or stdio
  auth: oauth # none, oauth, or api_key
  host: https://mcp.example.com # required for http/sse
---
```

</details>

Record visible MCP tool descriptions as quoted data. Say when authentication hides part of tool surface. New or materially changed live tool descriptions are external updates; return through candidates.

## Maintainer edit and reseal

Only for existing approved item changed by, or fully reviewed by, maintainer, with no unreviewed external or unexplained material. New upstream code, copied third-party instructions, changed live MCP descriptions always go through candidate flow.

Human may edit approved file directly. Agent edits only when user explicitly requests that named item. Agent cannot approve own edit. Edit makes stored digest stale; Claude must not use item until resealed.

1. Scan and preview. Dry run prints every content finding, changes nothing. Use `memory ENTRY_NAME` or `mcp ENTRY_NAME` for other kinds.

   ```sh
   python3 scripts/reseal_approved.py skill example \
     --approved-by "Reviewer Name" \
     --review-note "Reviewed maintainer changes"
   ```

2. Discuss. User reviews current bytes, scan findings, diff, medium-risk IDs. Expected target digest or wrapper mismatch is repairable. Other integrity failure blocks reseal.

3. Apply after explicit approval. Add `--accept-risk RULE_ID` once per accepted medium finding. Critical/high content findings stay blocked.

   ```sh
   python3 scripts/reseal_approved.py skill example \
     --approved-by "Reviewer Name" \
     --review-note "Reviewed maintainer changes" \
     --maintainer-edit \
     --apply
   ```

Successful reseal: pins current digest; records `source: maintainer-edit`; preserves prior registry entry in history; regenerates wrapper or index; creates no candidate copy.

## Shared memory behavior

[`memory/approved/standard_load.md`](memory/approved/standard_load.md) is mandatory startup context after registry verification. Other approved entries task-specific. Agents read current repository copies; no copy into private machine memory.

Repository sets `autoMemoryEnabled: false`. New shared memory enters through candidate review. Local machine memory stays outside this repository.

## Enforcement stack

| Control | Job |
| --- | --- |
| [`CLAUDE.md`](CLAUDE.md) | Loads policy and session gates. |
| [`.claude/settings.json`](.claude/settings.json) | Disables bypass/auto modes, blocks outside reads, asks before shell, network, MCP, or protected writes. |
| [`scripts/enforce_claude_policy.py`](scripts/enforce_claude_policy.py) | Blocks candidate execution and destructive shell/Git commands. |
| `scripts/scan_*.py` | Static scan plus approved-registry verification. |
| `scripts/promote_*.py` | Reviewed external promotion; consumes successful candidate. |
| [`scripts/reseal_approved.py`](scripts/reseal_approved.py) | Reviewed maintainer reseal without candidate duplication. |
| `registry/approved-*.json` | Approval provenance, findings, accepted risks, history, digest. |
| [`.github/workflows/scan-skills.yml`](.github/workflows/scan-skills.yml) | Tests and all-scope scans on Linux and Windows. |

Repository controls are defence in depth. Person controlling clone can alter local settings or hooks. Strong organisation enforcement also needs managed settings/hooks, protected branches, required review. Claude products that ignore Claude Code project configuration need explicit startup instructions and equivalent permission controls.

## Verification

Approved trust boundary:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/scan_skills.py --scope approved
python3 scripts/scan_memory.py --scope approved
python3 scripts/scan_mcp.py --scope approved
```

One candidate:

```sh
python3 scripts/scan_skills.py --scope candidates --skill NAME --format json
python3 scripts/scan_memory.py --scope candidates --entry NAME --format json
python3 scripts/scan_mcp.py --scope candidates --entry NAME --format json
```

CI runs `--scope all` per scanner. Held candidate with critical/high finding fails CI even when approved integrity passes. Current behavior, not approved-item integrity failure.

New Claude Code device: `/context`, `/skills`, `/hooks`, `/permissions` show which committed controls loaded.

## License

[Apache License 2.0](LICENSE)
