#!/usr/bin/env python3
"""Summarize port README requirements, without guessing ROMs or editions."""
from __future__ import annotations
import concurrent.futures
import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "data/catalog.json"
OUT = ROOT / "data/port_guides.json"
OVERRIDES = ROOT / "data/port_overrides.json"
NOW = datetime.datetime.now(datetime.timezone.utc)
WORKERS = 12

def repo_url(value):
    u = urllib.parse.urlsplit(str(value or "").strip())
    if u.netloc.lower() not in ("github.com", "www.github.com"):
        return ""
    parts = u.path.strip("/").split("/")
    if len(parts) < 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", x) for x in parts[:2]):
        return ""
    return "https://github.com/" + parts[0] + "/" + parts[1]

def compact(raw, cap):
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", raw)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<(?:br|/p|/li|/tr|/div)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"(?m)^\s*[>#*+-]+\s*", "", text)
    text = re.sub(r"[*_]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= cap:
        return text
    cut = max(text[:cap].rfind(". "), text[:cap].rfind("\n"))
    return text[:cut].strip() if cut > cap * 0.5 else text[:cap].rstrip() + "…"

def summary(readme):
    sections = []
    heading = "INTRO"
    body = []
    code = False
    for line in readme.splitlines():
        if line.lstrip().startswith(("~~~", chr(96) * 3)):
            code = not code
            continue
        if code:
            continue
        m = re.match(r"^\s*#{1,4}\s+(.+?)(?:\s+#+)?\s*$", line)
        if m:
            sections.append((heading, "\n".join(body)))
            heading, body = m.group(1), []
        else:
            body.append(line)
    sections.append((heading, "\n".join(body)))
    def section(pattern, cap):
        for title, content in sections:
            if re.search(pattern, title, re.I):
                cleaned = compact(content, cap)
                if cleaned:
                    return cleaned
        return ""
    intro = compact(sections[0][1], 160)
    if not intro:
        intro = next((compact(raw, 160) for name, raw in sections[1:] if
                      re.search(r"^(overview|about|introduction|description)$", name, re.I)), "")
    req = section(r"what you need|requirements|prerequisites|game files|game data|assets|original game", 460)
    install = section(r"how to install|installation|^install|quick start|getting started|^setup|how to play|^usage|how to run|instrucciones", 650)
    edition = section(r"supported editions|supported versions|compatible rom|supported rom|^rom|version requirements|game version|^region|compatibility", 400)
    if not edition:
        edition = section(r"^faq", 300) if re.search(r"(?i)(specific rom|us version)", readme) else ""
    return {"overview": intro, "requirements": req, "installation": install,
            "editions": edition, **overclock_info(readme)}


def overclock_info(readme):
    """Distinguish confirmed overclock requirements from mere mentions."""
    lines = []
    inside = False
    for line in readme.splitlines():
        if line.strip().startswith(("~~~", chr(96)*3)):
            inside = not inside
            continue
        if not inside: lines.append(line)
    whole = "\n".join(lines)
    pat = re.compile(r"over[\s-]?clock|under[\s-]?clock|\bsys[- ]?clk\b|\b(?:stock|default|custom|higher)\s+(?:cpu\s+|gpu\s+)?clocks?\b|\b(?:cpu|gpu|memory)\s+clock\b", re.I)
    hits = [(i,line) for i,line in enumerate(lines) if pat.search(line)]
    if not hits:
        return {"overclock_status":"not_documented", "overclock_notes":"", "overclock_source":""}
    headings = [(i,re.sub(r"^\s*#{1,6}\s*","",row).strip()) for i,row in enumerate(lines) if re.match(r"^\s*#{1,6}\s+",row)]
    selected = ""
    for index,heading in headings:
        if re.search(r"over[\s-]?clock|clocks?\s+and\s+performance",heading,re.I):
            stop=next((i for i,h in headings if i>index),len(lines))
            selected="\n".join(lines[index+1:stop]).strip()
            break
    if not selected:
        selected="\n".join(" ".join(lines[max(0,i-1):min(len(lines),i+2)]).strip() for i,_ in hits[:5])
    sanitized = re.sub(r"[*_]+","",selected).replace(chr(96),"")
    context=(sanitized+"\n"+whole[:1500]).lower()
    status="mentioned"
    if re.search(r"(?:without|with\s+no|no(?:\s+need\s+for)?|does\s+not\s+require)\s+(?:an?\s+)?over[\s-]?clock|over[\s-]?clock(?:ing)?\s+(?:is\s+)?(?:not\s+required|not\s+needed|unnecessary)",context):
        status="not_required"
    elif re.search(r"over[\s-]?clock(?:ing)?\s+(?:is\s+)?(?:required|mandatory|needed|necessary)|(?:must|need\s+to|requires?)\s+over[\s-]?clock",context):
        status="required"
    elif re.search(r"over[\s-]?clock(?:ing)?\s+(?:is\s+)?(?:recommended|advised)|recommend(?:ed)?\s+(?:an?\s+)?over[\s-]?clock",context):
        status="recommended"
    elif re.search(r"(?:optional|experimental?)\s+(?:cpu\s+|gpu\s+)?(?:over[\s-]?clock|clocks?)|(?:can|may|could)\s+(?:raise|increase|boost)\s+(?:the\s+)?(?:cpu|gpu|clock)|for\s+(?:higher|better|more)\s+(?:fps|performance)[^\n.]{0,90}over[\s-]?clock",context):
        status="optional"
    return {"overclock_status":status, "overclock_notes":compact(selected,690), "overclock_source":""}

def source_readme(repo):
    url = urllib.parse.urlsplit(repo)
    owner, name = url.path.strip("/").split("/")[:2]
    # Most repositories use main or master, but documentation can vary.
    for branch in ("main", "master", "develop", "switch_pr"):
        for namepart in ("README.md", "readme.md", "Readme.md", "README.MD", "README", "README.txt", "INSTALL", "README_original.md", "docs/Readme.md"):
            path = "https://raw.githubusercontent.com/" + urllib.parse.quote(owner) + "/" + urllib.parse.quote(name) + "/" + branch + "/" + namepart
            req = urllib.request.Request(path, headers={"User-Agent": "NXFlow-README-metadata/1.0", "Accept": "text/plain"})
            try:
                with urllib.request.urlopen(req, timeout=18) as reply:
                    data = reply.read(180001)
                    if len(data) > 180000:
                        return None, None, "README too large"
                    return data.decode("utf-8", "replace"), repo + "/blob/" + branch + "/" + namepart, ""
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                return None, None, "HTTP " + str(e.code)
            except (OSError, TimeoutError):
                return None, None, "connection unavailable"
    return None, None, "README not available at repository root"

def lookup(repo):
    try:
        raw, link, error = source_readme(repo)
        if raw is None:
            return repo, {"status": "review_needed", "readme_url": repo,
                          "reason": error, "overview": "", "requirements": "",
                          "installation": "", "editions": ""}
        parts = summary(raw)
        return repo, {"status": "readme_verified", "readme_url": link,
                      "reason": "", **parts}
    except Exception as ex:
        return repo, {"status": "review_needed", "readme_url": repo,
                      "reason": type(ex).__name__, "overview": "",
                      "requirements": "", "installation": "", "editions": ""}

def main():
    doc = json.loads(CAT.read_text(encoding="utf-8"))
    ports = [x for x in doc.get("items", []) if x.get("type") == "Port"]
    repos = sorted({repo_url(x.get("url")) for x in ports if repo_url(x.get("url"))})
    try:
        old = json.loads(OUT.read_text(encoding="utf-8")).get("by_repo", {})
    except (OSError, ValueError):
        old = {}
    try:
        overrides = json.loads(OVERRIDES.read_text(encoding="utf-8")).get("by_repo", {})
    except (OSError, ValueError):
        overrides = {}
    overrides = {repo_url(k): v for k, v in overrides.items() if repo_url(k)}
    results = {}
    todo = []
    for repo in repos:
        previous = old.get(repo, {})
        try:
            checked = datetime.datetime.fromisoformat(previous.get("checked_at", ""))
            fresh = (NOW - checked).days < 14 and previous.get("status") == "readme_verified" and "overclock_status" in previous
        except (ValueError, TypeError):
            fresh = False
        if fresh:
            results[repo] = previous
        else:
            todo.append(repo)
    print("Ports:", len(ports), "unique GitHub repositories:", len(repos), "fetching:", len(todo), flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        tasks = {pool.submit(lookup, repo): repo for repo in todo}
        for future in concurrent.futures.as_completed(tasks):
            repo = tasks[future]
            try:
                _, result = future.result()
            except Exception as ex:
                result = {"status": "review_needed", "reason": type(ex).__name__, "readme_url": repo}
            result["checked_at"] = NOW.isoformat(timespec="seconds")
            results[repo] = result
    for repo, source in overrides.items():
        if repo not in results:
            continue
        entry = results[repo]
        for field in ("title", "game_year", "original_platform", "original_files",
                      "game_edition", "installation", "install_url",
                      "source_readme", "verification", "rom_format",
                      "release_url", "release_tag", "overclock_status",
                      "overclock_notes", "overclock_source"):
            if source.get(field):
                entry[field] = source[field]
        if source.get("original_files"):
            entry["requirements"] = source["original_files"]
        if source.get("game_edition"):
            entry["editions"] = source["game_edition"]
        if source.get("source_readme"):
            entry["readme_url"] = source["source_readme"]
        if source.get("verification") and entry.get("status") == "review_needed":
            entry["status"] = "manual_verified"
    status = {}
    for value in results.values():
        status[value.get("status", "review_needed")] = status.get(value.get("status", "review_needed"), 0) + 1
    result = {"meta": {"generated_at": NOW.isoformat(timespec="seconds"),
                       "port_count": len(ports), "repositories": len(repos),
                       "statuses": status,
                       "note": "Overclock details come from the authors; mentions are not evidence it is necessary.",
                       "overclock_statuses": {key: sum(1 for entry in results.values() if entry.get("overclock_status", "not_documented")==key) for key in ("required","recommended","optional","not_required","mentioned","not_documented")}},
              "by_repo": {repo: results[repo] for repo in repos}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified / pending:", status, flush=True)

if __name__ == "__main__":
    main()
