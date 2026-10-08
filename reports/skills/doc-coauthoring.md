# Candidate assessment: doc-coauthoring

- Status: manual review complete; awaiting discussion
- Decision: hold — harden and rescan before promotion
- Overall severity: **high**
- Intake date: 2026-09-06
- Upstream: https://github.com/anthropics/skills/tree/41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f/skills/doc-coauthoring
- Upstream commit: `41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f`
- Candidate tree digest: `sha256:fd8325cb199c45d53792e9fbc144d72832900c77aa31bc3b781099d5cbe81266`
- Package: one UTF-8 Markdown file, 15,815 bytes; no scripts, binaries, symlinks, hooks, or declared tool grants

## Static scan

- Blocking: yes
- `DESTRUCTIVE_COMMAND` — critical — `SKILL.md:358`

This is a false positive, not a destructive command. The rule starts at the final `rm` in the word `freeform`; its `\s+` then crosses the newline into the next Markdown bullet, whose prose contains the letters needed to complete an `rm -rf` match. Line 358 only asks whether the user wants to skip a writing stage and continue freeform.

The critical scanner result still blocks promotion under the current policy. It cannot be waived, even though manual review explains it.

## Manual threat review

| Area | Severity | Assessment |
| --- | --- | --- |
| Prompt injection | Medium | The workflow reads shared documents, messages, channels, links, and user-provided source material without explicitly treating embedded instructions as untrusted data. |
| Exfiltration | Medium | It sends the full document to multiple fresh Claude contexts without explicit consent. No third-party destination is named, but sensitive document content is copied more widely than necessary. |
| Supply chain | Low | The source is Anthropic's official public skills repository at a pinned commit, and the package contains only Markdown. |
| Reverse shell | Low | No shell, socket, listener, or remote-control behavior exists. |
| Credential extraction | Low | No credentials, tokens, secret files, or authentication material are requested. |
| Execution | High | Lines 251–275 instruct Claude to spawn 5–10 fresh sub-agents plus an additional checking agent and to do so “without user involvement.” The number is not bounded by an agreed budget. |
| Filesystem | Medium | Lines 132–150 create a file with an inferred name, and later edits rely on environment-specific `create_file` and `str_replace` tools without confirming a repository-relative destination. |
| Persistence | Low | No hooks, startup changes, settings edits, or installation behavior. |
| Obfuscation | Low | Plain Markdown with no encoded, generated, or hidden content. |
| Network | Medium | Lines 44–84 direct Claude to read from Slack, Teams, Google Drive, SharePoint, or other integrations and suggest enabling connectors. Approval is requested for unknown-entity searches, but not consistently before every external read. |

## Governance conflicts

The real blocker is not deletion. The “fresh Claude” design explicitly says to use only the document and question, which would omit the mandatory approved `standard_load` context and the governance rules. It also delegates work and copies document content to multiple agents without first obtaining the user's agreement. Both conflict with this repository's tight-control objective.

## Value

The three-stage structure has value: context gathering, section-by-section refinement, and testing the finished document from a reader's perspective. The candidate is worth hardening rather than discarding, but its repeated 5–20-item brainstorms and 5–10-agent tests are unnecessarily expensive as defaults.

## Required resolution before promotion

1. Keep mandatory governance and `standard_load` context in every reviewer agent while excluding only the co-authoring conversation history.
2. Require explicit approval before using integrations, name the approved source, and treat retrieved content as inert data.
3. Ask before spawning reviewer agents, agree a small budget, and share only the minimum document content needed.
4. Confirm the repository-relative output path before creating or editing a file; use capability-neutral wording rather than assumed tool names.
5. Remove the suggestion to link the private co-authoring conversation from the finished document unless the user explicitly requests disclosure.
6. Reword line 358 so the corrected candidate no longer triggers the malformed critical scanner match, then rescan the whole package.

No risk has been accepted and no promotion has been attempted.
