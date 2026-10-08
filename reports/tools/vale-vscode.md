# Tool assessment: Vale VS Code extension

- Status: static and manual review complete
- Decision: human use only, conditionally acceptable in trusted repositories; do not enable in untrusted workspaces
- Overall severity: **high**
- Review date: 2026-09-07
- Upstream: https://github.com/ChrisChinchilla/vale-vscode
- Marketplace: https://marketplace.visualstudio.com/items?itemName=ChrisChinchilla.vale-vscode
- Reviewed tag: `v1.2.0`
- Reviewed commit: `a8f5d14d1b3f79e9e4fec35703eb89244b0ff9ec`
- Commit date: 2026-09-06
- Package version: `1.2.0`
- Extension identifier: `ChrisChinchilla.vale-vscode`

## Review boundary

The review treated the pinned repository as inert source. No extension code, package script, native proxy, downloaded language server, Vale installation path, synchronization path, or Docker image was executed.

Reviewed material included the manifest, lockfile, TypeScript source, Go proxy source, committed Windows proxy executables as opaque files, tests, and GitHub Actions workflows. A current advisory lookup against the pinned lockfile reported zero known vulnerabilities across 506 production, development, optional, and peer dependency entries. A production-only lookup also reported zero known vulnerabilities.

The published Marketplace package was not downloaded, unpacked, or reproducibly compared with the reviewed commit. The review therefore establishes properties of the pinned source, not binary equivalence of the Marketplace artifact.

## Static findings

### High: automatic Vale installation is not trust-gated

The manifest declares `vale.valeCLI.installVale` as a workspace-scoped setting that automatically installs and updates Vale. The setting is not included in `capabilities.untrustedWorkspaces.restrictedConfigurations`. The extension activates after startup, starts the Vale Language Server in Restricted Mode, reads the effective setting, and passes it as `installVale` to that server.

An untrusted repository can therefore request a download-and-execute path through workspace configuration. The review did not dynamically exercise the language server installer, but the extension's own setting description and initialization code establish the requested behavior. This is the principal reason for the high verdict.

Required condition: disable the extension in untrusted workspaces until the setting is included in the Restricted Mode configuration boundary and the fix is released and reviewed.

### High: release credentials cross mutable action references

The stable and pre-release publication workflows pass Open VSX and Visual Studio Marketplace credentials to `HaaLeo/publish-vscode-extension@v1`. Other write-capable workflows also use mutable major-version action references. None of the external actions are pinned to immutable commit digests.

This is a release supply-chain weakness. A compromised or moved action tag could access publication credentials or alter the released artifact. It does not prove that version `1.2.0` is compromised, but it prevents strong provenance assurance.

Required condition: treat Marketplace updates as new external artifacts. Prefer an upstream release process with commit-pinned actions, minimal permissions, and reproducible artifact provenance.

### Medium: first-use download and execution

The extension downloads Vale Language Server `v0.5.0` from GitHub on first launch and stores it in VS Code's per-extension global storage before executing it. Positive controls are present: the asset name is platform-specific, six expected SHA-256 digests are embedded in source, the response status and optional length are checked, only the exact expected archive entry is extracted, and the file is written through a temporary path before rename.

This is still a network, filesystem, persistence, and execution boundary. The embedded digest proves equality with the expected asset, not that the upstream asset itself is trustworthy.

### Medium: Docker mode broadens access

Docker mode mounts the workspace read-write and accepts a configurable image plus extra `docker run` arguments. The ordinary TypeScript runner passes arguments without a shell, and the generated POSIX wrapper quotes embedded values. On Windows, a shipped native proxy executes `docker.exe` directly with an argument array.

The configuration is deliberately powerful: extra arguments can add mounts or otherwise broaden the container's host access. The committed Windows executables were not independently reproduced during this review.

Required condition: leave Docker mode disabled by default. If enabled, review the exact image and every extra argument first.

### Medium: synchronization and vocabulary writes

Manual synchronization can fetch packages named by Vale configuration. The `syncOnStartup` default is false and the relevant setting is trust-restricted. Vocabulary commands create directories and append words under the resolved Vale styles path; explicit commands are blocked in Restricted Mode.

Required condition: inspect the repository configuration before synchronization, and treat vocabulary edits as intentional policy changes rather than harmless lint fixes.

### Medium: process lifecycle is not tightly bounded

Direct Vale commands stream process output but set no timeout, output limit, or cancellation boundary. A stuck or noisy Vale, Docker, proxy, or configuration path can consume time and resources until externally interrupted.

## Threat review

| Area | Severity | Assessment |
| --- | --- | --- |
| Prompt injection | Low | The extension is a deterministic linter, not an instruction-following agent. Workspace prose is not used as an AI prompt. |
| Exfiltration | Medium | No telemetry or credential-upload path was found. Docker mode exposes the mounted workspace to the selected local image, and synchronization contacts package sources. |
| Supply chain | High | Runtime dependencies are currently clear of known advisories, but the extension downloads an executable, ships opaque Windows binaries, supports package synchronization and Docker images, and publishes with mutable action references holding release credentials. |
| Reverse shell | Low | No listener, callback shell, socket-control path, or reverse-shell behavior was found. Normal process launches use argument arrays without a shell. |
| Credential extraction | Low | No code was found that seeks credential stores, environment secrets, keys, or authentication files. Publication secrets are confined to upstream CI workflows. |
| Execution | High | The extension auto-starts a downloaded language server and can start Vale, Docker, or a native proxy. The untrusted-workspace `installVale` gap can request another install-and-execute path. |
| Filesystem | Medium | It writes its language server and Docker wrapper to extension storage, may install Vale, mounts the workspace read-write in Docker mode, and can append to vocabulary files. |
| Persistence | Medium | Downloaded executables, a version marker, and wrapper scripts persist in VS Code global storage. Optional managed Vale installation can also persist. No login or startup persistence was found. |
| Obfuscation | Medium | TypeScript and Go source are readable, but two committed Windows executables and the Marketplace bundle were not independently reproduced. |
| Network | Medium | First launch contacts GitHub for the language server. Optional installation and synchronization add network access; Docker can pull or run a network-capable image. No telemetry endpoint was found. |

## Positive controls

- Vale Language Server version and platform archive checksums are pinned in source.
- Normal local and Docker commands use direct process execution with argument arrays.
- Generated POSIX Docker wrapper values are single-quote escaped.
- Direct synchronization, metrics, configuration, and vocabulary commands require a trusted workspace.
- Executable path, configuration path, startup synchronization, and Docker settings are restricted in untrusted workspaces.
- Automatic Vale installation, startup synchronization, lint-on-change, and Docker mode all default to false.
- Current full and production-only lockfile advisory lookups report zero known vulnerabilities.

## Decision

The extension does not pass as a generally safe, enable-everywhere tool. It is usable by the human owner under explicit conditions: trusted repositories only, automatic installation and synchronization disabled, Docker disabled unless separately reviewed, and updates reassessed.

This decision does not approve the extension as an agent capability. Agent use of the existing Vale CLI is governed separately by the approved skill at [skills/approved/vale/SKILL.md](../../skills/approved/vale/SKILL.md).
