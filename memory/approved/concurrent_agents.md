---
name: concurrent-agents
description: Repos are actively edited by more than one agent, user, or session concurrently; verify current state via the scanners rather than trusting your own last-known read.
metadata:
  type: project
---


If something you approved or expected is missing, changed, or contradicts the current
policy files, treat that as information, not alarm: investigate with `git log`, `git
status`, and a digest check, and report what you find rather than silently reverting it
or silently re-applying your own preference over it. 

The user may handle one part of a multi-part problem, stay scoped to the part they assigned you.
