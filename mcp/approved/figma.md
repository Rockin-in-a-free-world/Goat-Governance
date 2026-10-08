---
name: figma
description: Claude.ai-hosted Figma connector (claudeai-proxy) for reading Figma files and designs from within a session.
metadata:
  transport: http
  auth: oauth
  host: https://mcp.figma.com
---

## Provenance

A first-party claude.ai connector ("claude.ai Figma"), proxied via claudeai-proxy at
`https://mcp.figma.com`. It is configured through claude.ai's own connector settings, not
through this repository or any file here — this record only tracks what the server
declares itself to be and what it exposes. Approving it cannot make it connect, and
revoking approval here cannot disconnect it; that control lives entirely outside this
repository.

## Auth status and tool-surface visibility

OAuth required. As of this review, the session had not completed authentication, so only
the two auth-bootstrap tools below are visible. The server's real Figma tools (file/design
access, and whatever else it exposes once authenticated) are unknown and have not been
reviewed. This record must be re-reviewed with `--replace` once authentication completes
and the real tool surface becomes visible — a clean review of the bootstrap tools is not a
review of the product the server actually provides.

## Known tools (quoted verbatim from their declared descriptions, reviewed as data)

- `mcp__claude_ai_Figma__authenticate` — "The claude.ai Figma MCP server (claudeai-proxy
  at https://mcp.figma.com) is installed but requires authentication. Call this tool to
  start the OAuth flow — you'll receive an authorization URL to share with the user. Once
  the user completes authorization in their browser, the server's real tools will become
  available automatically."
- `mcp__claude_ai_Figma__complete_authentication` — "Complete an in-progress OAuth flow for
  the claude.ai Figma MCP server by submitting the callback URL. Call
  `mcp__claude_ai_Figma__authenticate` first to start the flow and get the authorization
  URL. After the user authorizes in their browser, the browser is redirected to a
  `http://localhost:<port>/callback?code=...&state=...` URL — on remote sessions that page
  fails to load, but the URL in the address bar is still valid. Pass that full URL here as
  `callback_url`."

Neither description tries to supersede earlier session instructions, points at a secret or
credential path, runs a destructive command, or changes persistent configuration. Both are
self-describing the OAuth bootstrap flow only. No conclusion is drawn here about the real
Figma tools, because they have not been observed yet.
