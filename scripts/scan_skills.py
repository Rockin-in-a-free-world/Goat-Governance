#!/usr/bin/env python3
"""Dependency-free static scanner and integrity verifier for governed skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = REPO_ROOT / "rules" / "scanning-rules.json"
DEFAULT_REGISTRY = REPO_ROOT / "registry" / "approved-skills.json"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


class ScannerError(RuntimeError):
    """Raised when scanner configuration or input cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    skill: str
    path: str
    line: int | None
    message: str


def _repo_display(path: Path, root: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def load_rules(path: Path = DEFAULT_RULES) -> dict[str, Any]:
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScannerError(f"cannot load scanning rules from {path}: {exc}") from exc

    if rules.get("schema_version") != 1:
        raise ScannerError("unsupported scanning-rules schema_version")
    threshold = rules.get("blocking_severity")
    if threshold not in SEVERITY_RANK:
        raise ScannerError(f"invalid blocking_severity: {threshold!r}")

    seen: set[str] = set()
    for entry in rules.get("patterns", []):
        rule_id = entry.get("id")
        severity = entry.get("severity")
        if not isinstance(rule_id, str) or not rule_id or rule_id in seen:
            raise ScannerError(f"invalid or duplicate pattern id: {rule_id!r}")
        if severity not in SEVERITY_RANK:
            raise ScannerError(f"invalid severity for {rule_id}: {severity!r}")
        try:
            re.compile(entry["regex"], re.MULTILINE)
        except (KeyError, re.error) as exc:
            raise ScannerError(f"invalid regex for {rule_id}: {exc}") from exc
        seen.add(rule_id)
    return rules


def _decode_scalar(value: str) -> str | None:
    value = value.strip()
    if not value or value[0] in "|>":
        return None
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, str) else None
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            return None
        return value[1:-1].replace("''", "'")
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value or None


BLOCK_SCALAR_RE = re.compile(r"^([|>])[+-]?\d*$")


def _fold_block_lines(lines: list[str], style: str) -> str:
    """Join a YAML block-scalar body. '>' folds each paragraph onto one line
    (a blank line starts a new paragraph); '|' keeps one line per entry.
    Simplified for prose frontmatter values, not a full YAML implementation.
    """
    if style == "|":
        return "\n".join(lines).rstrip("\n")
    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return "\n".join(paragraphs)


def parse_frontmatter(text: str, max_lines: int = 80) -> tuple[dict[str, str], list[str], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md must start with YAML frontmatter"], 0

    end = 0
    for index, line in enumerate(lines[1 : max_lines + 1], start=1):
        if line.strip() == "---":
            end = index
            break
    if not end:
        return {}, [f"frontmatter must close within {max_lines} lines"], 0

    metadata: dict[str, str] = {}
    errors: list[str] = []
    body = lines[1:end]
    i = 0
    while i < len(body):
        line = body[i]
        number = i + 2
        if not line.strip() or line.lstrip().startswith("#") or line[0].isspace():
            i += 1
            continue
        match = KEY_RE.match(line)
        if not match:
            errors.append(f"unsupported top-level frontmatter syntax on line {number}")
            i += 1
            continue
        key, raw_value = match.group(1), match.group(2) or ""
        if key in metadata:
            errors.append(f"duplicate frontmatter key {key!r} on line {number}")
            i += 1
            continue
        block_match = BLOCK_SCALAR_RE.match(raw_value.strip()) if raw_value.strip() else None
        if block_match:
            block_lines: list[str] = []
            j = i + 1
            while j < len(body) and (not body[j].strip() or body[j][0].isspace()):
                block_lines.append(body[j].strip())
                j += 1
            metadata[key] = _fold_block_lines(block_lines, block_match.group(1))
            i = j
            continue
        value = _decode_scalar(raw_value)
        if value is not None:
            metadata[key] = value
        i += 1
    return metadata, errors, end + 1


def digest_skill_tree(skill_dir: Path) -> str:
    if not skill_dir.is_dir() or skill_dir.is_symlink():
        raise ScannerError(f"skill directory is missing or is a symlink: {skill_dir}")
    digest = hashlib.sha256()
    files = sorted(path for path in skill_dir.rglob("*") if path.is_file() or path.is_symlink())
    for path in files:
        if path.is_symlink():
            raise ScannerError(f"cannot digest symlink: {path}")
        relative = path.relative_to(skill_dir).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def render_claude_wrapper(name: str, description: str) -> str:
    quoted_description = json.dumps(description, ensure_ascii=False)
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {quoted_description}\n"
        "---\n\n"
        f"<!-- Generated discovery wrapper. Canonical source: skills/approved/{name}/SKILL.md -->\n\n"
        f"Read and follow `../../../skills/approved/{name}/SKILL.md` before continuing. "
        "That approved file is authoritative; this wrapper exists only so Claude Code can "
        "discover it without a machine-local installation.\n"
    )


