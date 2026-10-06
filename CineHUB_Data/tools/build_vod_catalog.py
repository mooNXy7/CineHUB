#!/usr/bin/env python3
"""Build compact, platform-neutral VOD catalog indexes from the existing CineHUB catalog.

This phase is intentionally additive: existing WEB/Mobile/TV catalog files are
not replaced. The Data Engine reads the existing M3U/M3U8 catalog and produces
small, deterministic indexes/manifests for future consumers.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
import subprocess
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "CineHUB_WEB" / "dados" / "conteudo" / "catalogo"
OUT_DIR = ROOT / "CineHUB_Data" / "catalog"
MAX_NAME = 300

EXTINF_RE = re.compile(r'^#EXTINF:[^ ]*(?: [^,]*)?,(.*)$')
ATTR_RE = re.compile(r'([A-Za-z0-9_-]+)="([^"]*)"')


def clean(value: str) -> str:
    return " ".join((value or "").strip().split())[:MAX_NAME]


def parse_extinf(line: str) -> tuple[str, dict[str, str]]:
    match = EXTINF_RE.match(line.strip())
    if not match:
        return "", {}
    attrs = dict(ATTR_RE.findall(line))
    return clean(match.group(1)), attrs


def stable_id(name: str, url: str, kind: str) -> str:
    # URL is included so two legitimate providers with the same title do not
    # collapse into one record. This is a catalog-item ID, not a source ID.
    import hashlib
    key = f"{kind}|{name.casefold()}|{url.strip()}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()[:20]


def infer_kind(group: str, filename: str) -> str:
    text = f"{group} {filename}".casefold()
    return "series" if "série" in text or "series" in text else "movie"


def source_revision() -> str:
    try:
        value = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI", "--", "CineHUB_WEB/dados/conteudo/catalogo"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        ).strip()
        if value:
            return value
    except (OSError, subprocess.CalledProcessError):
        pass
    return "unknown"


def scan() -> tuple[list[dict], dict]:
    items: list[dict] = []
    files = sorted(SOURCE_DIR.glob("*.m3u*"))
    groups = Counter()
    kinds = Counter()
    files_ok = 0
    malformed = 0

    for path in files:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as fh:
                pending = None
                for raw in fh:
                    line = raw.strip()
                    if not line:
                        continue
                    if line.startswith("#EXTINF:"):
                        pending = line
                        continue
                    if line.startswith("#"):
                        continue
                    if pending is None or not re.match(r"^https?://", line, re.I):
                        malformed += 1
                        pending = None
                        continue

                    name, attrs = parse_extinf(pending)
                    group = clean(attrs.get("group-title", ""))
                    logo = attrs.get("tvg-logo", "").strip()
                    kind = infer_kind(group, path.name)
                    item = {
                        "id": stable_id(name, line, kind),
                        "title": name,
                        "type": kind,
                        "group": group,
                        "logo": logo,
                        "url": line,
                        "sourceFile": str(path.relative_to(ROOT)).replace("\\", "/"),
                    }
                    items.append(item)
                    groups[group or "Sem categoria"] += 1
                    kinds[kind] += 1
                    pending = None
            files_ok += 1
        except OSError:
            malformed += 1

    # Deterministic order makes GitHub Actions produce no noisy diffs.
    items.sort(key=lambda x: (x["type"], x["title"].casefold(), x["id"]))
    stats = {
        "generatedAt": source_revision(),
        "sourceFiles": len(files),
        "sourceFilesRead": files_ok,
        "items": len(items),
        "movies": kinds.get("movie", 0),
        "series": kinds.get("series", 0),
        "groups": len(groups),
        "malformedRecords": malformed,
    }
    return items, stats


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=False),
        encoding="utf-8",
    )


def main() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Catalog source directory not found: {SOURCE_DIR}")

    items, stats = scan()
    movies = [x for x in items if x["type"] == "movie"]
    series = [x for x in items if x["type"] == "series"]

    # The full item indexes are intentionally kept separate by type.
    write_json(OUT_DIR / "movies.index.json", {
        "schemaVersion": 1,
        "generatedAt": stats["generatedAt"],
        "items": movies,
    })
    write_json(OUT_DIR / "series.index.json", {
        "schemaVersion": 1,
        "generatedAt": stats["generatedAt"],
        "items": series,
    })

    # Lightweight home-facing indexes. They contain references, not full records.
    def top(groups: list[str], limit: int = 50):
        wanted = {g.casefold() for g in groups}
        return [
            {"id": x["id"], "title": x["title"], "type": x["type"], "logo": x["logo"], "group": x["group"]}
            for x in items
            if x["group"].casefold() in wanted
        ][:limit]

    featured = [
        {"id": x["id"], "title": x["title"], "type": x["type"], "logo": x["logo"], "group": x["group"]}
        for x in items
        if "destaque" in x["group"].casefold() or "lançamento" in x["group"].casefold()
    ][:100]

    releases = [
        {"id": x["id"], "title": x["title"], "type": x["type"], "logo": x["logo"], "group": x["group"]}
        for x in items
        if "lançamento" in x["group"].casefold() or "lancamento" in x["group"].casefold()
    ][:100]

    trending = featured[:50] if featured else movies[:50]

    write_json(OUT_DIR / "featured.json", {
        "schemaVersion": 1, "generatedAt": stats["generatedAt"], "items": featured
    })
    write_json(OUT_DIR / "releases.json", {
        "schemaVersion": 1, "generatedAt": stats["generatedAt"], "items": releases
    })
    write_json(OUT_DIR / "trending.json", {
        "schemaVersion": 1, "generatedAt": stats["generatedAt"], "items": trending
    })

    metadata = {
        "schemaVersion": 1,
        "generatedAt": stats["generatedAt"],
        "source": "CineHUB_WEB/dados/conteudo/catalogo",
        "stats": stats,
        "contract": {
            "movies": "CineHUB_Data/catalog/movies.index.json",
            "series": "CineHUB_Data/catalog/series.index.json",
            "featured": "CineHUB_Data/catalog/featured.json",
            "trending": "CineHUB_Data/catalog/trending.json",
            "releases": "CineHUB_Data/catalog/releases.json",
        },
    }
    write_json(OUT_DIR / "metadata.json", metadata)

    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
