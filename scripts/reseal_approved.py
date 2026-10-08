#!/usr/bin/env python3
"""Scan and reseal a human-reviewed in-place edit to approved content."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from promote_mcp import render_index as render_mcp_index
from promote_memory import atomic_json_write, atomic_write, render_index as render_memory_index
from scan_mcp import (
    ALLOWED_AUTH,
    ALLOWED_TRANSPORTS,
    ENTRY_NAME_RE as MCP_NAME_RE,
    digest_mcp_file,
    parse_mcp_frontmatter,
    scan_mcp_entry,
    verify_registry as verify_mcp_registry,
)
from scan_memory import (
    ALLOWED_TYPES,
    ENTRY_NAME_RE as MEMORY_NAME_RE,
    digest_memory_file,
    parse_memory_frontmatter,
    scan_memory_entry,
    verify_registry as verify_memory_registry,
)
from scan_skills import (
    NAME_RE as SKILL_NAME_RE,
    REPO_ROOT,
    SEVERITY_RANK,
    digest_skill_tree,
    load_rules,
    parse_frontmatter,
    render_claude_wrapper,
    scan_skill,
    verify_registry as verify_skill_registry,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("kind", choices=("skill", "memory", "mcp"))
    result.add_argument("name", help="approved item name")
    result.add_argument("--approved-by", required=True, help="human reviewer identity")
    result.add_argument("--review-note", required=True, help="what the human reviewer checked")
    result.add_argument(
        "--maintainer-edit",
        action="store_true",
        help="attest that the current approved bytes are maintainer-made or maintainer-reviewed and contain no unreviewed external material",
    )
    result.add_argument("--accept-risk", action="append", default=[], metavar="RULE_ID")
    result.add_argument("--apply", action="store_true", help="apply the reseal; omission is a dry run")
    result.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    return result


def finding_subject(item: object) -> str | None:
    return getattr(item, "skill", getattr(item, "entry", None))


def print_findings(findings: list[object]) -> None:
    for item in findings:
        location = item.path + (f":{item.line}" if item.line else "")
        print(f"{item.severity.upper()} {item.rule_id} {location}: {item.message}", file=sys.stderr)


def read_registry(path: Path, key: str) -> dict:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1 or not isinstance(registry.get(key), dict):
        raise ValueError(f"registry must use schema_version 1 and contain a {key} object")
    return registry


def restore_generated(path: Path, previous: str | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        atomic_write(path, previous)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = args.root.resolve()
    name = args.name
    if not args.approved_by.strip() or not args.review_note.strip():
        print("ERROR: approval identity and review note cannot be blank", file=sys.stderr)
        return 2
    if args.apply and not args.maintainer_edit:
        print("ERROR: --apply requires --maintainer-edit human attestation", file=sys.stderr)
        return 2

    try:
        rules = load_rules(root / "rules" / "scanning-rules.json")
    except Exception as exc:
        print(f"ERROR: cannot load scanning rules: {exc}", file=sys.stderr)
        return 2

    generated_path: Path
    generated_content: str
    extra: dict
    if args.kind == "skill":
        if not SKILL_NAME_RE.fullmatch(name) or len(name) > 64:
            print("ERROR: skill name must be kebab-case and at most 64 characters", file=sys.stderr)
            return 2
        approved = root / "skills" / "approved" / name
        registry_path = root / "registry" / "approved-skills.json"
        registry_key = "skills"
        verifier = verify_skill_registry
        allowed_integrity = {"DIGEST_MISMATCH", "CLAUDE_WRAPPER_MISMATCH", "MISSING_CLAUDE_WRAPPER"}
        findings = scan_skill(approved, rules, root)
        skill_file = approved / "SKILL.md"
        metadata, errors, _ = parse_frontmatter(
            skill_file.read_text(encoding="utf-8") if skill_file.is_file() else "",
            rules["limits"]["max_frontmatter_lines"],
        )
        if errors or not metadata.get("description"):
            print("ERROR: cannot reseal invalid skill frontmatter", file=sys.stderr)
            return 2
        digest = digest_skill_tree(approved)
        generated_path = root / ".claude" / "skills" / name / "SKILL.md"
        generated_content = render_claude_wrapper(name, metadata["description"])
        extra = {}
    elif args.kind == "memory":
        if not MEMORY_NAME_RE.fullmatch(name) or len(name) > 64:
            print("ERROR: memory name must be lowercase snake_case and at most 64 characters", file=sys.stderr)
            return 2
        approved = root / "memory" / "approved" / f"{name}.md"
        registry_path = root / "registry" / "approved-memory.json"
        registry_key = "entries"
        verifier = verify_memory_registry
        allowed_integrity = {"DIGEST_MISMATCH"}
        findings = scan_memory_entry(approved, rules, root)
        metadata, memory_type, errors = parse_memory_frontmatter(
            approved.read_text(encoding="utf-8") if approved.is_file() else "",
            rules["limits"]["max_frontmatter_lines"],
        )
        if errors or not metadata.get("description") or memory_type not in ALLOWED_TYPES:
            print("ERROR: cannot reseal invalid memory frontmatter", file=sys.stderr)
            return 2
        digest = digest_memory_file(approved)
        extra = {"description": metadata["description"], "memory_type": memory_type}
        generated_path = root / "memory" / "approved" / "MEMORY.md"
        generated_content = ""
    else:
        if not MCP_NAME_RE.fullmatch(name) or len(name) > 64:
            print("ERROR: MCP name must be lowercase snake_case and at most 64 characters", file=sys.stderr)
            return 2
        approved = root / "mcp" / "approved" / f"{name}.md"
        registry_path = root / "registry" / "approved-mcp.json"
        registry_key = "entries"
        verifier = verify_mcp_registry
        allowed_integrity = {"DIGEST_MISMATCH"}
        findings = scan_mcp_entry(approved, rules, root)
        top, metadata, errors = parse_mcp_frontmatter(
            approved.read_text(encoding="utf-8") if approved.is_file() else "",
            rules["limits"]["max_frontmatter_lines"],
        )
        transport = metadata.get("transport")
        auth = metadata.get("auth")
        if errors or not top.get("description") or transport not in ALLOWED_TRANSPORTS or auth not in ALLOWED_AUTH:
            print("ERROR: cannot reseal invalid MCP frontmatter", file=sys.stderr)
            return 2
        digest = digest_mcp_file(approved)
        extra = {
            "description": top["description"],
            "transport": transport,
            "auth": auth,
            "host": metadata.get("host"),
        }
        generated_path = root / "mcp" / "approved" / "MCP.md"
        generated_content = ""

    integrity = verifier(root, rules)
    unexpected = [
        item
        for item in integrity
        if not (finding_subject(item) == name and item.rule_id in allowed_integrity)
    ]
    target_changes = [
        item
        for item in integrity
        if finding_subject(item) == name and item.rule_id in allowed_integrity
    ]
    if unexpected:
        print_findings(unexpected)
        print("ERROR: unrelated or structural approval integrity failures block resealing", file=sys.stderr)
        return 2
    if not target_changes:
        print("ERROR: approved item already verifies; there is nothing to reseal", file=sys.stderr)
        return 2

    if findings:
        print("SCAN FINDINGS:", file=sys.stderr)
        print_findings(findings)

    blockers = [item for item in findings if SEVERITY_RANK[item.severity] >= SEVERITY_RANK["high"]]
    medium_ids = {item.rule_id for item in findings if item.severity == "medium"}
    accepted = set(args.accept_risk)
    if blockers:
        print_findings(blockers)
        print("ERROR: critical and high findings cannot be resealed", file=sys.stderr)
        return 1
    missing_acceptance = medium_ids - accepted
    unknown_acceptance = accepted - medium_ids
    if missing_acceptance:
        print(f"ERROR: medium findings require --accept-risk for: {', '.join(sorted(missing_acceptance))}", file=sys.stderr)
        return 1
    if unknown_acceptance:
        print(f"ERROR: accepted risk IDs not present in the scan: {', '.join(sorted(unknown_acceptance))}", file=sys.stderr)
        return 2

    try:
        registry = read_registry(registry_path, registry_key)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: cannot read registry: {exc}", file=sys.stderr)
        return 2
    previous = registry[registry_key].get(name)
    if not isinstance(previous, dict):
        print("ERROR: resealing requires an existing registry entry", file=sys.stderr)
        return 2

    print(f"Approved:  {args.kind}/{name}")
    print(f"Digest:    {digest}")
    print(f"Findings:  {len(findings)} ({len(medium_ids)} accepted medium-risk rule IDs)")
    print("Action:    reseal maintainer edit")
    if not args.apply:
        print("DRY RUN: no files changed; discuss the scan and repeat with --maintainer-edit --apply after explicit human approval")
        return 0

    history = list(previous.get("history", []))
    history.append({key: value for key, value in previous.items() if key != "history"})
    entry = dict(previous)
    entry.update(
        {
            "status": "approved",
            "digest": digest,
            "approved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "approved_by": [args.approved_by.strip()],
            "source": "maintainer-edit",
            "review_note": args.review_note.strip(),
            "accepted_risks": sorted(accepted),
            "scan_findings": [
                {"rule_id": item.rule_id, "severity": item.severity, "path": item.path, "line": item.line}
                for item in findings
            ],
            "history": history,
            **extra,
        }
    )
    registry[registry_key][name] = entry
    if args.kind == "memory":
        generated_content = render_memory_index(registry)
    elif args.kind == "mcp":
        generated_content = render_mcp_index(registry)

    old_registry = registry_path.read_text(encoding="utf-8")
    old_generated = generated_path.read_text(encoding="utf-8") if generated_path.is_file() else None
    try:
        atomic_write(generated_path, generated_content)
        atomic_json_write(registry_path, registry)
        post_findings = verifier(root, rules, name)
        if post_findings:
            raise RuntimeError("post-reseal integrity verification failed")
    except Exception as exc:
        atomic_write(registry_path, old_registry)
        restore_generated(generated_path, old_generated)
        print(f"ERROR: reseal failed and rollback was attempted: {exc}", file=sys.stderr)
        return 2

    print("APPLIED: approved content resealed; registry history and generated metadata updated")
    print("NEXT: run the full unit tests and all three repository scans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
