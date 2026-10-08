# Candidate assessment: vale

- Status: approved and registry-verified
- Decision: promoted after explicit human approval
- Overall severity: **medium**
- Review date: 2026-09-07
- Approved by: the-goat
- Approved at: 2026-09-07T12:05:40Z
- Source: user-requested local policy for an existing repository-configured Vale CLI
- Candidate tree digest: `sha256:92d93c61895a76698789a2ba46c9eb789a4a79dd8d21516085ab1a8820705a2d`
- Package: one UTF-8 Markdown file, 2,035 bytes; no scripts, binaries, symlinks, hooks, tool grants, dependencies, or remote instructions

## Static scan

- Blocking: no
- Critical: 0
- High: 0
- Medium: 0
- Low: 0

No scanner risk IDs require acceptance.

## Manual threat review

| Area | Severity | Assessment |
| --- | --- | --- |
| Prompt injection | Low | The skill consumes the repository's existing configuration and Vale diagnostics. It does not ask the agent to treat document content or external material as instructions. |
| Exfiltration | Low | The workflow names no external destination and authorizes no upload, telemetry, connector, or remote service. |
| Supply chain | Low | The skill contains only local policy and does not install, update, synchronize, or download tools or style packages. It uses an already available Vale executable. |
| Reverse shell | Low | No shell, listener, socket, callback, or remote-control behavior exists. |
| Credential extraction | Low | No credentials, secret stores, tokens, keys, environment values, or authentication material are requested. |
| Execution | Medium | The skill deliberately permits one bounded local Vale process over explicit files, plus at most one verification run after relevant fixes. This is necessary for the skill's purpose. |
| Filesystem | Low | Vale is used as a linter over an explicit changed-file set. Any edits remain bounded by the user's task, and policy or vocabulary changes require a separate ask. |
| Persistence | Low | Watch mode, background linting, installation, synchronization, editor-setting changes, and inferred configuration changes are prohibited. |
| Obfuscation | Low | Plain, readable Markdown with no encoded, generated, hidden, or opaque content. |
| Network | Low | The skill authorizes no network action. Missing tools or configuration are reported rather than fetched. |

## Control review

- Default frequency is one check at final review, not after every edit, save, or file.
- Scope defaults to governed prose files changed for the current task, passed as one explicit file list.
- Repository-wide checking requires an explicit user request.
- Generated, vendored, cached, and build-output files are excluded.
- Missing Vale or configuration stops the workflow without installation or repair.
- Installation, updates, package synchronization, Docker, editor settings, configuration, and vocabulary policy remain separate actions requiring separate authority.
- A single verification run is allowed after relevant fixes; repeated clean-up loops are prohibited.
- Output is summarized rather than dumped, limiting time and context use.
- The human-facing VS Code extension is explicitly excluded as an agent execution path. Its separate high-severity assessment does not grant this skill additional capability.

## Value

The skill solves the stated agent-control problem directly: Claude gets a predictable prose-quality gate without running Vale after every edit or silently expanding linting into tool installation, dependency synchronization, Docker, configuration changes, or repository-wide work.

Promotion completed through `scripts/promote_skill.py` after the findings were discussed and the user explicitly approved the Claude-only skill. The approved tree, registry digest, and generated Claude discovery wrapper verify. The redundant candidate copy was removed after promotion; the human extension remains separately classified as high risk and was not promoted.
