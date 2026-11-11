---
name: vale
description: Run the repository's existing Vale prose linter at one bounded checkpoint after meaningful documentation changes or when explicitly requested. Use for prose files governed by the repository's Vale configuration; do not invoke it for code-only edits or after every edit.
---

# Vale

Use the locally available Vale command-line tool and the repository's existing Vale configuration. A text editor's Vale integration is a human interface, not an agent execution path.

## Configuration source of truth

The organisation's `docs-template` repository is the canonical source of Vale rules: its `styles/` tree (custom styles, vocabularies, and synced packages) and its central `.vale.ini`.

A downstream repository uses one of two setups:

- **Central config:** it lints with the `docs-template` `.vale.ini` as-is.
- **Repository config:** it commits its own `.vale.ini` that points at the central `styles/` tree and customises which styles and rules apply, and at what alert level.

Use the configuration the repository's own Vale CI job uses. The job shows which applies: the committed `.vale.ini` it passes, or the central config at the `docs-template` ref it pins. A committed repository config is reviewed in that repository and is the configuration to use there.

This pointer is advisory: the local checkout path differs per machine, so treat the repository (and the branch or ref your workflow pins) as the source of truth, not any fixed local path.

The MDK repositories pin the `vale` branch of `docs-template` in their CI jobs (`docs_template_ref: vale`), so read that branch, not `main`, when checking which rules, exceptions, or vocabulary apply. A repository config reaches the central `styles/` tree through an ignored, relative symlink at the repository root, `.tether-vale-source`, pointing at the sibling `docs-template` checkout. A `StylesPath ... doesn't exist` error means that link is missing or dangling: report it, do not copy styles in.

New or changed rules, styles, and vocabulary belong in `docs-template` and are reviewed there; a repository config only selects and tunes them. Do not add uncommitted or per-machine overrides to change linting behavior, and never edit the synced package styles under `styles/` — `vale sync` overwrites them.

## Trigger gate

Run Vale only when one of these conditions is true:

- The user explicitly asks for a Vale check.
- A coherent documentation or prose change is complete and ready for final handoff.

For a normal task, default to one check at the final review point. An individual edit, save, or file completion is not a checkpoint. If the task changed no governed prose, do not run Vale.

## Bound the check

- Check only governed prose files changed for the current task.
- Use one invocation with an explicit file list. Do not start watch mode, background linting, or per-save checks.
- Pass the configuration explicitly with `--config`, and add `--no-global` so no machine-wide config is merged in. Do not rely on config discovery: an environment variable such as `VALE_CONFIG_PATH` can silently replace the repository's configuration.
- Do not scan the whole repository unless the user explicitly asks for a repository-wide check.
- Exclude generated, vendored, cached, and build-output files, and any paths the repository's Vale CI job ignores.
- If the Vale executable or repository configuration is unavailable, report that once and stop.
- Inside the sandbox container Vale is preinstalled at the version CI pins and egress is restricted. Do not run `vale sync`; the synced packages are already present in the central `styles/` tree. A missing package is a finding to report, not a download to attempt.
- Installing or updating Vale, synchronizing style packages, enabling Docker, changing editor settings, and changing the Vale configuration are separate tasks. Never infer permission for them from a lint request.

## Handle results

- Summarize findings by file, rule, and severity. Include exact diagnostics only when they help the user act.
- If the local Vale version may differ from the one CI runs, say so: findings can differ between versions. Updating Vale remains a separate task.
- Fix relevant findings only within the user's requested scope.
- Do not change vocabulary or style configuration merely to silence a finding. Ask before making such a policy change.
- After Vale-specific fixes, run at most one verification check over the same explicit file set.
- Do not loop until clean. Report any remaining findings and the reason they remain.

