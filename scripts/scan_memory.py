#!/usr/bin/env python3
"""Dependency-free static scanner and integrity verifier for shared governed memory.

Standalone by design (mirrors scan_skills.py) so this trust boundary can be
audited independently of the skills scanner even though both share a rule set.
"""

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
DEFAULT_REGISTRY = REPO_ROOT / "registry" / "approved-memory.json"
ENTRY_NAME_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
ALLOWED_TYPES = ("user", "feedback", "project", "reference")
IGNORED_FILENAMES = {".gitkeep", "MEMORY.md"}


class ScannerError(RuntimeError):
    """Raised when scanner configuration or input cannot be trusted."""


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    entry: str
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


def parse_memory_frontmatter(text: str, max_lines: int = 80) -> tuple[dict[str, str], str | None, list[str]]:
    """Parse top-level scalar frontmatter fields plus the nested metadata.type field.

    Returns (top-level fields, metadata.type value or None, parse errors).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, None, ["memory file must start with YAML frontmatter"]

    end = 0
    for index, line in enumerate(lines[1 : max_lines + 1], start=1):
        if line.strip() == "---":
            end = index
            break
    if not end:
        return {}, None, [f"frontmatter must close within {max_lines} lines"]

    metadata: dict[str, str] = {}
    errors: list[str] = []
    memory_type: str | None = None
    in_metadata = False
    body = lines[1:end]
    i = 0
    while i < len(body):
        line = body[i]
        number = i + 2
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if in_metadata:
            if line[0].isspace():
                match = re.match(r"^[ \t]+type:\s*(.+?)\s*$", line)
                if match:
                    memory_type = _decode_scalar(match.group(1))
                i += 1
                continue
            in_metadata = False
        if line.strip() == "metadata:":
            in_metadata = True
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
    return metadata, memory_type, errors


def digest_memory_file(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ScannerError(f"memory file is missing or is a symlink: {path}")
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(
    rule_id: str,
    severity: str,
    entry: str,
    path: Path,
    message: str,
    line: int | None = None,
    root: Path = REPO_ROOT,
) -> Finding:
    return Finding(rule_id, severity, entry, _repo_display(path, root), line, message)


def scan_memory_entry(path: Path, rules: dict[str, Any], root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    entry = path.stem
    limits = rules["limits"]

    if path.is_symlink():
        return [_finding("SYMLINK_FILE", "critical", entry, path, "memory files must not be symlinks", root=root)]
    if not path.is_file():
        return [_finding("INVALID_MEMORY_PATH", "critical", entry, path, "memory entry path is not a regular file", root=root)]
    if path.suffix.lower() != ".md":
        return [_finding("OPAQUE_FILE", "critical", entry, path, "memory entries must be plain Markdown (.md); opaque types cannot be statically reviewed", root=root)]
    if not ENTRY_NAME_RE.fullmatch(entry) or len(entry) > 64:
        findings.append(_finding("INVALID_MEMORY_NAME", "high", entry, path, "filename stem must be lowercase snake_case and at most 64 characters", root=root))
    if path.name in set(rules["denied_filenames"]) or path.name.startswith(".env."):
        findings.append(_finding("DENIED_FILENAME", "critical", entry, path, "credential-like filename is forbidden", root=root))

    try:
        size = path.stat().st_size
    except OSError as exc:
        return findings + [_finding("UNREADABLE_FILE", "critical", entry, path, str(exc), root=root)]
    if size > limits["max_file_bytes"]:
        findings.append(_finding("FILE_TOO_LARGE", "high", entry, path, f"file is {size} bytes; maximum is {limits['max_file_bytes']}", root=root))

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return findings + [_finding("NON_UTF8_FILE", "critical", entry, path, f"memory file is not valid UTF-8: {exc}", root=root)]

    metadata, memory_type, fm_errors = parse_memory_frontmatter(text, limits["max_frontmatter_lines"])
    for message in fm_errors:
        findings.append(_finding("INVALID_FRONTMATTER", "high", entry, path, message, line=1, root=root))
    for required in ("name", "description"):
        if not metadata.get(required):
            findings.append(_finding("MISSING_FRONTMATTER", "high", entry, path, f"missing simple scalar frontmatter field {required!r}", line=1, root=root))
    if metadata.get("name") and not SLUG_RE.fullmatch(metadata["name"]):
        findings.append(_finding("INVALID_MEMORY_SLUG", "high", entry, path, "frontmatter name must be a kebab-case slug", line=1, root=root))
    if memory_type not in ALLOWED_TYPES:
        findings.append(_finding("INVALID_MEMORY_TYPE", "high", entry, path, f"metadata.type must be one of {ALLOWED_TYPES}, found {memory_type!r}", line=1, root=root))

    for pattern in rules["patterns"]:
        match = re.search(pattern["regex"], text, re.MULTILINE)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            findings.append(_finding(pattern["id"], pattern["severity"], entry, path, pattern["description"], line=line, root=root))

    return findings


def discover_memory_entries(base: Path, selected: str | None = None) -> list[Path]:
    if not base.exists():
        return []
    if not base.is_dir() or base.is_symlink():
        raise ScannerError(f"memory collection is not a regular directory: {base}")
    if selected:
        if not ENTRY_NAME_RE.fullmatch(selected):
            raise ScannerError(f"invalid memory entry selector: {selected!r}")
        candidate = base / f"{selected}.md"
        return [candidate] if candidate.exists() else []
    return sorted(
        path
        for path in base.iterdir()
        if path.name not in IGNORED_FILENAMES and path.suffix.lower() == ".md"
    )


def verify_registry(root: Path, rules: dict[str, Any], selected: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    registry_path = root / "registry" / "approved-memory.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [_finding("INVALID_REGISTRY", "critical", "<registry>", registry_path, str(exc), root=root)]

    if registry.get("schema_version") != 1 or not isinstance(registry.get("entries"), dict):
        return [_finding("INVALID_REGISTRY", "critical", "<registry>", registry_path, "registry must use schema_version 1 and contain an entries object", root=root)]

    approved_root = root / "memory" / "approved"
    approved_names = {path.stem for path in discover_memory_entries(approved_root, selected)}
    entries: dict[str, Any] = registry["entries"]
    registry_names = {selected} & set(entries) if selected else set(entries)

    for name in sorted(approved_names | registry_names):
        if not ENTRY_NAME_RE.fullmatch(name) or len(name) > 64:
            findings.append(_finding("INVALID_REGISTRY_NAME", "critical", name, registry_path, "registry entry name must be lowercase snake_case and at most 64 characters", root=root))
            continue
        entry_path = approved_root / f"{name}.md"
        entry = entries.get(name)
        if not entry_path.is_file():
            findings.append(_finding("REGISTRY_ORPHAN", "critical", name, registry_path, "registry entry has no approved memory file", root=root))
            continue
        if not isinstance(entry, dict):
            findings.append(_finding("UNREGISTERED_APPROVED_MEMORY", "critical", name, entry_path, "approved memory file has no registry entry", root=root))
            continue
        try:
            actual_digest = digest_memory_file(entry_path)
        except (OSError, ScannerError) as exc:
            findings.append(_finding("DIGEST_FAILURE", "critical", name, entry_path, str(exc), root=root))
            continue
        if entry.get("digest") != actual_digest:
            findings.append(_finding("DIGEST_MISMATCH", "critical", name, entry_path, f"registry has {entry.get('digest')!r}; actual digest is {actual_digest}", root=root))
        if entry.get("status") != "approved" or not entry.get("approved_by") or not entry.get("approved_at"):
            findings.append(_finding("INCOMPLETE_APPROVAL", "critical", name, registry_path, "approval metadata is incomplete", root=root))

    return findings


def list_approved_memory(root: Path, rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Inventory every approved shared-memory entry for session-start adoption.

    Each row reports whether the entry's digest verifies. A caller (human or
    agent) proposing which entries to adopt for a session must exclude any
    row with verified=False rather than silently repair or ignore it.
    """
    findings = verify_registry(root, rules)
    unverified = {item.entry for item in findings}

    registry_path = root / "registry" / "approved-memory.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScannerError(f"cannot read registry: {exc}") from exc

    inventory: list[dict[str, Any]] = []
    for name, entry in sorted(registry.get("entries", {}).items()):
        inventory.append({
            "name": name,
            "description": entry.get("description", "") if isinstance(entry, dict) else "",
            "memory_type": entry.get("memory_type") if isinstance(entry, dict) else None,
            "verified": name not in unverified,
            "status": entry.get("status") if isinstance(entry, dict) else None,
            "approved_by": entry.get("approved_by") if isinstance(entry, dict) else None,
            "approved_at": entry.get("approved_at") if isinstance(entry, dict) else None,
        })
    return inventory


