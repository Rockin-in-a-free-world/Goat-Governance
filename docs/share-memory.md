# Share memory across machines

## Overview

Claude's local auto-memory is private to one machine and loads without review. Shared memory here is the opposite:
reviewed, digest-pinned, read from a repository clone. Nothing in this flow copies files into `~/.claude`, and nothing
needs to be published: keep the memory repository private and only the scripts and policy public.

## Set up a private memory repository

1. Create a private Git repository (for example `goat-memory`) and clone it beside this one on every machine.
2. Give it this layout, copying `scanning-rules.json` from this repository.

   ```text
   goat-memory/
   ├── memory/
   │   ├── candidates/
   │   └── approved/
   ├── registry/approved-memory.json   # start with {"schema_version": 1, "entries": {}}
   └── rules/scanning-rules.json
   ```

3. Run the memory scripts with `--root` pointing at that clone.

   ```sh
   python3 scripts/scan_memory.py --root ../goat-memory --list
   python3 scripts/promote_memory.py NAME --root ../goat-memory --approved-by … --source … --review-note … --apply
   ```

## Move a local memory into shared memory

1. Copy the local file from `~/.claude/projects/<project>/memory/` to `goat-memory/memory/candidates/<snake_case>.md`.
   Keep its frontmatter (`name`, `description`, `metadata.type`).
2. Scan it: `python3 scripts/scan_memory.py --root ../goat-memory --scope candidates --entry <name>`.
3. Read it as text, confirm `metadata.type` matches the content, and that it states a fact or preference, not an
   instruction to an agent.
4. [Promote it](promote.md) with `--root ../goat-memory`. Commit and push the private repository.

## Point every session at it

Add this to the workspace `CLAUDE.md` on each machine (not to this repository):

```text
Governance load: use CLAUDE.md and rules/policy.md from ./goat-governance.
Verify approved memory with `python3 goat-governance/scripts/scan_memory.py --root goat-memory --list`.
Read goat-memory/memory/approved/standard_load.md before work. Load other approved memory only when
task-relevant. List approved skills and connected MCP servers, propose only relevant ones, and wait for my
agreement before using them.
```

A session then reads the private clone directly. The public repository holds only the placeholder
[`standard_load`](../memory/approved/standard_load.md).

## Next steps

- [Read the shared memory policy](../rules/policy.md#shared-memory): what may enter and how it is reviewed
- [Check what is approved and verified](list-approved.md) before each session
