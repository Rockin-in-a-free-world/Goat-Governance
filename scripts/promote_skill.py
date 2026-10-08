#!/usr/bin/env python3
"""Promote a reviewed candidate and atomically update approval metadata."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from scan_skills import (
    DEFAULT_RULES,
    NAME_RE,
    REPO_ROOT,
    SEVERITY_RANK,
    digest_skill_tree,
    load_rules,
    parse_frontmatter,
    render_claude_wrapper,
    scan_skill,
    verify_registry,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("skill", help="candidate skill name")
    result.add_argument("--approved-by", required=True, help="human reviewer identity")
    result.add_argument("--source", required=True, help="reviewed source or provenance")
    result.add_argument("--review-note", required=True, help="what the human reviewer checked")
    result.add_argument("--accept-risk", action="append", default=[], metavar="RULE_ID", help="explicitly accept one medium-risk rule ID")
    result.add_argument("--apply", action="store_true", help="apply the promotion; omission is a dry run")
    result.add_argument("--replace", action="store_true", help="replace an existing approved skill and retain its registry history")
    result.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    return result


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = args.root.resolve()
    name = args.skill
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        print("ERROR: skill name must be kebab-case and at most 64 characters", file=sys.stderr)
        return 2
    if not args.approved_by.strip() or not args.source.strip() or not args.review_note.strip():
        print("ERROR: approval identity, source, and review note cannot be blank", file=sys.stderr)
        return 2

    candidate = root / "skills" / "candidates" / name
    approved = root / "skills" / "approved" / name
    registry_path = root / "registry" / "approved-skills.json"
    wrapper_dir = root / ".claude" / "skills" / name
    if not candidate.is_dir() or candidate.is_symlink():
        print(f"ERROR: candidate does not exist as a regular directory: {candidate}", file=sys.stderr)
        return 2
    if approved.exists() and not args.replace:
        print("ERROR: approved skill already exists; use --replace for an explicitly reviewed update", file=sys.stderr)
        return 2
    if args.replace and not approved.is_dir():
        print("ERROR: --replace requires an existing approved skill", file=sys.stderr)
        return 2

    rules = load_rules(DEFAULT_RULES if root == REPO_ROOT else root / "rules" / "scanning-rules.json")
    integrity_findings = verify_registry(root, rules, name)
    if integrity_findings:
        for item in integrity_findings:
            print(f"{item.severity.upper()} {item.rule_id} {item.path}: {item.message}", file=sys.stderr)
        print("ERROR: existing approval state is inconsistent; repair it in a separate reviewed change", file=sys.stderr)
        return 2
    findings = scan_skill(candidate, rules, root)
    blockers = [item for item in findings if SEVERITY_RANK[item.severity] >= SEVERITY_RANK["high"]]
    medium_ids = {item.rule_id for item in findings if item.severity == "medium"}
    accepted = set(args.accept_risk)
    missing_acceptance = medium_ids - accepted
    unknown_acceptance = accepted - medium_ids
    if blockers:
        for item in blockers:
            print(f"{item.severity.upper()} {item.rule_id} {item.path}: {item.message}", file=sys.stderr)
        print("ERROR: critical and high findings cannot be promoted", file=sys.stderr)
        return 1
    if missing_acceptance:
        print(f"ERROR: medium findings require --accept-risk for: {', '.join(sorted(missing_acceptance))}", file=sys.stderr)
        return 1
    if unknown_acceptance:
        print(f"ERROR: accepted risk IDs not present in the scan: {', '.join(sorted(unknown_acceptance))}", file=sys.stderr)
        return 2

    metadata, metadata_errors, _ = parse_frontmatter((candidate / "SKILL.md").read_text(encoding="utf-8"), rules["limits"]["max_frontmatter_lines"])
    if metadata_errors or not metadata.get("description"):
        print("ERROR: cannot create discovery wrapper from invalid frontmatter", file=sys.stderr)
        return 2

    candidate_digest = digest_skill_tree(candidate)
    print(f"Candidate: {name}")
    print(f"Digest:    {candidate_digest}")
    print(f"Findings:  {len(findings)} ({len(medium_ids)} accepted medium-risk rule IDs)")
    print(f"Action:    {'replace' if args.replace else 'promote'}")
    if not args.apply:
        print("DRY RUN: no files changed; repeat with --apply only after explicit human approval")
        return 0

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read registry: {exc}", file=sys.stderr)
        return 2
    if registry.get("schema_version") != 1 or not isinstance(registry.get("skills"), dict):
        print("ERROR: invalid registry schema", file=sys.stderr)
        return 2

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    previous = registry["skills"].get(name)
    history = list(previous.get("history", [])) if isinstance(previous, dict) else []
    if previous:
        history.append({key: previous.get(key) for key in ("approved_at", "approved_by", "digest", "source", "review_note", "accepted_risks")})
    entry = {
        "status": "approved",
        "digest": candidate_digest,
        "approved_at": now,
        "approved_by": [args.approved_by.strip()],
        "source": args.source.strip(),
        "review_note": args.review_note.strip(),
        "accepted_risks": sorted(accepted),
        "scan_findings": [
            {"rule_id": item.rule_id, "severity": item.severity, "path": item.path, "line": item.line}
            for item in findings
        ],
        "history": history,
    }

    approved.parent.mkdir(parents=True, exist_ok=True)
    wrapper_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}.staging.", dir=approved.parent))
    backup = approved.parent / f".{name}.backup"
    wrapper_backup = wrapper_dir.parent / f".{name}.backup"
    committed = False
    approved_backed_up = False
    wrapper_backed_up = False
    approved_installed = False
    wrapper_installed = False
    candidate_consumed = False
    consumed_candidate = staging / "consumed-candidate"
    try:
        shutil.copytree(candidate, staging / name, symlinks=True)
        if digest_skill_tree(staging / name) != candidate_digest:
            raise RuntimeError("staged copy digest differs from reviewed candidate")
        staged_wrapper = staging / "claude-wrapper"
        staged_wrapper.mkdir()
        (staged_wrapper / "SKILL.md").write_text(render_claude_wrapper(name, metadata["description"]), encoding="utf-8")
        if backup.exists() or wrapper_backup.exists():
            raise RuntimeError("stale promotion backup blocks promotion")
        if approved.exists():
            os.replace(approved, backup)
            approved_backed_up = True
        if wrapper_dir.exists():
            os.replace(wrapper_dir, wrapper_backup)
            wrapper_backed_up = True
        os.replace(staging / name, approved)
        approved_installed = True
        os.replace(staged_wrapper, wrapper_dir)
        wrapper_installed = True
        os.replace(candidate, consumed_candidate)
        candidate_consumed = True
        registry["skills"][name] = entry
        atomic_json_write(registry_path, registry)
        committed = True
    except Exception as exc:
        if not committed:
            if approved_installed and approved.exists():
                shutil.rmtree(approved)
            if approved_backed_up and backup.exists():
                os.replace(backup, approved)
            if wrapper_installed and wrapper_dir.exists():
                shutil.rmtree(wrapper_dir)
            if wrapper_backed_up and wrapper_backup.exists():
                os.replace(wrapper_backup, wrapper_dir)
            if candidate_consumed and consumed_candidate.exists():
                os.replace(consumed_candidate, candidate)
        print(f"ERROR: promotion failed and rollback was attempted: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    for old_path in (backup, wrapper_backup):
        try:
            if old_path.exists():
                shutil.rmtree(old_path)
        except OSError as exc:
            print(f"WARNING: promotion succeeded but old backup remains at {old_path}: {exc}", file=sys.stderr)

    print("APPLIED: approved skill, discovery wrapper, and registry updated; candidate consumed")
    print("NEXT: run unit tests and python3 scripts/scan_skills.py --scope all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