def print_inventory(inventory: list[dict[str, Any]]) -> None:
    for item in inventory:
        flag = "OK" if item["verified"] else "UNVERIFIED"
        memory_type = item.get("memory_type") or "?"
        print(f"{flag:10} {item['name']:28} ({memory_type}) {item['description']}")
    unverified_count = sum(1 for item in inventory if not item["verified"])
    print(f"{len(inventory)} approved memory entr{'y' if len(inventory) == 1 else 'ies'}; {unverified_count} unverified")


def scan_repository(root: Path, scope: str, selected: str | None, rules: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    collections: Iterable[str] = ("candidates", "approved") if scope == "all" else (scope,)
    for collection in collections:
        for entry_path in discover_memory_entries(root / "memory" / collection, selected):
            findings.extend(scan_memory_entry(entry_path, rules, root))
    if scope in {"approved", "all"}:
        findings.extend(verify_registry(root, rules, selected))
    return sorted(findings, key=lambda item: (-SEVERITY_RANK[item.severity], item.entry, item.path, item.line or 0, item.rule_id))


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
    parser.add_argument("--entry", help="scan one snake_case memory entry (filename stem)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--list", action="store_true", help="list approved, digest-verified memory entries for session-start adoption instead of scanning")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)
        if args.list:
            inventory = list_approved_memory(args.root.resolve(), rules)
            if args.format == "json":
                print(json.dumps({"entries": inventory}, indent=2))
            else:
                print_inventory(inventory)
            return 1 if any(not item["verified"] for item in inventory) else 0
        findings = scan_repository(args.root.resolve(), args.scope, args.entry, rules)
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
