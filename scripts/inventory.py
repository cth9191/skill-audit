#!/usr/bin/env python3
"""Read-only skill inventory. Signals are review candidates, not verdicts."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:
    raise SystemExit("inventory.py requires PyYAML. Use a configured Python runtime with PyYAML, or inspect manually.")

SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv"}
STOP = {"the", "and", "for", "with", "that", "this", "when", "use", "skill", "user", "from", "into", "your", "requests", "a", "to", "of", "or", "in"}
SIGNALS = {
    "approval language; inspect whether justified": r"\b(?:wait for|ask for|require|obtain)\b.{0,65}\b(?:approval|confirmation|permission)\b",
    "fixed procedure language; inspect necessity": r"\b(?:always|never|must|exactly|mandatory)\b",
    "broad trigger language; inspect scope": r"\b(?:any task|every task|whenever|always use|any question|any request)\b",
}


def identity(path):
    return os.path.normcase(str(Path(path).resolve()))


def linked(path):
    # Windows junctions are reparse points even on Python <3.12, which has no
    # Path.is_junction(). lstat inspects the link itself without following it.
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def discover(roots, catalog, errors):
    found = {}
    def should_skip(path):
        try:
            return linked(path)
        except OSError as exc:
            errors.append({"path": str(path), "error": str(exc)})
            return True
    def add(path, source):
        try:
            key = identity(path)
            found.setdefault(key, {"path": Path(path).resolve(), "sources": []})["sources"].append(source)
        except OSError as exc:
            errors.append({"path": str(path), "error": str(exc)})
    for value in catalog:
        add(value, "session catalog")
    for raw in roots:
        root = Path(raw).expanduser().absolute()
        if not root.exists():
            errors.append({"path": str(root), "error": "root not found"})
            continue
        if should_skip(root):
            errors.append({"path": str(root), "error": "linked root skipped; explicitly supply its resolved target"})
            continue
        if root.is_file():
            if root.name.lower() == "skill.md":
                add(root, str(root))
            else:
                errors.append({"path": str(root), "error": "root file is not SKILL.md"})
            continue
        def onerror(exc):
            errors.append({"path": str(exc.filename), "error": str(exc)})
        for folder, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
            dirs[:] = sorted(d for d in dirs if d not in SKIP and not should_skip(Path(folder) / d))
            for name in files:
                path = Path(folder) / name
                if name.lower() == "skill.md" and not should_skip(path):
                    add(path, str(root))
    return [found[k] for k in sorted(found)]


def parse_skill(path):
    raw_bytes = path.read_bytes()
    if len(raw_bytes) > 2_000_000:
        raise ValueError("SKILL.md exceeds the 2 MB inspection limit")
    raw = raw_bytes.decode("utf-8-sig")
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("unclosed YAML frontmatter")
    meta = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(meta, dict) or not all(isinstance(meta.get(k), str) and meta[k].strip() for k in ("name", "description")):
        raise ValueError("frontmatter requires nonempty name and description strings")
    signals = []
    for index, line in enumerate(lines, 1):
        for label, pattern in SIGNALS.items():
            if re.search(pattern, line, re.I):
                signals.append({"kind": label, "line": index, "excerpt": line[:300]})
    refs = []
    # Only prose Markdown links. Fenced examples are not dependencies. Dynamic
    # paths and conventional URL placeholders are unresolved, not declared broken.
    fence = None
    for index, line in enumerate(lines, 1):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            token, tail = marker.groups()
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not tail.strip():
                fence = None
            continue
        if fence:
            continue
        for match in re.finditer(r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", line):
            target = match.group(1).strip("<>")
            if not target or target.startswith("#") or urlsplit(target).scheme or target.startswith("//"):
                continue
            bare = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not bare:
                continue
            if bare.lower() in {"url", "link", "your-url"}:
                status = "placeholder; resolve manually"
                resolved = bare
            elif any(x in bare for x in ("$", "{", "}", "*", "~")):
                status = "dynamic; resolve manually"
                resolved = bare
            else:
                dest = (path.parent / bare).resolve()
                status = "present" if dest.exists() else "missing"
                resolved = str(dest)
            refs.append({"line": index, "target": target, "resolved": resolved, "status": status})
    body = "\n".join(lines[end + 1:]).strip()
    return {"name": meta["name"], "description": meta["description"], "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "body_sha256": hashlib.sha256(body.encode()).hexdigest(), "line_count": len(lines),
            "signals": signals, "references": refs}


def read_usage(path, known_paths):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("coverage"), str) or not data["coverage"].strip() or not isinstance(data.get("events"), list):
        raise ValueError("usage requires nonempty coverage and an events array")
    counts = defaultdict(int)
    rejected, seen = [], set()
    for event in data["events"]:
        try:
            if not isinstance(event, dict) or not all(isinstance(event.get(k), str) and event[k].strip() for k in ("skill_path", "timestamp", "evidence")):
                raise ValueError("event needs skill_path, timestamp and evidence")
            stamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timestamp needs a timezone")
            candidate = Path(event["skill_path"]).expanduser()
            key = identity(candidate if candidate.is_absolute() else path.parent / candidate)
            if key not in known_paths:
                raise ValueError("event path is outside the scanned skill inventory")
            event_key = (key, stamp.isoformat(), event["evidence"])
            if event_key not in seen:
                seen.add(event_key)
                counts[key] += 1
        except (ValueError, TypeError) as exc:
            rejected.append({"event": event, "error": str(exc)})
    return {"coverage": data["coverage"], "source": str(path.resolve()), "rejected_events": rejected,
            "note": "Imported invocation evidence; authenticity and coverage not independently verified"}, counts


def build_inventory(roots, catalog=None, usage_path=None):
    errors = []
    entries = discover(roots, catalog or [], errors)
    skills = []
    for entry in entries:
        item = {"path": str(entry["path"]), "discovered_from": sorted(set(entry["sources"])),
                "activation_status": "advertised in session" if "session catalog" in entry["sources"] else "not established by filesystem scan",
                "usage": {"observed_invocations": None, "status": "unknown"}}
        try:
            item.update(parse_skill(entry["path"]))
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            item["inspection_error"] = str(exc)
            errors.append({"path": item["path"], "error": str(exc)})
        skills.append(item)
    coverage = {"coverage": "unavailable", "note": "No usage evidence supplied"}
    if usage_path:
        coverage, counts = read_usage(Path(usage_path), {identity(s["path"]) for s in skills})
        for skill in skills:
            count = counts.get(identity(skill["path"]), 0)
            skill["usage"] = {"observed_invocations": count, "status": "observed" if count else "not observed in supplied evidence"}
    groups = defaultdict(list)
    for skill in skills:
        if skill.get("sha256"):
            groups[skill["sha256"]].append(skill["path"])
    duplicate_groups = [paths for paths in groups.values() if len(paths) > 1]
    candidates = []
    valid = [s for s in skills if "name" in s]
    for i, left in enumerate(valid):
        a = set(re.findall(r"[a-z0-9]+", (left["name"] + " " + left["description"]).lower())) - STOP
        for right in valid[i + 1:]:
            if left["sha256"] == right["sha256"]:
                continue
            b = set(re.findall(r"[a-z0-9]+", (right["name"] + " " + right["description"]).lower())) - STOP
            score = len(a & b) / len(a | b) if a | b else 0
            if left["name"] == right["name"] or score >= .45:
                candidates.append({"paths": [left["path"], right["path"]], "lexical_similarity": round(score, 3),
                                   "same_name": left["name"] == right["name"], "status": "inspect meaning and runtime before consolidating"})
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "roots": [str(Path(r).expanduser().absolute()) for r in roots],
            "skill_count": len(skills), "skills": skills, "exact_duplicate_groups": duplicate_groups,
            "overlap_candidates": sorted(candidates, key=lambda x: x["lexical_similarity"], reverse=True),
            "usage_coverage": coverage, "errors": errors,
            "limitations": ["Filesystem discovery does not establish runtime precedence or enabled status.",
                            "Lexical and instruction signals require human or agent review; no skill was executed.",
                            "Symlink and junction directories are skipped; Markdown-reference detection is conservative."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", default=[])
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--include-plugins", action="store_true")
    parser.add_argument("--usage", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8-sig")) if args.catalog else []
    if not isinstance(catalog, list) or not all(isinstance(p, str) for p in catalog):
        parser.error("catalog must be an array of SKILL.md path strings")
    codex_root = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    roots = args.root or ([] if args.catalog else [str(codex_root / "skills"), str(Path.home() / ".agents" / "skills")])
    if args.include_plugins:
        roots.append(str(codex_root / "plugins" / "cache"))
    # Guard against overwriting an inspected input with the output.
    out = args.out.resolve()
    if out.name.lower() == "skill.md" or any(out == Path(p).expanduser().resolve() for p in catalog) or (args.usage and out == args.usage.resolve()) or (args.catalog and out == args.catalog.resolve()):
        parser.error("output must not overwrite an input")
    for root in roots:
        resolved = Path(root).expanduser().resolve()
        if out == resolved or (resolved.is_dir() and out.is_relative_to(resolved)):
            parser.error("output must be outside scanned roots")
    for source in catalog:
        if out.is_relative_to(Path(source).expanduser().resolve().parent):
            parser.error("output must be outside catalog skill directories")
    result = build_inventory(roots, catalog, args.usage)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"skills": result["skill_count"], "errors": len(result["errors"]), "output": str(out)}))


if __name__ == "__main__":
    main()
