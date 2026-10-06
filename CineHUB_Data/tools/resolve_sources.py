#!/usr/bin/env python3
"""CineHUB Data Engine - Phase 5 multi-source resolver.

Builds a deterministic, bounded fallback order for each normalized entity.
It does not replace the application player and does not probe every stream.
Source health comes from the Data Engine registry/health-check layer.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "CineHUB_Data/sources/registry.json"
INPUT_PATH = ROOT / "CineHUB_Data/normalized/channels.json"
OUTPUT_DIR = ROOT / "CineHUB_Data/resolved"
OUTPUT_PATH = OUTPUT_DIR / "channels.json"

MAX_FALLBACKS = 4
STATUS_RANK = {
    "healthy": 0,
    "degraded": 1,
    "unknown": 2,
    "offline": 3,
}

QUALITY_RANK = {
    "2160p": 0,
    "1440p": 1,
    "1080p": 2,
    "720p": 3,
    "sd": 4,
}


def load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def source_health(registry: dict) -> dict[str, dict]:
    result = {}
    for source in [*registry.get("sources", []), *registry.get("localSources", [])]:
        sid = source.get("id")
        if not sid:
            continue
        health = source.get("health") or {}
        result[sid] = {
            "status": health.get("status", "unknown"),
            "lastChecked": health.get("lastChecked"),
            "latency": health.get("latency"),
            "httpStatus": health.get("httpStatus"),
            "error": health.get("error"),
        }
    return result


def numeric_priority(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 9999


def rank_source(source: dict, health: dict) -> tuple:
    status = health.get("status", "unknown")
    quality = str(source.get("quality") or "").lower()
    return (
        STATUS_RANK.get(status, STATUS_RANK["unknown"]),
        numeric_priority(source.get("priority")),
        QUALITY_RANK.get(quality, 99),
        numeric_priority(source.get("sourceOrder")),
        str(source.get("sourceId") or ""),
        str(source.get("url") or ""),
    )


def resolve() -> int:
    normalized = load_json(INPUT_PATH, {"channels": []})
    registry = load_json(REGISTRY_PATH, {"sources": [], "localSources": []})
    health = source_health(registry)

    channels = []
    stats = {
        "entitiesRead": 0,
        "entitiesPublished": 0,
        "sourcesRead": 0,
        "sourcesEligible": 0,
        "sourcesOffline": 0,
        "fallbackChains": 0,
        "maxFallbacks": MAX_FALLBACKS,
    }

    for entity in normalized.get("channels", []):
        stats["entitiesRead"] += 1
        resolved_sources = []

        for order, source in enumerate(entity.get("sources", []), start=1):
            if not source.get("url"):
                continue

            sid = source.get("sourceId")
            h = health.get(sid, {
                "status": "unknown",
                "lastChecked": None,
                "latency": None,
                "httpStatus": None,
                "error": None,
            })

            stats["sourcesRead"] += 1
            status = h.get("status", "unknown")
            if status == "offline":
                stats["sourcesOffline"] += 1

            resolved_sources.append({
                **source,
                "sourceOrder": order,
                "health": {
                    "status": status,
                    "lastChecked": h.get("lastChecked"),
                    "latency": h.get("latency"),
                    "httpStatus": h.get("httpStatus"),
                    "error": h.get("error"),
                },
            })

        resolved_sources.sort(
            key=lambda s: rank_source(s, s.get("health") or {})
        )

        # Keep offline sources as the final safety net. This preserves a
        # channel's last known source instead of silently deleting it.
        if resolved_sources:
            stats["sourcesEligible"] += sum(
                1 for s in resolved_sources
                if (s.get("health") or {}).get("status") != "offline"
            )

        selected = resolved_sources[:MAX_FALLBACKS]
        if len(selected) > 1:
            stats["fallbackChains"] += 1

        for index, source in enumerate(selected, start=1):
            source["fallbackOrder"] = index

        if selected:
            channels.append({
                "id": entity.get("id"),
                "name": entity.get("name"),
                "aliases": entity.get("aliases", []),
                "country": entity.get("country"),
                "language": entity.get("language"),
                "group": entity.get("group"),
                "sources": selected,
                "resolver": {
                    "strategy": "health-priority-quality",
                    "maxAttempts": len(selected),
                    "bounded": True,
                    "generatedBy": "CineHUB Data Engine Phase 5",
                },
            })
            stats["entitiesPublished"] += 1

    output = {
        "schemaVersion": "1.1.0",
        "generatedBy": "CineHUB Data Engine Phase 5",
        "policy": {
            "maxFallbacks": MAX_FALLBACKS,
            "strategy": "health-priority-quality",
            "offlineSourcesKeptAsLastResort": True,
            "infiniteRetries": False,
        },
        "stats": stats,
        "channels": sorted(
            channels,
            key=lambda x: (str(x.get("name") or "").lower(), str(x.get("id") or "")),
        ),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(resolve())
