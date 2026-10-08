#!/usr/bin/env python3
"""Diff a retiring archive tree against the current docs tree (promotion step 4).

Finds pages present in the version about to be deleted (A) but absent from the
current tree, so each dropped URL gets an explicit safety-net redirect before A
leaves the disk. Run it while A is still present (before the delete in step 5).

For each A page with no current-tree counterpart it prints the derived URL and
whether the URL still resolves in current (parity via the catch-all) or needs an
explicit `/A/<path>` -> <current-target> override. Parked pages (a path segment
beginning with `_`) have no route and are skipped.

    python diff_pages.py --repo <mdk-docs> --old v0-8-0

This reports; it does not edit redirects.config.mjs — add the overrides by hand
(mirroring any existing unversioned mapping's target), per SKILL.md step 9.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def page_urls(tree: Path) -> dict[str, Path]:
    """Map each routable page's unversioned URL path -> file.

    Mirrors the site's routing: drop the `.mdx` suffix and a trailing `index`,
    and skip any page whose path has a `_`-prefixed (parked) segment.
    """
    urls: dict[str, Path] = {}
    for f in sorted(tree.rglob("*.mdx")):
        rel = f.relative_to(tree).with_suffix("")
        parts = rel.parts
        if any(p.startswith("_") for p in parts):
            continue
        if parts and parts[-1] == "index":
            parts = parts[:-1]
        urls["/" + "/".join(parts)] = f
    return urls


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", type=Path, required=True, help="path to the mdk-docs repo root")
    p.add_argument("--old", required=True, help="retiring archive dir slug, e.g. v0-8-0")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    old_tree = args.repo / "content" / "archived" / args.old
    cur_tree = args.repo / "content" / "docs"
    for t in (old_tree, cur_tree):
        if not t.is_dir():
            raise SystemExit(f"ABORT: not found: {t}")

    old_urls = page_urls(old_tree)
    cur_urls = page_urls(cur_tree)

    dropped = sorted(u for u in old_urls if u not in cur_urls)
    if not dropped:
        print(f"No pages in {args.old} are missing from current — catch-all `/{args.old}/*` -> /:splat covers everything.")
        return 0

    print(f"Pages in {args.old} with no current-tree URL (add these before deleting {args.old}):\n")
    slug = "/" + args.old
    for url in dropped:
        print(f"  {url}")
        print(f"    -> no parity: add override  {{ from: '{slug}{url}/', to: '<current-target>/' }}  in redirects.config.mjs")
    print(
        f"\nEverything else keeps path parity and is covered by the catch-all "
        f"{{ from: '{slug}/*', to: '/:splat' }}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
