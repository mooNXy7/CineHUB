#!/usr/bin/env python3
"""Build the public CineHUB Data Engine publication package."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "CineHUB_Data"
OUT = ROOT / "CineHUB_WEB" / "data-engine"

FILES = {
    "status.json": DATA / "status" / "data-status.json",
    "sources.json": DATA / "sources" / "registry.json",
    "channels/normalized.json": DATA / "normalized" / "channels.json",
    "channels/resolved.json": DATA / "resolved" / "channels.json",
    "catalog/manifest.json": DATA / "catalog" / "catalog-manifest.json",
    "catalog/movies.index.json": DATA / "catalog" / "movies.index.json",
    "catalog/series.index.json": DATA / "catalog" / "series.index.json",
    "catalog/series.entities.json": DATA / "catalog" / "series.entities.json",
    "catalog/episodes.index.json": DATA / "catalog" / "episodes.index.json",
    "catalog/featured.json": DATA / "catalog" / "featured.json",
    "catalog/trending.json": DATA / "catalog" / "trending.json",
    "catalog/releases.json": DATA / "catalog" / "releases.json",
    "catalog/metadata.json": DATA / "catalog" / "metadata.json",
    "epg/schedule.index.json": DATA / "epg" / "schedule.index.json",
    "epg/status.json": DATA / "status" / "epg-status.json",
}

REQUIRED = {
    "status.json",
    "sources.json",
    "channels/normalized.json",
    "channels/resolved.json",
    "catalog/manifest.json",
    "catalog/movies.index.json",
    "catalog/series.index.json",
    "catalog/metadata.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def build() -> dict:
    missing = [key for key, src in FILES.items() if key in REQUIRED and not src.is_file()]
    if missing:
        raise SystemExit("Missing required Data Engine outputs: " + ", ".join(missing))

    previous = None
    previous_path = OUT / "manifest.json"
    if previous_path.is_file():
        try:
            previous = read_json(previous_path)
        except Exception:
            previous = None

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    with TemporaryDirectory(prefix="cinehub-data-publish-") as tmp:
        tmp_root = Path(tmp)
        datasets = {}

        for rel, src in FILES.items():
            if not src.is_file():
                continue
            dest = tmp_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            datasets[rel] = {
                "path": f"data-engine/{rel}",
                "bytes": dest.stat().st_size,
                "sha256": sha256(dest),
            }

        status = read_json(DATA / "status" / "data-status.json")
        epg_status_path = DATA / "status" / "epg-status.json"
        epg_status = read_json(epg_status_path) if epg_status_path.is_file() else None

        capabilities = {
            "channels": "resolved+normalized",
            "catalog": "pre-indexed",
            "series": "series+season+episode indexes",
            "epg": bool(epg_status_path.is_file() and (DATA / "epg" / "schedule.index.json").is_file()),
            "health": True,
        }

        publication = {
            "schemaVersion": "1.0.0",
            "engine": "CineHUB Data Engine",
            "publicationVersion": 1,
            "generatedAt": generated_at,
            "basePath": "/data-engine/",
            "atomic": True,
            "datasets": datasets,
            "capabilities": capabilities,
        }

        if previous and previous.get("datasets") == datasets and previous.get("capabilities") == capabilities:
            publication["generatedAt"] = previous.get("generatedAt", generated_at)

        health = status.get("healthChecks", {})
        catalog = status.get("catalog", {})
        if not catalog.get("movies") or not catalog.get("series"):
            try:
                stats = read_json(DATA / "catalog" / "metadata.json").get("stats", {})
                catalog = {
                    "movies": stats.get("movies"),
                    "series": stats.get("seriesEntities", stats.get("series")),
                    "episodes": stats.get("episodes"),
                }
            except Exception:
                pass

        consolidated = {
            "schemaVersion": "1.0.0",
            "status": status.get("status", "unknown"),
            "updatedAt": publication["generatedAt"],
            "engine": {
                "phase": 8,
                "lastRunAt": status.get("engine", {}).get("lastRunAt"),
                "publication": "cloudflare-pages-compatible",
            },
            "sources": {
                "total": health.get("total", 0),
                "healthy": health.get("healthy", 0),
                "degraded": health.get("degraded", 0),
                "offline": health.get("offline", 0),
                "unknown": health.get("unknown", 0),
            },
            "catalog": catalog,
            "epg": {
                "status": epg_status.get("status", "not-generated") if epg_status else "not-generated",
                "lastRefresh": epg_status.get("generatedAt") if epg_status else None,
                "channelsWithPrograms": (epg_status or {}).get("stats", {}).get("channelsWithPrograms"),
                "programs": (epg_status or {}).get("stats", {}).get("programs"),
            },
            "publication": {
                "manifest": "/data-engine/manifest.json",
                "cachePolicy": "short-lived manifest, cacheable datasets",
            },
        }

        previous_status_path = OUT / "status-public.json"
        if previous_status_path.is_file():
            try:
                old = read_json(previous_status_path)
                a = dict(consolidated)
                b = dict(old)
                a.pop("updatedAt", None)
                b.pop("updatedAt", None)
                if a == b:
                    consolidated["updatedAt"] = old.get("updatedAt", publication["generatedAt"])
            except Exception:
                pass

        (tmp_root / "manifest.json").write_text(
            json.dumps(publication, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (tmp_root / "status-public.json").write_text(
            json.dumps(consolidated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        backup = OUT.with_name(OUT.name + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        if OUT.exists():
            OUT.rename(backup)
        try:
            shutil.copytree(tmp_root, OUT)
        except Exception:
            if OUT.exists():
                shutil.rmtree(OUT)
            if backup.exists():
                backup.rename(OUT)
            raise
        else:
            if backup.exists():
                shutil.rmtree(backup)

    return publication


if __name__ == "__main__":
    result = build()
    print(json.dumps({
        "published": True,
        "generatedAt": result["generatedAt"],
        "datasets": len(result["datasets"]),
        "basePath": result["basePath"],
        "epg": result["capabilities"]["epg"],
    }, ensure_ascii=False))
