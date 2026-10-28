# What is this all about?

This repo exists to enforce the ABC's: Assume nothing, believe nothing, check everything.

Goat governance gives Claude governance controls.

> Governance shrinks what the agent is told: isolation shrinks what the agent can reach.

## The agent setup

Governance:

- MDK/CLAUDE.md  is prose for the model. It's injected into the conversation at session start, like a standing first message. Mine says "run the governance load before work".

- skills/ — mine symlinks to the approved skills across the repos in my workspace. It's my way of ensuring claude doesn't duplicate existing skills.

- settings.json: .claude/ is machinery for the harness — the Claude Code program itself, not the model: permission rules, hooks, env vars. These are enforced by the program (a denied Bash rule blocks the call no matter what the model thinks), whereas CLAUDE.md is only ever 'followed'. That's an important distinction: .claude is hard config, CLAUDE.md is soft instruction.

BUT, nothing stops settings.json from being deleted or altered.

## The adversarial environment

There is a recent example of an attack https://safedep.io/litellm-pypi-compromise-credential-stealer-backdoor/ had three linked parts:

1. Typo squat: Lookalike repository — attacker creates Berri-AI/litellm, one hyphen away from the real BerriAI/litellm, and puts the malicious code there.

2. Hacked release pipeline — stolen GitHub credentials let them repoint LiteLLM’s own trusted release workflow to build from that fake repo, so PyPI/official images received the poisoned build.

3. Automatic execution after install — the built wheel drops Python startup files into site-packages, so starting Python runs the malware.

> Any Python command in that environment—python, pip, pytest, a notebook kernel, or the LiteLLM app—triggers the payload without the user importing litellm or doing anything unusual.

## Isolation

What this repo does not do is provide isolation. To do that, run your agent inside your container.

The container: the agent runs in a throwaway Debian container. Only the project folder you declare or launch the container from is mounted; the launcher refuses to mount `~` and warns about `.env` and credential files in scope. Root privileges should last just long enough to program the firewall, then the process drops to an unprivileged user with every capability stripped and `no-new-privileges` set, so nothing in the tree can get them back.

The container is enforced by the kernel.

1. Tokens and the agent: the container had no GitHub access at all — no `ssh` binary in the image, no `gh` auth,
no git credential helper.
2. The firewall: default-deny egress, written with IP tables before the agent starts. A project registry can be allowlisted at launch, never by editing the rules.

IF you ran the corrupted LiteLLM: the payload still runs on the next `python`. Inside the box it runs as `dev`, sees one project, and has nowhere to send anything.

Governance shrinks what the agent is told; the container shrinks what it can touch; the firewall shrinks where it can send it.
