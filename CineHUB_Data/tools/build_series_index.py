#!/usr/bin/env python3
"""CineHUB Data Engine - Phase 6 series/episode indexer.

Consumes the existing VOD series index and adds stable series entities plus
season/episode metadata. It does not alter the WEB/Mobile/TV catalog paths.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "CineHUB_Data/catalog/series.index.json"
OUTPUT_SERIES = ROOT / "CineHUB_Data/catalog/series.entities.json"
OUTPUT_EPISODES = ROOT / "CineHUB_Data/catalog/episodes.index.json"
MANIFEST = ROOT / "CineHUB_Data/catalog/catalog-manifest.json"
METADATA = ROOT / "CineHUB_Data/catalog/metadata.json"

EPISODE_RE = re.compile(r"(?i)\b(?:S|T)(\d{1,3})\s*E(\d{1,4})\b")


def series_title(title: str) -> str:
    value = EPISODE_RE.sub("", title or "")
    value = re.sub(r"\s*[\[(](?:L|LEGENDADO|DUBLADO)[\])]\s*", " ", value, flags=re.I)
    return " ".join(value.split()).strip()


def series_id(title: str) -> str:
    key = f"series|{series_title(title).casefold()}".encode("utf-8")
    return "series-" + hashlib.sha256(key).hexdigest()[:20]


def main() -> None:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    items = data.get("items", [])
    entities = {}
    episodes = []

    for item in items:
        title = item.get("title", "")
        match = EPISODE_RE.search(title)
        season = int(match.group(1)) if match else None
        episode = int(match.group(2)) if match else None
        name = series_title(title)
        sid = series_id(title)

        entity = entities.setdefault(sid, {
            "id": sid,
            "title": name,
            "type": "series",
            "logo": item.get("logo") or None,
            "groups": set(),
            "seasons": set(),
            "episodeCount": 0,
        })
        if item.get("logo") and not entity["logo"]:
            entity["logo"] = item["logo"]
        if item.get("group"):
            entity["groups"].add(item["group"])
        if season is not None:
            entity["seasons"].add(season)
        if season is not None and episode is not None:
            entity["episodeCount"] += 1

        episodes.append({
            "id": f"{sid}-s{season or 0:03d}e{episode or 0:04d}-{item.get('id')}",
            "seriesId": sid,
            "seriesTitle": name,
            "season": season,
            "episode": episode,
            "title": title,
            "logo": item.get("logo"),
            "group": item.get("group"),
            "url": item.get("url"),
            "sourceFile": item.get("sourceFile"),
            "sourceItemId": item.get("id"),
        })

    series = []
    for entity in entities.values():
        entity["groups"] = sorted(entity["groups"], key=str.casefold)
        entity["seasons"] = sorted(entity["seasons"])
        entity["seasonCount"] = len(entity["seasons"])
        series.append(entity)
    series.sort(key=lambda x: x["title"].casefold())
    episodes.sort(key=lambda x: (
        x["seriesTitle"].casefold(),
        x["season"] if x["season"] is not None else 9999,
        x["episode"] if x["episode"] is not None else 9999,
        x["id"],
    ))

    generated_at = data.get("generatedAt")
    OUTPUT_SERIES.write_text(json.dumps({
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "stats": {
            "series": len(series),
            "episodes": len(episodes),
            "seasons": len({(x["seriesId"], x["season"]) for x in episodes if x["season"] is not None}),
        },
        "items": series,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    OUTPUT_EPISODES.write_text(json.dumps({
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "items": episodes,
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest.setdefault("indexes", {})["seriesEntities"] = "CineHUB_Data/catalog/series.entities.json"
    manifest["indexes"]["episodes"] = "CineHUB_Data/catalog/episodes.index.json"
    manifest["schemaVersion"] = max(2, int(manifest.get("schemaVersion", 1)))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metadata = json.loads(METADATA.read_text(encoding="utf-8")) if METADATA.exists() else {
        "schemaVersion": 1, "stats": {}
    }
    metadata.setdefault("contract", {})["seriesEntities"] = "CineHUB_Data/catalog/series.entities.json"
    metadata["contract"]["episodes"] = "CineHUB_Data/catalog/episodes.index.json"
    metadata["stats"]["seriesEntities"] = len(series)
    metadata["stats"]["episodes"] = len(episodes)
    metadata["stats"]["seasons"] = len({(x["seriesId"], x["season"]) for x in episodes if x["season"] is not None})
    metadata["schemaVersion"] = max(2, int(metadata.get("schemaVersion", 1)))
    METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "seriesEntities": len(series),
        "episodes": len(episodes),
        "seasons": len({(x["seriesId"], x["season"]) for x in episodes if x["season"] is not None}),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
