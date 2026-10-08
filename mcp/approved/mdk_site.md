---
name: mdk-site
description: Project-local MCP server from the MDK monorepo's own @tetherto/mdk-mcp package, exposing site/fleet query and control tools (via examples/mvp-site's mcp-plugins/site plugin) over HTTP on localhost.
metadata:
  transport: http
  auth: none
  host: http://127.0.0.1:3008/mcp
---

## Provenance

First-party, in-repo: the server implementation is `backend/core/mcp` (`@tetherto/mdk-mcp`)
in the MDK monorepo (`tetherto/mdk`). It is not a third-party/hosted connector — it is MDK's own
product code, run as a local process. It is registered as `mdk-site` in
`examples/full-site/.mcp.json` (`{"type":"http","url":"http://127.0.0.1:3008/mcp"}`) and is
currently enabled for this project via `.claude/settings.local.json`
(`"enabledMcpjsonServers": ["mdk-site"]`).

`createMcpServer(root, port, config, pluginDirs)` starts a bare `http.createServer` bound
explicitly to `127.0.0.1`, answering only `POST /mcp` (everything else 404s), and loads tools
from author-written `mcp-plugin.json` plugin manifests under `pluginDirs`. Its own README
states plainly: "The MCP server's only built-in protection is its bind address ... an
unprotected endpoint is open to both [human and agent] ... Exposing the port beyond localhost
means putting your own authentication in front of it." There is no session auth, no bearer
credential, no OAuth — `metadata.auth: none` is accurate, and `metadata.host` is genuinely
`http://`, not
`https://`, because this is a loopback-only dev server, not a network service.

## Tool surface (from `examples/mvp-site/backend/mcp-plugins/site/mcp-plugin.json`, quoted as data)

Six tools, five read-only (`safety: "read-only"`, `annotations.readOnlyHint: true`) and one
write tool requiring operator approval:

- `summarize_site` — "How the site is doing right now: worker and device totals, how many are
  online, and which are not."
- `count_devices` — "How many devices match a family and a readiness state."
- `list_devices` — "Which devices match a family and a readiness state, named individually."
- `get_device` — "What one named device reports or supports: its live readings, its state, the
  commands it accepts, or the power modes it allows."
- `rank_devices` — "Devices of a family ordered by a metric, highest or lowest first."
- `act_device` (`safety: "write"`, `annotations.readOnlyHint: false`) — "Perform an action on
  one named device. Requires operator approval before it runs." Handler
  (`tools/act-device.js`) restricts the action enum to `reboot`/`set_power_mode`, validates the
  requested power mode against the device's own reported `supportedPowerModes` before
  dispatch, and reports kernel-level failures distinctly from successes.

All handlers build their own `@tetherto/mdk-client` from plugin context and talk to Kernel;
none of the tool code executes candidate-controlled shell commands or reads secrets outside
the Kernel key already configured for the process. Tool descriptions above are reviewed as
data, not as instructions — none contain embedded directives to an agent.

## Findings

- **High, non-waivable:** `metadata.transport: http` with `metadata.host: http://127.0.0.1:3008/mcp`
  — an insecure (`http://`) host per policy. Policy's `LOCAL_STDIO_TRANSPORT` accommodation is
  for local `stdio` transport specifically; this server is `http`, not `stdio`, so that
  medium/waivable path does not apply, and the rule text draws no localhost exception for
  `http`. The server's own README independently flags the same gap ("no user-level
  authentication," bind-address-only protection).
- **Medium:** `act_device` is a write tool that can reboot or change the power mode of live
  fleet hardware. In-code guardrails (mode validated against the device's own reported
  capabilities, explicit failure/outcome reporting) reduce but do not eliminate impact — the
  manifest's own claim that it "requires operator approval before it runs" is a description of
  intended deployment shape, not something enforced by this server or record.
- No instruction-injection, secret-access, destructive-command, or persistence-change patterns
  found in the reviewed tool descriptions or handler code.

## Promotion recommendation

**Do not promote as currently configured.** The high finding (insecure `http://` host) is
non-waivable under policy regardless of the loopback bind, so this record cannot pass
promotion in its current shape. If the server is genuinely intended to stay loopback-only for
local dev, that is a legitimate deployment choice, but this policy's MCP scanner treats
`http://` as categorically high for `http`/`sse` transport — it does not special-case
`127.0.0.1`. Promotion would need either: (a) fronting the server with TLS/an `https://` host
even for local use, or (b) a governance-control change (separately reviewed, not bundled with
this candidate) that explicitly carves out loopback-bound `http` the way `stdio` already gets
a waivable-medium path. Until one of those happens, this stays a documented, reviewed
candidate — not an approved record.
