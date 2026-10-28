---
name: docs-version-bump
description: >
  Promotes the newest version of MDK, archives the previous version, deletes the prior version.
---

# Promote

You are a senior technical writer.

`maintainers/content/versioning.md` is the authoritative process. Read **Promoting a new
release** there and work its steps in order.

This file adds only what that page does not cover: the scripts, the ordering traps, and two
checks that live nowhere else. Where the two disagree, versioning.md wins and this file is the
bug — fix it here rather than working around it.

## Curious

You have access to the user as a colleague. You ask questions rather than make assumptions.

## Vocabulary

This file and the scripts use three letters; versioning.md uses words for the same things:

| Here | versioning.md | What it is |
| --- | --- | --- |
| A | `<retired>` | the version leaving the archive slot, deleted this promotion |
| B | `<old>` | the outgoing current release, frozen into the archive slot |
| C | `<new>` | the release becoming current |

Slugs take two forms. The **dir/URL slug** uses dashes (`v0-9-0`) in
`content/archived/<slug>/`, `_snippets/<slug>/`, `redirects.config.mjs` and
`archive.meta.yaml`. The **release tag** uses dots (`v0.9.0`) and appears only inside
`github.com/...` source URLs. `archive.meta.yaml` stores both: `archived_version` is the dash
slug, `archived_label` the dot label.

## Execution notes

Keyed to the numbered steps in versioning.md's **Promoting a new release**.

**Before step 1** — confirm the tag `vB` exists upstream, or every link the freeze pins will
404: `git ls-remote --tags https://github.com/tetherto/mdk.git vB`.

**Steps 1 and 3 (freeze, copy snippets)** — plain recursive copies, no script. Copy, never
move: the current lane keeps its own `content/_snippets/current/`.

**Before step 2 (delete A), diff A against the new archive.** Not in versioning.md, and the
build will not catch it: versioning.md's step 8 check walks the *archive* tree against current,
so it never sees a page that existed in A and is already gone from B. Those URLs survive only
via the `/A/*` catch-all, which lands them on a page that may not be the right one.

Run `diff_pages.py --repo <repo> --old A` while A's tree is still on disk. It lists each A page
with no current-tree URL and the override to add; parked (`_`-prefixed) pages are skipped, and
parity pages need nothing beyond the catch-all. Add those overrides in step 2, before the
catch-all splat.

**Step 4 (pin GitHub links), plus the self-containment requirement** — both are automated by
`freeze_archive_links.py --repo <repo> --version B --tag vB` (`--version` is the dash slug,
`--tag` the dot tag). It (a) prefixes root-relative docs routes (`/concepts`, `/guides`,
`/reference`, `/support`, `/tutorials`) with `/archive`, (b) repoints `_snippets/current/`
includes to `_snippets/B/`, and (c) pins `blob|tree/main` to the tag. It processes `*.mdx` and
`meta.json` alike — nav descriptions carry links — and is idempotent. Run with no `--apply`
first to preview, then with `--apply`. Verify with `npm run check-external-links`.

**After step 4, strip the LLM dump.** Not in versioning.md. **Every** archive needs this, on
every promotion: only the current release ships `/llms-full.txt` and `/llms.txt`
(`scripts/generate-llms-full.ts` walks `content/docs` only), and archived pages render no
copy-for-LLM actions. The copied landing page still carries the current site's "Full docs in
one file" card, which would 404 under `/archive` and fail `check-built-links`.

- Remove that `<LandingCard>` (and its now-unused `FileText` import) from
  `content/archived/B/index.mdx`.
- The freeze script deliberately leaves `/llms-full.txt` links untouched, so confirm none
  remain: `grep -rn llms-full content/archived/B content/archived/_snippets/B` must return
  nothing.

**Step 8 (redirect dropped URLs)** — follow versioning.md's two placement rules there
(`mappings`, not `currentDocsSlugRedirects`; exact paths over a `/section/*` splat). Then
regenerate `_redirects` with `npm run build:redirects`.

**Step 9 (clear caches)** — the full verification, in order:

1. Delete `.next`, `node_modules/.cache` and `out`, then regenerate the fumadocs source with
   `npx fumadocs-mdx`. The `.source` index caches the old A paths; a stale one makes
   `check:nav` throw `MODULE_NOT_FOUND` on the deleted tree.
2. Run `npm run check:nav`, `npm run check:snippets`, `npm run check-redirects`,
   `npm run check-external-links`, then the full `npm run build` (which also runs
   next-broken-links, check-built-links and check:maintainers).
3. **Restructure fallout:** if the new release folded or renamed a page, shared snippets can
   still link to the old path. The current tree hides this via a slug redirect, but the static
   archive has none, so `next-broken-links` flags `/archive/<old-path>`. Repoint those links
   inside the archive to the surviving page (e.g. a folded `guides/cli/install` ->
   `guides/cli`). This belongs to the freeze's self-containment mandate, not to day-to-day
   archive editing.

## Monorepo (port-sync) snippets

Some current pages are single leaf `.mdx` files that pull their body from a monorepo-synced
snippet under `content/_snippets/current/monorepo/**` (an `<include>` plus a `monorepo:` source-path
frontmatter field), replacing what older releases authored as multi-page directories with their own
`meta.json`. The freeze needs no special case for these: they live under `_snippets/`, so the lane
repoint (`_snippets/current/` -> `_snippets/B/`), `/archive` link prefixing, and GitHub tag pinning
all apply through `freeze_archive_links.py` as they do to any snippet.

Leave two things as inert frozen metadata — do not rewrite them:

- the `monorepo:` frontmatter (a source path for the sync tool, which only ever writes to
  `_snippets/current/`; it does not render or link); and
- each snippet tree's `.sync-manifest.json` (records the ref the snippets were synced from).

When such a folding drops a URL (e.g. a `guides/cli/` section becoming a single `guides/cli` leaf),
that is an ordinary dropped page needing a redirect, and any stale links to the old path are
restructure fallout under step 9.

## Rules

- Never hand-edit `_redirects` — it is generated from `redirects.config.mjs` by
  `scripts/generate-redirects.mjs`
- No unrequested edits
- No links must remain from `content/archived` into `content/docs`, or from `content/docs` into
  `content/archived`
- Do not treat the branch as ready until the full `npm run build`, `check-redirects` and
  `check-external-links` all pass

## Scripts

Kept in this skill folder so each promotion reuses (and improves) them:

- `diff_pages.py` — the A-vs-current page-tree diff; prints the safety-net overrides to add.
- `freeze_archive_links.py` — the three archive link rewrites (prefix `/archive`, repoint
  snippet lane, pin GitHub tag), idempotent, dry-run by default.

Both take `--repo <mdk-docs path>` and print `--help`.

## Output

Branch is ready for commit and commit message provided.
