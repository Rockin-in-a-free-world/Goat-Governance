#!/usr/bin/env python3
"""Reform links in a freshly-frozen mdk-docs archive tree (promotion step 7-8).

Applies the three mechanical rewrites that make a copied `content/docs` tree
self-contained under `/archive`, run against both the frozen docs tree
(`content/archived/<version>/`) and its snippet lane
(`content/archived/_snippets/<version>/`):

  1. Internal doc links  -> prefix root-relative docs routes with `/archive`
                            (/concepts, /guides, /reference, /support,
                             /tutorials, /llms-full.txt).
  2. Snippet includes    -> repoint the lane `_snippets/current/` to
                            `_snippets/<version>/`.
  3. GitHub source links -> pin `github.com/tetherto/mdk/blob/main` and
                            `.../tree/main` to the release tag (`blob/<tag>`).

The rewrite is idempotent: already-`/archive` links, an already-repointed lane,
and already-pinned refs are left untouched, so re-running is safe.

Defaults are a dry run; pass --apply to write. See SKILL.md steps 7-8.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Root-relative first segments that are docs routes (everything else — /src in a
# code sample, external URLs, github path segments — is left alone).
DOCS_ROUTES = ("concepts", "guides", "reference", "support", "tutorials")

# Match a docs route or /llms-full.txt only at a genuine link boundary:
#  - lookbehind blocks a preceding word char (already `/archive...`) or `/`
#    (a path segment inside a URL such as .../blob/main/guides/...);
#  - lookahead requires the segment to end (so /reference but not /referenced).
_ROUTE = "|".join(DOCS_ROUTES)
INTERNAL_LINK_RE = re.compile(
    r"(?<![\w/])(/(?:" + _ROUTE + r")|/llms-full\.txt)(?=[/\"#)\s]|$)"
)

GITHUB_MAIN_RE = re.compile(r"(github\.com/tetherto/mdk/(?:blob|tree))/main(?=[/\"#)\s]|$)")


def rewrite(text: str, version: str, tag: str) -> tuple[str, dict[str, int]]:
    """Return (new_text, counts-per-transform) for one file's contents."""
    counts = {"links": 0, "includes": 0, "github": 0}

    def prefix_link(m: re.Match) -> str:
        counts["links"] += 1
        return "/archive" + m.group(1)

    text = INTERNAL_LINK_RE.sub(prefix_link, text)

    lane_from = "_snippets/current/"
    lane_to = f"_snippets/{version}/"
    counts["includes"] = text.count(lane_from)
    text = text.replace(lane_from, lane_to)

    def pin(m: re.Match) -> str:
        counts["github"] += 1
        return f"{m.group(1)}/{tag}"

    text = GITHUB_MAIN_RE.sub(pin, text)

    return text, counts


def iter_targets(repo: Path, version: str) -> list[Path]:
    trees = [
        repo / "content" / "archived" / version,
        repo / "content" / "archived" / "_snippets" / version,
    ]
    files: list[Path] = []
    for tree in trees:
        if not tree.is_dir():
            sys.exit(f"ABORT: expected archive tree not found: {tree}")
        # .mdx pages plus meta.json nav files (whose descriptions carry internal links).
        files.extend(sorted(tree.rglob("*.mdx")))
        files.extend(sorted(tree.rglob("meta.json")))
    return files


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", type=Path, required=True, help="path to the mdk-docs repo root")
    p.add_argument("--version", required=True, help="archive dir slug, e.g. v0-9-0")
    p.add_argument("--tag", required=True, help="upstream release tag, e.g. v0.9.0")
    p.add_argument("--apply", action="store_true", help="write changes (omitted = dry run)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    files = iter_targets(args.repo, args.version)

    totals = {"links": 0, "includes": 0, "github": 0}
    changed = 0
    for path in files:
        original = path.read_text(encoding="utf-8")
        new, counts = rewrite(original, args.version, args.tag)
        if new == original:
            continue
        changed += 1
        for k in totals:
            totals[k] += counts[k]
        rel = path.relative_to(args.repo)
        print(f"  {rel}  links+{counts['links']} includes+{counts['includes']} github+{counts['github']}")
        if args.apply:
            path.write_text(new, encoding="utf-8")

    mode = "APPLIED" if args.apply else "DRY RUN (pass --apply to write)"
    print(
        f"\n{mode}: {changed}/{len(files)} files, "
        f"links+{totals['links']} includes+{totals['includes']} github+{totals['github']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
