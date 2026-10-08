# Driving the app to verify / capture screens (Playwright MCP + Brave)

To confirm what a screen actually shows before writing narration — or to grab fresh screenshots — drive
the live app with the **Playwright MCP**. On this machine there is **no Google Chrome installed**, and the
browser CDN (`cdn.playwright.dev`) is **blocked by the Socket firewall**, so `npx playwright install
chrome|chromium` fails. Use the **already-installed Brave** instead (Chromium-based, so Playwright drives
it natively).

## One-time config

Point the Playwright MCP at Brave's binary via `--executable-path` in `~/.claude.json`
(`mcpServers.playwright.args`):

```json
"playwright": {
  "type": "stdio",
  "command": "npx",
  "args": [
    "@playwright/mcp@latest",
    "--executable-path",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
  ],
  "env": {}
}
```

- Verify the binary first: `ls "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"`.
- **Restart the Claude Code session** (or reconnect via `/mcp`) after editing — the MCP server reads its
  args at launch, so a mid-session edit does not take effect until it respawns.
- Alternative to `--executable-path`: start Brave yourself with `--remote-debugging-port=9222` and set
  `--cdp-endpoint http://localhost:9222` instead (use this if you want to attach to a Brave you're already
  signed into). `@playwright/mcp` also accepts `--browser` and `--cdp-header`.

## Sign-in (handoff, no secret capture)

- Base URL (staging): `https://dev-moria.tether.to/`. Cooling screens live under
  `/group-operations/cooling/miners` and `/group-operations/cooling/hvac`.
- Navigate to the base URL, then **hand off to the user to sign in themselves.**
- **Do not `browser_snapshot` or `browser_take_screenshot` the login page**, and do not read/echo
  credentials. Resume inspecting only after the user confirms they're signed in.

## Capturing

- `browser_snapshot` (accessibility tree) is better than a screenshot for *reading* structure/labels and
  for finding click targets; `browser_take_screenshot` is for the visual shots that go in `shots/`.
- Save screenshots into the screen's `assets/shots/` with the same `NN-screen-detail.png` convention used
  by the Cooling capture set.
