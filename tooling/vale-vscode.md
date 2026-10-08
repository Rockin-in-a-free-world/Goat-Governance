# Vale VS Code extension

This is a portable human-tool record. It is not a skill, an MCP server record, an installation instruction for agents, or an agent permission grant.

- Tool: Vale Linter for VS Code
- Extension identifier: `ChrisChinchilla.vale-vscode`
- Reviewed version: `1.2.0`
- Reviewed source commit: `a8f5d14d1b3f79e9e4fec35703eb89244b0ff9ec`
- Upstream source: https://github.com/ChrisChinchilla/vale-vscode
- Marketplace: https://marketplace.visualstudio.com/items?itemName=ChrisChinchilla.vale-vscode
- Review date: 2026-09-07
- Human-use status: **conditionally acceptable in trusted repositories only**
- Overall safety severity: **high**
- Full assessment: [reports/tools/vale-vscode.md](../reports/tools/vale-vscode.md)
- Agent behavior: the separate [approved Vale skill](../skills/approved/vale/SKILL.md) governs bounded Claude use of the existing CLI

## Why the status is conditional

The extension is not passive. It activates after startup, runs local processes, downloads and executes a checksum-pinned Vale Language Server on first use, can ask that server to install or update Vale, can synchronize style packages, can write vocabulary files, and can optionally run a configurable Docker image with a workspace mount.

The pinned source has a concrete Restricted Mode gap: `vale.valeCLI.installVale` is workspace-scoped and is passed to the automatically started language server, but it is missing from the extension's `restrictedConfigurations` list. An untrusted repository can therefore request automatic Vale installation or update. Until upstream closes that gap, keep this extension disabled for untrusted workspaces.

The publishing workflows also give release credentials to third-party GitHub Actions referenced by mutable version tags rather than immutable commit digests. That weakens confidence that a Marketplace package necessarily matches the reviewed source commit.

## Safer local defaults

Keep these user-level settings unless you deliberately need a listed feature:

```json
{
  "vale.valeCLI.installVale": false,
  "vale.valeCLI.syncOnStartup": false,
  "vale.valeCLI.lintOnChange": false,
  "vale.docker.enabled": false
}
```

Also:

- Use VS Code Workspace Trust and enable the extension only for repositories you trust.
- Keep Vale itself installed and updated through your normal trusted toolchain, rather than through a repository setting.
- Inspect `.vale.ini` before manually synchronizing packages.
- Leave Docker mode off unless needed. If enabled, review the image and every extra argument because the workspace is mounted into the container.
- Reassess any new extension version before adopting it. The source commit, Vale Language Server version and checksums, native binaries, dependencies, and release workflows can all change.

## Portability

This record and its assessment travel with the governance repository. The extension and Vale executable do not: each device still needs its own explicit installation and user-level configuration. Agents must use the approved `vale` skill; they must not treat this human-tool record as authorization to install, update, synchronize, or enable anything.
