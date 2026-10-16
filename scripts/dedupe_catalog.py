#!/usr/bin/env python3
"""Show one entry per game, console and category; keep the highest listed version.

Different forks are not necessarily comparable release lines. Alternatives are
preserved in metadata, but only one game card is displayed.
"""
from __future__ import annotations
import json
import re
import sys
import unicodedata
from pathlib import Path


def clean_title(title: str) -> str:
    name = unicodedata.normalize("NFKD", str(title or "")).casefold()
    name = "".join(c for c in name if not unicodedata.combining(c))
    # Remove leading availability badges (🟢, 🔴, 🟠) and whitespace.
    name = re.sub(r"^[^\w\d]+", "", name, flags=re.UNICODE)
    return " ".join(re.findall(r"[a-z0-9]+", name))


def sanitized_title(title: str) -> str:
    return re.sub(r"^[^\w\d]+", "", str(title or "")).strip()


def version_rank(version):
    value = str(version or "").strip().lower()
    m = re.search(r"(?<!\d)(\d+(?:\.\d+){0,6})", value)
    if not m:
        return (0, (0,) * 7, 0)
    parts = [int(p) for p in m.group(1).split(".")]
    parts = tuple((parts + [0] * 7)[:7])
    # A stable release of a version outranks alpha/beta/RC/test of the same version.
    stable = 0 if re.search(r"\b(?:alpha|beta|rc|test|preview|pre-release|prerelease|dev|nightly)\b", value) else 1
    return (1, parts, stable)


def plausible_port(item):
    """Guard against obvious source-list copy/paste errors such as DKC3 -> DKC2."""
    name = sanitized_title(item.get("title", ""))
    match = re.search(r"\bDonkey Kong Country\s+([123])\b", name, flags=re.I)
    if match:
        repo = str(item.get("url", "")).lower()
        project = re.search(r"/dkc([123])recomp", repo)
        if project and project.group(1) != match.group(1):
            return False
    return True


def pick_key(item):
    normalized = clean_title(item.get("title", ""))
    return (str(item.get("type", "")).strip().casefold(),
            str(item.get("platform", "")).strip().casefold(),
            normalized)


def score(item):
    version = version_rank(item.get("version"))
    date = str(item.get("updated", "") or "")
    # Use the listed release version as the primary criterion; date breaks ties.
    return (int(plausible_port(item)), *version, date, int(bool(item.get("cover"))))


def deduplicate(items):
    groups = {}
    removed_invalid = 0
    for record in items:
        if not isinstance(record, dict) or not record.get("id"):
            removed_invalid += 1
            continue
        key = pick_key(record)
        if not key[2]:
            removed_invalid += 1
            continue
        groups.setdefault(key, []).append(record)
    deduped = []
    removed = 0
    for group in groups.values():
        # Keep first item as deterministic tie break, in case versions/dates match.
        winner = max(group, key=score)
        merged = dict(winner)
        # Transfer artwork if only an alternate entry had one.
        if not merged.get("cover"):
            illustrated = next((x for x in group if x.get("cover")), None)
            if illustrated:
                merged["cover"] = illustrated["cover"]
                if illustrated.get("cover_source"):
                    merged["cover_source"] = illustrated["cover_source"]
        alternatives = list(winner.get("alternatives") or [])
        for item in group:
            if item is winner:
                continue
            if item.get("url") or item.get("download"):
                alternatives.append({k: item.get(k) for k in
                                     ("title", "version", "url", "download", "source", "updated")
                                     if item.get(k)})
        seen = set()
        unique = []
        for alt in alternatives:
            if not isinstance(alt, dict):
                continue
            url = str(alt.get("url") or alt.get("download") or "").rstrip("/")
            if not url or url == str(merged.get("url") or merged.get("download") or "").rstrip("/") or url in seen:
                continue
            seen.add(url)
            unique.append(alt)
        if unique:
            merged["alternatives"] = unique[:30]
        else:
            merged.pop("alternatives", None)
        deduped.append(merged)
        removed += len(group) - 1
    return deduped, {"duplicate_records_removed": removed,
                     "invalid_records_removed": removed_invalid,
                     "unique_records": len(deduped)}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "data/catalog.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["items"], stats = deduplicate(payload.get("items", []))
    payload.setdefault("meta", {}).update(stats)
    payload["meta"]["covers_resolved"] = sum(1 for item in payload["items"] if item.get("cover"))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
