#!/usr/bin/env python3
"""CineHUB Data Engine - Phase 4 normalizer and deduplicator.

Builds a canonical channel index without changing the application-facing lists.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "CineHUB_Data/sources/registry.json"
OUTPUT_DIR = ROOT / "CineHUB_Data/normalized"
OUTPUT_PATH = OUTPUT_DIR / "channels.json"
TIMEOUT = 25
MAX_BYTES = 25 * 1024 * 1024

QUALITY_RE = re.compile(r"(?i)(?:\\s*[-|/]?\\s*)?(?:\\[?\\s*(?:sd|hd|fhd|full\\s*hd|uhd|4k|8k|720p|1080p|1440p|2160p)\\s*\\]?)(?:\\s*)$")
BRACKET_QUALITY_RE = re.compile(r"(?i)\\s*[\\[(](?:sd|hd|fhd|full\\s*hd|uhd|4k|8k|720p|1080p|1440p|2160p)[\\])]\\s*$")
PUNCT_RE = re.compile(r"[^a-z0-9]+")
ATTR_RE = re.compile(r'([\\w-]+)="([^"]*)"')


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))


def clean_text(value: str) -> str:
    value = strip_accents(value or "").strip()
    value = re.sub(r"\\s+", " ", value)
    return value


def canonical_name(value: str) -> str:
    value = clean_text(value)
    previous = None
    while previous != value:
        previous = value
        value = QUALITY_RE.sub("", value).strip()
        value = BRACKET_QUALITY_RE.sub("", value).strip()
    value = re.sub(r"(?i)\\s+(?:HD|FHD|UHD|SD)$", "", value).strip()
    value = re.sub(r"\\s*[-|/]\\s*$", "", value).strip()
    return value or "Unknown Channel"


def identity_key(name: str, country: str = "", language: str = "") -> str:
    base = " ".join(
        x for x in [canonical_name(name).lower(), clean_text(country).lower(), clean_text(language).lower()]
        if x
    )
    return base


def stable_id(key: str) -> str:
    return "channel-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def parse_extinf(line: str) -> tuple[dict, str]:
    meta = dict(ATTR_RE.findall(line))
    title = line.split(",", 1)[1].strip() if "," in line else meta.get("tvg-name", "")
    return meta, title


def parse_m3u(text: str) -> list[dict]:
    lines = [x.strip() for x in text.replace("\\r", "").split("\\n") if x.strip()]
    records = []
    pending = None
    for line in lines:
        if line.startswith("#EXTINF"):
            pending = parse_extinf(line)
        elif pending and not line.startswith("#"):
            meta, title = pending
            records.append({
                "name": meta.get("tvg-name") or title,
                "title": title,
                "tvg_id": meta.get("tvg-id") or meta.get("tvgid") or "",
                "logo": meta.get("tvg-logo") or "",
                "group": meta.get("group-title") or meta.get("group") or "",
                "country": meta.get("tvg-country") or meta.get("country") or "",
                "language": meta.get("tvg-language") or meta.get("language") or "",
                "url": line,
            })
            pending = None
    return records


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "CineHUB-Data-Engine/4.0", "Accept": "*/*"})
    with urlopen(req, timeout=TIMEOUT) as response:
        chunks, total = [], 0
        while True:
            chunk = response.read(min(1024 * 1024, MAX_BYTES - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_BYTES:
                raise ValueError("source exceeds configured maximum size")
            chunks.append(chunk)
    return b"".join(chunks)


def source_records(source: dict) -> list[dict]:
    if source.get("transport") == "local":
        path = ROOT / source["path"]
        if not path.exists():
            return []
        body = path.read_bytes()
    else:
        body = fetch(source["url"])
    return parse_m3u(body.decode("utf-8", errors="replace"))


def normalize() -> int:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    previous = {}
    if OUTPUT_PATH.exists():
        try:
            previous = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
    entities: dict[str, dict] = {}
    stats = {"sourcesRead": 0, "recordsRead": 0, "entities": 0, "duplicatesMerged": 0, "failedSources": 0}

    all_sources = [*registry.get("sources", []), *registry.get("localSources", [])]
    channel_sources = [s for s in all_sources if s.get("enabled") and s.get("scope") == "channels"]
    source_ids = {s.get("id") for s in channel_sources}

    # Start from the previous normalized index, but remove entries belonging to
    # sources we are going to refresh. Failed sources are restored below.
    for old in previous.get("channels", []):
        kept = [x for x in old.get("sources", []) if x.get("sourceId") not in source_ids]
        if kept:
            old = dict(old)
            old["sources"] = kept
            entities[old["id"]] = old

    successful_source_ids = set()
    failed_source_ids = set()
    for source in channel_sources:
        try:
            records = source_records(source)
        except Exception as exc:
            failed_source_ids.add(source.get("id"))
            stats["failedSources"] += 1
            print(f"WARNING: {source.get('id')}: {exc}")
            continue
        successful_source_ids.add(source.get("id"))
        stats["sourcesRead"] += 1
        stats["recordsRead"] += len(records)
        stats["sourcesRead"] += 1
        stats["recordsRead"] += len(records)

        for item in records:
            name = clean_text(item.get("name") or item.get("title") or "")
            if not name:
                continue
            country = clean_text(item.get("country", ""))
            language = clean_text(item.get("language", ""))
            key = identity_key(name, country, language)
            entity_id = stable_id(key)
            if entity_id not in entities:
                entities[entity_id] = {
                    "id": entity_id,
                    "name": canonical_name(name),
                    "aliases": [],
                    "country": country or None,
                    "language": language or None,
                    "group": clean_text(item.get("group", "")) or None,
                    "sources": [],
                }
            entity = entities[entity_id]
            if name != entity["name"] and name not in entity["aliases"]:
                entity["aliases"].append(name)

            source_entry = {
                "sourceId": source.get("id"),
                "url": item.get("url"),
                "tvgId": item.get("tvg_id") or None,
                "logo": item.get("logo") or None,
                "group": clean_text(item.get("group", "")) or None,
                "quality": detect_quality(name),
                "priority": source.get("priority"),
            }
            source_key = (source_entry["sourceId"], source_entry["url"])
            if not any((x.get("sourceId"), x.get("url")) == source_key for x in entity["sources"]):
                entity["sources"].append(source_entry)
            else:
                stats["duplicatesMerged"] += 1

    # Restore the last known records from failed sources. This prevents a
    # temporary outage from deleting healthy historical entities from the index.
    if failed_source_ids:
        for old in previous.get("channels", []):
            for old_source in old.get("sources", []):
                if old_source.get("sourceId") not in failed_source_ids:
                    continue
                entity_id = old.get("id")
                if not entity_id:
                    continue
                if entity_id not in entities:
                    entities[entity_id] = {**old, "sources": []}
                if not any(
                    x.get("sourceId") == old_source.get("sourceId") and x.get("url") == old_source.get("url")
                    for x in entities[entity_id]["sources"]
                ):
                    entities[entity_id]["sources"].append(old_source)

    # Drop entities that no longer have any source after a successful refresh.
    entities = {k: v for k, v in entities.items() if v.get("sources")}
    for entity in entities.values():
        entity["aliases"] = sorted(set(entity.get("aliases", [])))
        entity["sources"].sort(key=lambda x: (x.get("priority") is None, x.get("priority") or 9999, x.get("sourceId") or ""))
    output = {
        "schemaVersion": "1.0.0",
        "generatedBy": "CineHUB Data Engine Phase 4",
        "stats": {**stats, "entities": len(entities)},
        "channels": sorted(entities.values(), key=lambda x: (x["name"].lower(), x["id"])),
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(output["stats"], ensure_ascii=False, indent=2))
    return 0


def detect_quality(name: str) -> str | None:
    value = clean_text(name).lower()
    if "2160p" in value or "4k" in value or "uhd" in value:
        return "2160p"
    if "1440p" in value:
        return "1440p"
    if "1080p" in value or "fhd" in value or "full hd" in value:
        return "1080p"
    if "720p" in value or re.search(r"\\bhd\\b", value):
        return "720p"
    if re.search(r"\\bsd\\b", value):
        return "sd"
    return None


if __name__ == "__main__":
    raise SystemExit(normalize())