def _finding(
    rule_id: str,
    severity: str,
    skill: str,
    path: Path,
    message: str,
    line: int | None = None,
    root: Path = REPO_ROOT,
) -> Finding:
    return Finding(rule_id, severity, skill, _repo_display(path, root), line, message)


def scan_skill(skill_dir: Path, rules: dict[str, Any], root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    name = skill_dir.name
    limits = rules["limits"]

    if skill_dir.is_symlink():
        return [_finding("SYMLINK_SKILL", "critical", name, skill_dir, "skill directory must not be a symlink", root=root)]
    if not skill_dir.is_dir():
        return [_finding("INVALID_SKILL_PATH", "critical", name, skill_dir, "skill path is not a directory", root=root)]
    if not NAME_RE.fullmatch(name) or len(name) > 64:
        findings.append(_finding("INVALID_SKILL_NAME", "high", name, skill_dir, "directory name must be kebab-case and at most 64 characters", root=root))

    entries = sorted(path for path in skill_dir.rglob("*") if path.is_file() or path.is_symlink())
    if len(entries) > limits["max_files"]:
        findings.append(_finding("TOO_MANY_FILES", "high", name, skill_dir, f"skill has {len(entries)} files; maximum is {limits['max_files']}", root=root))

    total_bytes = 0
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file() or skill_file.is_symlink():
        findings.append(_finding("MISSING_SKILL_FILE", "critical", name, skill_file, "required regular file SKILL.md is missing", root=root))

    text_extensions = set(rules["text_extensions"])
    denied_names = set(rules["denied_filenames"])
    decoded: dict[Path, str] = {}
    for path in entries:
        relative = path.relative_to(skill_dir)
        if path.is_symlink():
            findings.append(_finding("SYMLINK_FILE", "critical", name, path, "symlinks are not permitted in governed skills", root=root))
            continue
        try:
            size = path.stat().st_size
        except OSError as exc:
            findings.append(_finding("UNREADABLE_FILE", "critical", name, path, str(exc), root=root))
            continue
        total_bytes += size
        if size > limits["max_file_bytes"]:
            findings.append(_finding("FILE_TOO_LARGE", "high", name, path, f"file is {size} bytes; maximum is {limits['max_file_bytes']}", root=root))
        if path.name in denied_names or path.name.startswith(".env."):
            findings.append(_finding("DENIED_FILENAME", "critical", name, path, "credential-like files are forbidden", root=root))
        if path.name != "SKILL.md" and path.suffix.lower() not in text_extensions:
            findings.append(_finding("OPAQUE_FILE", "high", name, path, f"opaque file type {path.suffix or '<none>'!r} cannot be statically reviewed", root=root))
            continue
        try:
            decoded[path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(_finding("NON_UTF8_FILE", "high", name, path, f"text file is not valid UTF-8: {exc}", root=root))

        if any(part.startswith(".") for part in relative.parts):
            findings.append(_finding("HIDDEN_FILE", "medium", name, path, "hidden files require explicit review", root=root))

    if total_bytes > limits["max_total_bytes"]:
        findings.append(_finding("SKILL_TOO_LARGE", "high", name, skill_dir, f"skill is {total_bytes} bytes; maximum is {limits['max_total_bytes']}", root=root))

    if skill_file in decoded:
        metadata, metadata_errors, _ = parse_frontmatter(decoded[skill_file], limits["max_frontmatter_lines"])
        for message in metadata_errors:
            findings.append(_finding("INVALID_FRONTMATTER", "high", name, skill_file, message, line=1, root=root))
        for required in rules["required_frontmatter"]:
            if not metadata.get(required):
                findings.append(_finding("MISSING_FRONTMATTER", "high", name, skill_file, f"missing simple scalar frontmatter field {required!r}", line=1, root=root))
        if metadata.get("name") and metadata["name"] != name:
            findings.append(_finding("NAME_MISMATCH", "high", name, skill_file, f"frontmatter name {metadata['name']!r} does not match directory", line=1, root=root))
        for key in rules["high_risk_frontmatter"]:
            if re.search(rf"(?m)^{re.escape(key)}\s*:", decoded[skill_file]):
                findings.append(_finding("HIGH_RISK_FRONTMATTER", "high", name, skill_file, f"frontmatter field {key!r} can grant tools or register executable hooks", line=1, root=root))

    for path, content in decoded.items():
        for pattern in rules["patterns"]:
            match = re.search(pattern["regex"], content, re.MULTILINE)
            if match:
                line = content.count("\n", 0, match.start()) + 1
                findings.append(_finding(pattern["id"], pattern["severity"], name, path, pattern["description"], line=line, root=root))

    return findings


def discover_skill_dirs(base: Path, selected: str | None = None) -> list[Path]:
    if not base.exists():
        return []
    if not base.is_dir() or base.is_symlink():
        raise ScannerError(f"skill collection is not a regular directory: {base}")
    if selected:
        if not NAME_RE.fullmatch(selected):
            raise ScannerError(f"invalid skill selector: {selected!r}")
        candidate = base / selected
        return [candidate] if candidate.exists() else []
    return sorted(path for path in base.iterdir() if path.name != ".gitkeep")


def verify_registry(root: Path, rules: dict[str, Any], selected: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    registry_path = root / "registry" / "approved-skills.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [_finding("INVALID_REGISTRY", "critical", "<registry>", registry_path, str(exc), root=root)]

    if registry.get("schema_version") != 1 or not isinstance(registry.get("skills"), dict):
        return [_finding("INVALID_REGISTRY", "critical", "<registry>", registry_path, "registry must use schema_version 1 and contain a skills object", root=root)]

    approved_root = root / "skills" / "approved"
    approved_names = {path.name for path in discover_skill_dirs(approved_root, selected)}
    entries: dict[str, Any] = registry["skills"]
    registry_names = {selected} & set(entries) if selected else set(entries)
    wrapper_names = {
        path.name
        for path in discover_skill_dirs(root / ".claude" / "skills", selected)
    }

    for name in sorted(approved_names | registry_names | wrapper_names):
        if not NAME_RE.fullmatch(name) or len(name) > 64:
            findings.append(_finding("INVALID_REGISTRY_NAME", "critical", name, registry_path, "registry skill name must be kebab-case and at most 64 characters", root=root))
            continue
        skill_dir = approved_root / name
        entry = entries.get(name)
        if name in wrapper_names and name not in approved_names and name not in registry_names:
            wrapper_path = root / ".claude" / "skills" / name
            findings.append(_finding("ORPHAN_CLAUDE_WRAPPER", "critical", name, wrapper_path, "Claude discovery wrapper has no approved skill or registry entry", root=root))
            continue
        if not skill_dir.is_dir():
            findings.append(_finding("REGISTRY_ORPHAN", "critical", name, registry_path, "registry entry has no approved skill directory", root=root))
            continue
        if not isinstance(entry, dict):
            findings.append(_finding("UNREGISTERED_APPROVED_SKILL", "critical", name, skill_dir, "approved directory has no registry entry", root=root))
            continue
        try:
            actual_digest = digest_skill_tree(skill_dir)
        except (OSError, ScannerError) as exc:
            findings.append(_finding("DIGEST_FAILURE", "critical", name, skill_dir, str(exc), root=root))
            continue
        if entry.get("digest") != actual_digest:
            findings.append(_finding("DIGEST_MISMATCH", "critical", name, skill_dir, f"registry has {entry.get('digest')!r}; actual digest is {actual_digest}", root=root))
        if entry.get("status") != "approved" or not entry.get("approved_by") or not entry.get("approved_at"):
            findings.append(_finding("INCOMPLETE_APPROVAL", "critical", name, registry_path, "approval metadata is incomplete", root=root))

        skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8") if (skill_dir / "SKILL.md").is_file() else ""
        metadata, _, _ = parse_frontmatter(skill_text, rules["limits"]["max_frontmatter_lines"])
        expected_wrapper = render_claude_wrapper(name, metadata.get("description", ""))
        wrapper_path = root / ".claude" / "skills" / name / "SKILL.md"
        try:
            actual_wrapper = wrapper_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            findings.append(_finding("MISSING_CLAUDE_WRAPPER", "critical", name, wrapper_path, str(exc), root=root))
        else:
            if actual_wrapper != expected_wrapper:
                findings.append(_finding("CLAUDE_WRAPPER_MISMATCH", "critical", name, wrapper_path, "generated discovery wrapper does not match the approved skill", root=root))

    return findings


def list_approved_skills(root: Path, rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Inventory every approved skill for session-start selection.

    Each row reports whether the skill's digest and Claude wrapper verify. A
    caller (human or agent) proposing a session's skill set must exclude any
    row with verified=False rather than silently repair or ignore it.
    """
    findings = verify_registry(root, rules)
    unverified = {item.skill for item in findings}

    registry_path = root / "registry" / "approved-skills.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScannerError(f"cannot read registry: {exc}") from exc

    inventory: list[dict[str, Any]] = []
    for name, entry in sorted(registry.get("skills", {}).items()):
        skill_file = root / "skills" / "approved" / name / "SKILL.md"
        description = ""
        if skill_file.is_file() and not skill_file.is_symlink():
            metadata, _, _ = parse_frontmatter(skill_file.read_text(encoding="utf-8"), rules["limits"]["max_frontmatter_lines"])
            description = metadata.get("description", "")
        inventory.append({
            "name": name,
            "description": description,
            "verified": name not in unverified,
            "status": entry.get("status") if isinstance(entry, dict) else None,
            "approved_by": entry.get("approved_by") if isinstance(entry, dict) else None,
            "approved_at": entry.get("approved_at") if isinstance(entry, dict) else None,
        })
    return inventory


def print_inventory(inventory: list[dict[str, Any]]) -> None:
    for item in inventory:
        flag = "OK" if item["verified"] else "UNVERIFIED"
        print(f"{flag:10} {item['name']:28} {item['description']}")
    unverified_count = sum(1 for item in inventory if not item["verified"])
    print(f"{len(inventory)} approved skill(s); {unverified_count} unverified")


def scan_repository(root: Path, scope: str, selected: str | None, rules: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    collections: Iterable[str] = ("candidates", "approved") if scope == "all" else (scope,)
    for collection in collections:
        for skill_dir in discover_skill_dirs(root / "skills" / collection, selected):
            findings.extend(scan_skill(skill_dir, rules, root))
    if scope in {"approved", "all"}:
        findings.extend(verify_registry(root, rules, selected))
    return sorted(findings, key=lambda item: (-SEVERITY_RANK[item.severity], item.skill, item.path, item.line or 0, item.rule_id))


def is_blocking(findings: Iterable[Finding], threshold: str) -> bool:
    rank = SEVERITY_RANK[threshold]
    return any(SEVERITY_RANK[item.severity] >= rank for item in findings)


def print_text(findings: list[Finding], threshold: str) -> None:
    for item in findings:
        location = item.path + (f":{item.line}" if item.line else "")
        print(f"{item.severity.upper():8} {item.rule_id:28} {location} — {item.message}")
    counts = Counter(item.severity for item in findings)
    summary = ", ".join(f"{severity}={counts.get(severity, 0)}" for severity in ("critical", "high", "medium", "low"))
    outcome = "BLOCK" if is_blocking(findings, threshold) else "PASS"
    print(f"{outcome}: {len(findings)} finding(s); {summary}; blocking threshold={threshold}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("candidates", "approved", "all"), default="candidates")
    parser.add_argument("--skill", help="scan one kebab-case skill name")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--list", action="store_true", help="list approved, digest-verified skills for session-start selection instead of scanning")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)
        if args.list:
            inventory = list_approved_skills(args.root.resolve(), rules)
            if args.format == "json":
                print(json.dumps({"skills": inventory}, indent=2))
            else:
                print_inventory(inventory)
            return 1 if any(not item["verified"] for item in inventory) else 0
        findings = scan_repository(args.root.resolve(), args.scope, args.skill, rules)
    except ScannerError as exc:
        print(f"SCANNER ERROR: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"blocking": is_blocking(findings, rules["blocking_severity"]), "threshold": rules["blocking_severity"], "findings": [asdict(item) for item in findings]}, indent=2))
    else:
        print_text(findings, rules["blocking_severity"])
    return 1 if is_blocking(findings, rules["blocking_severity"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
