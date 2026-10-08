---
name: mdk-docs-release
description: >
  Promotes the newest version of MDK, archives the previous version, deletes the prior version.
---

# Promote

You are a senior technical writer. You always review the processes in maintainers/content/versioning.md to understand
the workflow.

## Curious

You have access to the user as a colleague. You ask questions rather than make assumptions.

## The process

We will call the outgoing version A, the previous current version that will become the archive B, and the new
version C.

Version slugs take two forms: the **dir/URL slug** with dashes (`v0-9-0`, used for
`content/archived/<slug>/`, `_snippets/<slug>/`, `redirects.config.mjs`, `archive.meta.yaml`)
and the **release tag** with dots (`v0.9.0`, used only inside `github.com/...` source URLs).
`archive.meta.yaml` stores both (`archived_version` = dash slug, `archived_label` = dot label).

1. Under mdk-docs/content/archived, create a new folder for B.
2. Copy the entire current mdk-docs/content/docs folder into the folder created at 1.
3. Update the archive.meta.yaml for the version numbers for B and C (`archived_version`/`archived_label` = B, `current_version` = C). Do this before regenerating redirects in step 9, since the generator reads the active archive slug from here.
4. Diff the page trees of A against the folder for B (just created in steps 1-2) to find pages present in A but missing from B. Each needs an explicit redirect mapping for `/A/*` to the closest current equivalent (reuse an existing unversioned mapping's target when one exists) — do this before deleting A in step 5, while A's tree is still on disk to diff against.
   - Run `diff_pages.py --repo <mdk-docs> --old A` (in this skill folder). It lists each A page with no current-tree URL and the override to add; parked (`_`-prefixed) pages are skipped (no route). Parity pages need nothing beyond the catch-all.
5. Delete the folder for A.
6. Delete mdk-docs/content/archived/_snippets/A and copy the entire mdk-docs/content/_snippets/current folder into mdk-docs/content/archived/_snippets/B.
> You now have all the archive B assets.
7. Reform every link for mdk-docs/content/archived so that nothing for archive B reaches outside of mdk-docs/content/archived: all includes, all page links, everything should be self contained within the archive.
8. Pin every GitHub source link inside the new archive B trees (`mdk-docs/content/archived/B` and `mdk-docs/content/archived/_snippets/B`) from blob/main / tree/main to blob/vB / tree/vB, per maintainers/content/urls-and-links.md. Verify with `npm run check-external-links`.
   - Steps 7-8 are automated by `freeze_archive_links.py --repo <mdk-docs> --version B --tag vB` (in this skill folder; `--version` is the dash slug, `--tag` is the dot tag). Run with no `--apply` first to preview, then with `--apply`. It (a) prefixes root-relative docs routes (`/concepts`, `/guides`, `/reference`, `/support`, `/tutorials`, `/llms-full.txt`) with `/archive`, (b) repoints `_snippets/current/` includes to `_snippets/B/`, and (c) pins `blob|tree/main` to the tag. It processes both `*.mdx` and `meta.json` (nav descriptions carry links). It is idempotent. Confirm the tag `vB` exists upstream first (`git ls-remote --tags https://github.com/tetherto/mdk.git vB`), or the pinned links 404.
9. Update the redirect rules for the deleted version A in redirects.config.mjs: add A to retiredVersionSlugs and add its safety-net mapping(s) — including the explicit per-page mappings found in step 4, placed before the catch-all `/A/*` splat — in the same change as step 5 (not as a follow-up, or old A URLs 404 with no way back). Then regenerate `_redirects` with `npm run build:redirects`.
10. Verify. Clear caches and rebuild:
    - Delete the build caches (`.next`, `node_modules/.cache`, `out`), then regenerate the fumadocs source with `npx fumadocs-mdx` (the `.source` index caches the old A paths; a stale one makes `check:nav` throw MODULE_NOT_FOUND on the deleted tree).
    - Run `npm run check:nav`, `npm run check:snippets`, `npm run check-redirects`, `npm run check-external-links`, then the full `npm run build` (which also runs next-broken-links, check-built-links, check:maintainers).
    - **Restructure fallout:** if the new release folded or renamed a page, shared snippets can still link to the old path. The current tree hides this via a slug redirect, but the static archive has none, so `next-broken-links` flags `/archive/<old-path>`. Repoint those links inside the archive to the surviving page (e.g. a folded `guides/cli/install` -> `guides/cli`). This is part of step 7's "self-contained" mandate, not day-to-day archive editing.

## Monorepo (port-sync) snippets

Some current pages are single leaf `.mdx` files that pull their body from a monorepo-synced
snippet under `content/_snippets/current/monorepo/**` (an `<include>` plus a `monorepo:` source-path
frontmatter field), replacing what older releases authored as multi-page directories with their own
`meta.json`. The freeze needs no special case for these: they live under `_snippets/`, so step 7-8's
lane repoint (`_snippets/current/` -> `_snippets/B/`), `/archive` link prefixing, and GitHub tag
pinning all apply through `freeze_archive_links.py` as they do to any snippet.

Leave two things as inert frozen metadata — do not rewrite them:
- the `monorepo:` frontmatter (a source path for the sync tool, which only ever writes to `_snippets/current/`; it does not render or link); and
- each snippet tree's `.sync-manifest.json` (records the ref the snippets were synced from).

When such a folding drops a URL (e.g. a `guides/cli/` section becoming a single `guides/cli` leaf),
that is an ordinary step-4 dropped page needing a redirect, and any stale links to the old path are
step-10 restructure fallout.

## Rules

- Never hand-edit `_redirects` — it is generated from redirects.config.mjs by scripts/generate-redirects.mjs
- No unrequested edits
- No links must remain from mdk-docs/content/archived into mdk-docs/content/docs, or from mdk-docs/content/docs into mdk-docs/content/archived
- Do not treat the branch as ready until the full `npm run build`, `check-redirects`, and `check-external-links` all pass

## Scripts

Kept in this skill folder so each promotion reuses (and improves) them:

- `diff_pages.py` — step 4. A-vs-current page-tree diff; prints the safety-net overrides to add.
- `freeze_archive_links.py` — steps 7-8. The three archive link rewrites (prefix `/archive`, repoint snippet lane, pin GitHub tag), idempotent, dry-run by default.

Both take `--repo <mdk-docs path>` and print `--help`.

## Output

Branch is ready for commit and commit message provided.
